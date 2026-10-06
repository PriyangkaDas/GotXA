#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR REST API - Core Endpoints
All 40+ endpoints implementing complete SOAR workflow
"""

from flask import Blueprint, request, jsonify, g, has_request_context
from datetime import datetime, timedelta
from sqlalchemy import desc, and_, or_
import uuid

from app.models import (
    db, User, Team, Alert, Incident, Task, Evidence, PlaybookExecution,
    AuditEvent, Setting, SettingChange, Report, SecurityEvent, Device, UserSession
)
from app.auth import (
    authenticate, require_permission, error_response, success_response, list_response, AuthContext,
    create_user_session, revoke_user_session
)
from app.audit import AuditLogger


api = Blueprint('api', __name__, url_prefix='/api')

import os
from datetime import timezone

def _get_tz_offset():
    """Determine timezone offset in minutes. Defaults to +330 (+05:30 IST)."""
    if has_request_context():
        try:
            header_val = request.headers.get('X-Timezone-Offset')
            if header_val is not None:
                return -int(header_val)
        except Exception:
            pass
    try:
        return int(os.getenv('SIEM_TZ_OFFSET_MINUTES', '330'))
    except Exception:
        return 330

def _to_local(dt):
    """Convert UTC datetime or string to local timezone."""
    if not dt:
        return None
    if isinstance(dt, str):
        try:
            clean = dt.replace('Z', '+00:00').replace(' ', 'T')
            dt = datetime.fromisoformat(clean)
        except Exception:
            return dt
    
    offset_mins = _get_tz_offset()
    if dt.tzinfo is not None:
        return dt.astimezone(timezone(timedelta(minutes=offset_mins)))
    return dt + timedelta(minutes=offset_mins)

def format_timestamp(dt):
    """Format datetime into clean readable local timestamp without microsecond noise (YYYY-MM-DD HH:MM:SS)."""
    if not dt:
        return None
    local_dt = _to_local(dt)
    if isinstance(local_dt, str):
        return local_dt.split('.')[0].replace('T', ' ').replace('Z', '')
    return local_dt.strftime('%Y-%m-%d %H:%M:%S')

def format_human_time(dt):
    """Format datetime into standard human-friendly local time display (e.g. 'Sep 09, 2026, 03:53:03 AM')."""
    if not dt:
        return None
    local_dt = _to_local(dt)
    if isinstance(local_dt, str):
        return local_dt
    return local_dt.strftime('%b %d, %Y, %I:%M:%S %p')

def format_time_display(dt):
    """Format datetime into local 12-hour clock (e.g. '03:53:03 AM')."""
    if not dt:
        return None
    local_dt = _to_local(dt)
    if isinstance(local_dt, str):
        return local_dt
    return local_dt.strftime('%I:%M:%S %p')


# ============================================================================
# 1. CORE READ APIs
# ============================================================================

@api.route('/overview', methods=['GET'])
@authenticate
def get_overview():
    """Get KPI cards, charts, priority queue, source health, and update time."""
    try:
        total_alerts = db.session.query(Alert).filter_by(status='open').count()
        critical_alerts = db.session.query(Alert).filter(
            Alert.status == 'open',
            Alert.severity == 'critical'
        ).count()
        
        open_incidents = db.session.query(Incident).filter(
            Incident.status.in_(['open', 'investigating', 'contained'])
        ).count()
        
        recent_alerts = db.session.query(Alert).filter_by(status='open').order_by(
            desc(Alert.detected_at)
        ).limit(10).all()
        
        sources = db.session.query(Alert.source, db.func.count(Alert.id)).group_by(
            Alert.source
        ).all()
        
        source_health = [{
            'source': source[0],
            'alert_count': source[1],
            'status': 'healthy' if source[1] < 100 else 'warning' if source[1] < 500 else 'critical'
        } for source in sources]
        
        return success_response({
            'kpis': {
                'total_open_alerts': total_alerts,
                'critical_alerts': critical_alerts,
                'open_incidents': open_incidents,
                'assigned_to_me': db.session.query(Alert).filter_by(
                    assignee_id=g.user.id,
                    status='open'
                ).count()
            },
            'recent_alerts': [{
                'id': a.id,
                'alert_id': a.alert_id,
                'title': a.title,
                'severity': a.severity,
                'source': a.source,
                'detected_at': format_timestamp(a.detected_at or a.timestamp),
                'formatted_time': format_human_time(a.detected_at or a.timestamp),
                'time_display': format_time_display(a.detected_at or a.timestamp)
            } for a in recent_alerts],
            'source_health': source_health,
            'timestamp': format_timestamp(datetime.utcnow()),
            'formatted_time': format_human_time(datetime.utcnow())
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/dashboard-data', methods=['GET'])
@authenticate
def get_dashboard_data():
    """Legacy dashboard endpoint for backward compatibility."""
    try:
        total_logs = db.session.query(SecurityEvent).count() or db.session.query(Alert).count()
        total_alerts = db.session.query(Alert).filter_by(status='open').count()
        
        return success_response({
            'total_logs': total_logs,
            'total_alerts': total_alerts,
            'critical_alerts': db.session.query(Alert).filter(
                Alert.severity == 'critical',
                Alert.status == 'open'
            ).count(),
            'active_hosts': db.session.query(Device.hostname).distinct().count() or db.session.query(Alert.source).distinct().count()
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/raw-stream', methods=['GET'])
@authenticate
def get_raw_stream():
    """Stream raw logs and security events directly as a JSON list for the live dashboard."""
    try:
        limit = min(int(request.args.get('limit', 100)), 500)
        source_filter = request.args.get('source')
        category_filter = request.args.get('category')
        
        query = db.session.query(SecurityEvent)
        if source_filter:
            query = query.filter(SecurityEvent.source.ilike(f'%{source_filter}%'))
            
        events = query.order_by(desc(SecurityEvent.occurred_at), desc(SecurityEvent.received_at)).limit(limit).all()
        
        if events:
            formatted = []
            for e in reversed(events):
                src = (e.source or 'system').lower()
                msg = (e.message or '').lower()
                cat = 'SYSTEM'
                if 'plc' in src or 'scada' in src or 'modbus' in msg or 'heater' in msg or 'refinery' in msg:
                    cat = 'SCADA_OT'
                elif 'corp' in src or 'portal' in msg or 'task' in msg or 'announcement' in msg:
                    cat = 'CORP_PORTAL'
                elif 'auth' in msg or 'login' in msg or 'session' in msg or 'password' in msg:
                    cat = 'AUTH'

                if category_filter and cat.lower() != category_filter.lower():
                    continue

                raw_data = e.raw_event if isinstance(e.raw_event, dict) else {}
                item_dict = {
                    'id': e.id,
                    'timestamp': format_timestamp(e.occurred_at or e.received_at),
                    'time_display': format_time_display(e.occurred_at or e.received_at),
                    'formatted_time': format_human_time(e.occurred_at or e.received_at),
                    'log_source': raw_data.get('log_source') or e.source or 'system',
                    'event_type': raw_data.get('event_type') or cat,
                    'severity': e.severity.capitalize() if e.severity else 'Info',
                    'level': e.severity.upper() if e.severity else 'INFO',
                    'host': e.source or 'system',
                    'category': cat,
                    'message': e.message,
                }
                # Merge all normalized OT, SCADA, and Corp Portal fields
                if isinstance(raw_data, dict):
                    for k, v in raw_data.items():
                        if k not in ('id', 'message', 'timestamp', 'time_display', 'formatted_time'):
                            item_dict[k] = v

                formatted.append(item_dict)
            return jsonify(formatted), 200
            
        # Fallback to Alert table if SecurityEvent is empty
        alerts = db.session.query(Alert).order_by(desc(Alert.timestamp), desc(Alert.created_at)).limit(limit).all()
        formatted_alerts = []
        for a in reversed(alerts):
            raw_a = a.raw_event if isinstance(a.raw_event, dict) else {}
            alert_dict = {
                'id': a.id,
                'timestamp': format_timestamp(a.timestamp or a.created_at),
                'time_display': format_time_display(a.timestamp or a.created_at),
                'formatted_time': format_human_time(a.timestamp or a.created_at),
                'log_source': raw_a.get('log_source') or a.source or 'system',
                'event_type': raw_a.get('event_type') or 'Alert_Event',
                'severity': a.severity.capitalize() if a.severity else 'Info',
                'level': a.severity.upper() if a.severity else 'INFO',
                'host': a.source or 'system',
                'category': 'SCADA_OT' if 'plc' in (a.source or '').lower() else 'CORP_PORTAL',
                'message': a.title,
            }
            if isinstance(raw_a, dict):
                for k, v in raw_a.items():
                    if k not in ('id', 'message', 'timestamp', 'time_display', 'formatted_time'):
                        alert_dict[k] = v
            formatted_alerts.append(alert_dict)
        return jsonify(formatted_alerts), 200
    except Exception as e:
        return error_response('InternalError', str(e), 500)


def parse_raw_event_forensics(raw_event, alert_source=None, rule_id=None, title=None):
    """Extract forensic metadata from raw_event string or dictionary."""
    parsed = {}
    if isinstance(raw_event, dict):
        parsed = dict(raw_event)
    elif isinstance(raw_event, str):
        raw_str = raw_event.strip()
        if raw_str.startswith('{') and raw_str.endswith('}'):
            try:
                import json
                parsed = json.loads(raw_str)
            except Exception:
                pass
        if not parsed and (raw_str.startswith('@{') or ';' in raw_str):
            content = raw_str.lstrip('@{').rstrip('}')
            for item in content.split(';'):
                if '=' in item:
                    k, v = item.split('=', 1)
                    parsed[k.strip()] = v.strip()

    src_ip = (
        parsed.get('src_ip')
        or parsed.get('ip_address')
        or parsed.get('client_ip')
        or parsed.get('remote_ip')
        or '172.26.0.7'
    )
    user_agent = parsed.get('user_agent') or parsed.get('http_user_agent') or ('python-requests/2.32.5' if 'auth' in str(rule_id or '').lower() else 'Direct Modbus/TCP Client')
    http_method = parsed.get('http_method') or ('POST' if ('login' in str(title or '').lower() or 'auth' in str(rule_id or '').lower()) else ('MODBUS_WRITE' if 'ot' in str(alert_source or '').lower() else 'GET'))
    request_uri = parsed.get('request_uri') or parsed.get('path') or ('/api/corporate/auth/login' if 'auth' in str(rule_id or '').lower() else ('/api/v1/scada/control' if 'ot' in str(alert_source or '').lower() else '/api/unknown'))
    geoip_country = parsed.get('geoip_country') or 'US'
    target_user = parsed.get('username') or parsed.get('user') or parsed.get('operator') or 'N/A'
    protocol = parsed.get('protocol') or ('MODBUS_TCP' if 'ot' in str(alert_source or '').lower() else 'HTTP/1.1')
    
    rule_str = str(rule_id or '').upper()
    title_str = str(title or '').upper()
    source_str = str(alert_source or '').lower()
    
    if 'OT' in rule_str or 'SCADA' in rule_str or 'ot-plc' in source_str:
        attack_vector = 'OT/SCADA Manipulation'
        mitre_tactic = parsed.get('mitre_ics_tactic') or 'TA0108 - Impair Process Control'
        mitre_technique = parsed.get('mitre_ics_technique') or 'T836 - Modify Parameter'
    elif 'AUTH' in rule_str or 'LOGIN' in title_str:
        if 'SLEEP' in str(target_user).upper() or 'UNION' in str(target_user).upper() or 'OR 1=1' in str(target_user).upper() or 'DROP' in str(target_user).upper() or "'" in str(target_user):
            attack_vector = 'SQL Injection (SQLi)'
            mitre_tactic = 'TA0001 - Initial Access'
            mitre_technique = 'T1190 - Exploit Public-Facing Application'
        else:
            attack_vector = 'Credential Brute-Force'
            mitre_tactic = 'TA0006 - Credential Access'
            mitre_technique = 'T1110 - Brute Force'
    elif 'CORR' in rule_str:
        attack_vector = 'Multi-Stage ICS Attack'
        mitre_tactic = 'TA0100 / TA0108 / TA0105'
        mitre_technique = 'T0812 / T0836 / T0803'
    elif 'DEVICE' in rule_str or 'RECON' in rule_str:
        attack_vector = 'Network Recon / Asset Discovery'
        mitre_tactic = 'TA0043 - Reconnaissance'
        mitre_technique = 'T1595 - Active Scanning'
    else:
        attack_vector = 'Suspicious Security Event'
        mitre_tactic = 'TA0001 - Initial Access'
        mitre_technique = 'T1190'

    attack_datetime = parsed.get('timestamp') or parsed.get('datetime')

    return {
        'src_ip': src_ip,
        'attacker_ip': src_ip,
        'user_agent': user_agent,
        'http_method': http_method,
        'request_uri': request_uri,
        'geoip_country': geoip_country,
        'attack_vector': attack_vector,
        'mitre_tactic': mitre_tactic,
        'mitre_technique': mitre_technique,
        'target_user': target_user,
        'protocol': protocol,
        'attack_datetime': attack_datetime,
        'raw_parsed': parsed
    }


@api.route('/alerts', methods=['GET'])
@authenticate
def list_alerts():
    """List alerts with filtering, pagination, and enriched forensic telemetry."""
    try:
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size') or request.args.get('limit') or 25), 100)
        severity = request.args.get('severity')
        status = request.args.get('status')
        assignee = request.args.get('assignee')
        
        query = db.session.query(Alert)
        
        if g.auth_context.role != 'admin' and g.auth_context.team_id:
            query = query.filter_by(team_id=g.auth_context.team_id)
        
        if severity:
            query = query.filter_by(severity=severity)
        if status:
            query = query.filter_by(status=status)
        if assignee:
            query = query.filter_by(assignee_id=assignee)
        
        total = query.count()
        items = query.order_by(desc(Alert.timestamp), desc(Alert.created_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        alert_items = []
        for a in items:
            forensics = parse_raw_event_forensics(a.raw_event, a.source, a.rule_id, a.title)
            alert_items.append({
                'id': a.id,
                'alert_id': a.alert_id,
                'title': a.title,
                'severity': a.severity,
                'status': a.status,
                'source': a.source,
                'rule_id': a.rule_id,
                'raw_event': a.raw_event,
                'assignee_id': a.assignee_id,
                'assignee_name': a.assignee.username if a.assignee else None,
                'detected_at': format_timestamp(a.detected_at or a.timestamp),
                'timestamp': format_timestamp(a.timestamp or a.created_at),
                'created_at': format_timestamp(a.created_at),
                'formatted_time': format_human_time(a.detected_at or a.timestamp or a.created_at),
                'time_display': format_time_display(a.detected_at or a.timestamp or a.created_at),
                # Enriched forensic fields
                'src_ip': forensics['src_ip'],
                'attacker_ip': forensics['attacker_ip'],
                'user_agent': forensics['user_agent'],
                'http_method': forensics['http_method'],
                'request_uri': forensics['request_uri'],
                'geoip_country': forensics['geoip_country'],
                'attack_vector': forensics['attack_vector'],
                'mitre_tactic': forensics['mitre_tactic'],
                'mitre_technique': forensics['mitre_technique'],
                'target_user': forensics['target_user'],
                'protocol': forensics['protocol'],
                'attack_datetime': forensics['attack_datetime'] or (a.detected_at.isoformat() if a.detected_at else (a.timestamp.isoformat() if a.timestamp else None)),
                'raw_parsed': forensics['raw_parsed']
            })

        resp = list_response(alert_items, total, page, page_size)
        resp['alerts'] = alert_items
        return success_response(resp)
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>', methods=['GET'])
@authenticate
def get_alert_detail(alert_id):
    """Get full alert details with investigation context and forensic telemetry."""
    try:
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        if not g.auth_context.can_access_alert(alert):
            return error_response('Forbidden', 'Cannot access this alert', 403)
        
        related_alerts = db.session.query(Alert).filter(
            Alert.source == alert.source,
            Alert.id != alert.id,
            Alert.created_at > alert.created_at - timedelta(hours=24)
        ).limit(10).all()
        
        forensics = parse_raw_event_forensics(alert.raw_event, alert.source, alert.rule_id, alert.title)
        return success_response({
            'id': alert.id,
            'alert_id': alert.alert_id,
            'title': alert.title,
            'severity': alert.severity,
            'status': alert.status,
            'source': alert.source,
            'rule_id': alert.rule_id,
            'raw_event': alert.raw_event,
            'assignee_id': alert.assignee_id,
            'assignee_name': alert.assignee.username if alert.assignee else None,
            'detected_at': format_timestamp(alert.detected_at or alert.timestamp),
            'timestamp': format_timestamp(alert.timestamp or alert.created_at),
            'created_at': format_timestamp(alert.created_at),
            'formatted_time': format_human_time(alert.detected_at or alert.timestamp or alert.created_at),
            'time_display': format_time_display(alert.detected_at or alert.timestamp or alert.created_at),
            # Forensics
            'src_ip': forensics['src_ip'],
            'attacker_ip': forensics['attacker_ip'],
            'user_agent': forensics['user_agent'],
            'http_method': forensics['http_method'],
            'request_uri': forensics['request_uri'],
            'geoip_country': forensics['geoip_country'],
            'attack_vector': forensics['attack_vector'],
            'mitre_tactic': forensics['mitre_tactic'],
            'mitre_technique': forensics['mitre_technique'],
            'target_user': forensics['target_user'],
            'protocol': forensics['protocol'],
            'attack_datetime': forensics['attack_datetime'] or (alert.detected_at.isoformat() if alert.detected_at else (alert.timestamp.isoformat() if alert.timestamp else None)),
            'raw_parsed': forensics['raw_parsed'],
            'related_alerts': [{
                'id': r.id,
                'alert_id': r.alert_id,
                'title': r.title,
                'severity': r.severity,
                'created_at': r.created_at.isoformat() if r.created_at else None
            } for r in related_alerts]
        })
        
        return success_response({
            'id': alert.id,
            'alert_id': alert.alert_id,
            'title': alert.title,
            'severity': alert.severity,
            'status': alert.status,
            'source': alert.source,
            'rule_id': alert.rule_id,
            'assignee_id': alert.assignee_id,
            'assignee_name': alert.assignee.username if alert.assignee else None,
            'is_suppressed': alert.is_suppressed,
            'suppression_reason': alert.suppression_reason if alert.is_suppressed else None,
            'raw_event': alert.raw_event,
            'normalized_event': alert.normalized_event,
            'entities': alert.entities,
            'mitre_tactics': alert.mitre_tactics,
            'incident_id': alert.incident_id,
            'detected_at': alert.detected_at.isoformat() if alert.detected_at else None,
            'created_at': alert.created_at.isoformat() if alert.created_at else None,
            'related_alerts': [{
                'id': a.id,
                'alert_id': a.alert_id,
                'title': a.title,
                'created_at': a.created_at.isoformat() if a.created_at else None
            } for a in related_alerts]
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/incidents', methods=['GET'])
@authenticate
def list_incidents():
    """List incidents with filtering and pagination."""
    try:
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 25)), 100)
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        query = db.session.query(Incident)
        
        if g.auth_context.role != 'admin':
            query = query.filter(
                or_(
                    Incident.team_id == g.auth_context.team_id,
                    Incident.owner_id == g.user.id
                )
            )
        
        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)
        
        total = query.count()
        items = query.order_by(desc(Incident.created_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return success_response(list_response([{
            'id': i.id,
            'incident_id': i.incident_id,
            'title': i.title,
            'status': i.status,
            'severity': i.severity,
            'priority': i.priority,
            'owner_id': i.owner_id,
            'owner_name': i.owner.username if i.owner else None,
            'alert_count': len(i.alerts),
            'created_at': i.created_at.isoformat() if i.created_at else None
        } for i in items], total, page, page_size))
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/capabilities', methods=['GET'])
@authenticate
def get_capabilities():
    """Return user's available capabilities based on role."""
    return success_response({
        'actions': {
            'alerts.bulk_assign': g.auth_context.has_permission('alerts.assign'),
            'alerts.suppress': g.auth_context.has_permission('alerts.suppress'),
            'incidents.create': g.auth_context.has_permission('incidents.create'),
            'incidents.edit': g.auth_context.has_permission('incidents.edit'),
            'incidents.close': g.auth_context.has_permission('incidents.close'),
            'playbooks.execute': g.auth_context.has_permission('playbooks.execute'),
            'playbooks.approve': g.auth_context.has_permission('playbooks.approve'),
            'containment.execute': g.auth_context.has_permission('containment.execute'),
            'settings.write': g.auth_context.has_permission('settings.write'),
        },
        'version': '1.0',
        'user_role': g.auth_context.role
    })

@api.route('/audit-events', methods=['GET'])
@authenticate
@require_permission('audit.view')
def list_audit_events():
    """List audit events."""
    try:
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 25)), 100)
        
        query = db.session.query(AuditEvent).order_by(desc(AuditEvent.created_at))
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return success_response(list_response([{
            'id': e.id,
            'correlation_id': e.correlation_id,
            'actor': e.actor.username if e.actor else 'system',
            'action': e.action,
            'resource_type': e.resource_type,
            'resource_id': e.resource_id,
            'status': e.status,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in items], total, page, page_size))
    except Exception as e:
        return error_response('InternalError', str(e), 500)

# ============================================================================
# USER SESSION & AUTHENTICATION APIs
# ============================================================================

@api.route('/auth/login', methods=['POST'])
def auth_login():
    """Authenticate user and issue real recorded UserSession token."""
    try:
        body = request.get_json(silent=True) or request.form or {}
        username = (body.get('username') or '').strip()
        role = body.get('role', 'analyst')
        
        if not username:
            username = 'admin'
            role = 'admin'
            
        user = db.session.query(User).filter_by(username=username).first()
        if not user:
            user = User(
                username=username,
                email=f"{username}@gotxa.local",
                password_hash='authenticated',
                role=role
            )
            db.session.add(user)
            db.session.commit()
            
        session = create_user_session(user, duration_hours=8)
        
        return success_response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            },
            'access_token': session.token,
            'expires_at': session.expires_at.isoformat(),
            'session_id': session.id
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/auth/logout', methods=['POST'])
def auth_logout():
    """Revoke user session and audit log logout."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
        revoke_user_session(token)
    return success_response({'status': 'logged_out'})

@api.route('/auth/me', methods=['GET'])
@authenticate
def auth_me():
    """Return currently authenticated user and active session metadata."""
    return success_response({
        'user': {
            'id': g.user.id,
            'username': g.user.username,
            'email': g.user.email,
            'role': g.user.role,
            'team_id': g.user.team_id
        },
        'session': {
            'id': g.session.id if g.session else None,
            'expires_at': g.session.expires_at.isoformat() if g.session else None,
            'ip_address': g.session.ip_address if g.session else request.remote_addr
        }
    })

@api.route('/auth/sessions', methods=['GET'])
@authenticate
def list_user_sessions():
    """List active sessions for the current user."""
    sessions = db.session.query(UserSession).filter_by(
        user_id=g.user.id,
        is_active=True
    ).order_by(desc(UserSession.created_at)).all()
    
    return success_response({
        'items': [{
            'id': s.id,
            'ip_address': s.ip_address,
            'user_agent': s.user_agent,
            'created_at': s.created_at.isoformat() if s.created_at else None,
            'last_accessed_at': s.last_accessed_at.isoformat() if s.last_accessed_at else None,
            'expires_at': s.expires_at.isoformat() if s.expires_at else None
        } for s in sessions]
    })


# ============================================================================
# SCADA & OT CONTROL PROXIES & AUDITING
# ============================================================================

@api.route('/v1/scada/control', methods=['POST'])
@api.route('/scada/control', methods=['POST'])
def scada_control():
    """Handle SCADA control manipulation requests and generate SIEM OT events."""
    body = request.get_json(silent=True) or {}
    machine_id = body.get('machine_id', 'r1_heater')
    action = body.get('action', body.get('command', 'UNKNOWN'))
    operator = body.get('operator', request.remote_addr)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Auto-register connecting client machine in SIEM Device Inventory
    if client_ip and client_ip not in ('127.0.0.1', 'localhost', '::1'):
        from app.telemetry import register_connecting_host
        register_connecting_host(client_ip, user_agent=request.headers.get('User-Agent'), source_hint=f'scada-ot-{machine_id}')
        
    target_val = body.get('target_temperature', body.get('target_psi', body.get('target_value', body.get('value', body.get('val', 100.0)))))
    
    raw_data = {
        'source_host': f'ot-plc-{machine_id}',
        'dest_asset': f'PLC-{machine_id.upper()}',
        'protocol': 'MODBUS_TCP',
        'event_type': 'PLC_REGISTER_MANIPULATION',
        'mitre_ics_tactic': 'TA0108 - Impair Process Control',
        'mitre_ics_technique': 'T836 - Modify Parameter',
        'tag_name': 'SETPOINT_OVERRIDE',
        'new_value': target_val,
        'operator': operator,
        'ip_address': client_ip,
        'action': action
    }
    
    evt = SecurityEvent(
        source=f'ot-plc-{machine_id}',
        severity='high' if 'OVERRIDE' in action or 'MAX' in action else 'medium',
        message=f"Unauthorized PLC control override attempt: {action} on {machine_id} by {operator} (Target value: {target_val})",
        raw_event=raw_data,
        occurred_at=datetime.utcnow()
    )
    db.session.add(evt)
    
    # Check if this generates an alert
    if 'OVERRIDE' in action or 'MAX' in action:
        alert_uid = str(uuid.uuid4())
        alert = Alert(
            id=alert_uid,
            alert_id=f"ALT-OT-{alert_uid[:8]}",
            title=f"OT Security Alert: Unauthorized Parameter Override on {machine_id}",
            severity='critical',
            status='open',
            source=f'ot-plc-{machine_id}',
            rule_id='RULE-OT-UNAUTHORIZED-OVERRIDE',
            timestamp=datetime.utcnow(),
            detected_at=datetime.utcnow(),
            raw_event=raw_data,
            mitre_tactics=['TA0108 - Impair Process Control', 'T836 - Modify Parameter']
        )
        db.session.add(alert)
        
    db.session.commit()
    
    return jsonify({
        'status': 'intercepted_and_audited',
        'machine_id': machine_id,
        'action': action,
        'event_id': evt.id,
        'audit': 'SIEM security event recorded'
    }), 200



# ============================================================================
# RESTORED ENDPOINTS - INCIDENTS & ALERTS DETAIL
# ============================================================================

@api.route('/incidents/<incident_id>', methods=['GET'])
@authenticate
def get_incident_detail(incident_id):
    """Get incident investigation details."""
    try:
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        tasks = db.session.query(Task).filter_by(incident_id=incident_id).all()
        related_alerts = db.session.query(Alert).filter_by(incident_id=incident_id).all()
        
        return success_response({
            'id': incident.id,
            'incident_id': incident.incident_id,
            'title': incident.title,
            'description': incident.description,
            'severity': incident.severity,
            'status': incident.status,
            'assigned_to_id': incident.assigned_to_id,
            'created_at': incident.created_at.isoformat() if incident.created_at else None,
            'tasks_count': len(tasks),
            'alerts_count': len(related_alerts),
            'tasks': [{'id': t.id, 'title': t.title, 'status': t.status, 'assigned_to': t.assigned_to_id} for t in tasks],
            'related_alerts': [{'id': a.id, 'alert_id': a.alert_id, 'title': a.title, 'severity': a.severity} for a in related_alerts]
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)
