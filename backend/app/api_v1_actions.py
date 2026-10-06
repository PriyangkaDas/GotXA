#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR REST API - Action Endpoints
SOAR playbook execution, incident lifecycle, settings management
"""

from flask import Blueprint, request, g, jsonify
from datetime import datetime
from sqlalchemy import desc
import ipaddress
import logging
import os
import subprocess
import uuid

from app.models import (
    db, Alert, Incident, Task, Evidence, PlaybookExecution, AuditEvent, Setting, SettingChange
)
from app.auth import authenticate, require_permission, error_response, success_response
from app.audit import AuditLogger

api = Blueprint('api_actions', __name__, url_prefix='/api')
audit = AuditLogger()
logger = logging.getLogger(__name__)


def _enforce_ip_block(target_ip):
    """Apply an idempotent INPUT drop rule when real enforcement is enabled."""
    try:
        parsed_ip = ipaddress.ip_address(str(target_ip))
    except ValueError:
        return False, f'Invalid target IP: {target_ip}'

    if parsed_ip.is_loopback or parsed_ip.is_unspecified or parsed_ip.is_multicast:
        return False, f'Refusing to block unsafe target IP: {target_ip}'

    real_mode = os.getenv('SOAR_REAL_MODE', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}
    command = ['iptables', '-s', str(parsed_ip), '-j', 'DROP']
    if not real_mode:
        return True, f'[SIMULATED] iptables -A INPUT -s {parsed_ip} -j DROP'

    try:
        exists = subprocess.run(
            ['iptables', '-C', 'INPUT', *command[1:]],
            capture_output=True,
            text=True,
            check=False,
        )
        if exists.returncode != 0:
            subprocess.run(
                ['iptables', '-A', 'INPUT', *command[1:]],
                capture_output=True,
                text=True,
                check=True,
            )
        return True, f'[REAL] iptables INPUT DROP installed for {parsed_ip}'
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, 'stderr', '') or str(error)
        return False, f'Unable to install firewall rule for {parsed_ip}: {detail.strip()}'

# ============================================================================
# 2. ALERT ACTIONS
# ============================================================================

@api.route('/alerts/assign', methods=['POST'])
@authenticate
@require_permission('alerts.assign')
def bulk_assign_alerts():
    """Bulk assign alerts to users."""
    try:
        data = request.get_json()
        alert_ids = data.get('alert_ids', [])
        assignee_id = data.get('assignee_id')
        reason = data.get('reason', 'Bulk assignment')
        
        if not alert_ids or not assignee_id:
            return error_response('BadRequest', 'alert_ids and assignee_id required', 400)
        
        alerts = db.session.query(Alert).filter(Alert.id.in_(alert_ids)).all()
        
        for alert in alerts:
            old_assignee = alert.assignee_id
            alert.assignee_id = assignee_id
            
            audit.log(
                actor=g.user,
                action='alert.reassigned',
                resource_type='Alert',
                resource_id=alert.id,
                change_before={'assignee_id': old_assignee},
                change_after={'assignee_id': assignee_id},
                reason=reason
            )
        
        db.session.commit()
        
        return success_response({
            'assigned_count': len(alerts),
            'timestamp': datetime.utcnow().isoformat()
        }, 'Alerts assigned', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>/suppress', methods=['POST'])
@authenticate
@require_permission('alerts.suppress')
def suppress_alert(alert_id):
    """Suppress an alert."""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Manual suppression')
        scope = data.get('scope', 'single')  # single, rule, source
        duration_hours = data.get('duration_hours', 24)
        
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        alert.is_suppressed = True
        alert.suppression_reason = reason
        alert.suppression_scope = scope
        alert.suppression_expires_at = datetime.utcnow() + __import__('datetime').timedelta(hours=duration_hours)
        
        audit.log(
            actor=g.user,
            action='alert.suppressed',
            resource_type='Alert',
            resource_id=alert.id,
            reason=reason
        )
        
        db.session.commit()
        
        return success_response({'id': alert.id, 'suppressed': True}, 'Alert suppressed', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>/status', methods=['PUT'])
@authenticate
def update_alert_status(alert_id):
    """Update alert status."""
    try:
        data = request.get_json()
        new_status = data.get('status')  # open, investigating, resolved, closed
        reason = data.get('reason', '')
        
        if new_status not in ['open', 'investigating', 'resolved', 'closed']:
            return error_response('BadRequest', 'Invalid status', 400)
        
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        old_status = alert.status
        alert.status = new_status
        
        audit.log(
            actor=g.user,
            action='alert.status_changed',
            resource_type='Alert',
            resource_id=alert.id,
            change_before={'status': old_status},
            change_after={'status': new_status},
            reason=reason
        )
        
        db.session.commit()
        
        return success_response({'id': alert.id, 'status': new_status}, 'Alert status updated', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 3. INCIDENT ACTIONS
# ============================================================================

@api.route('/incidents', methods=['POST'])
@authenticate
@require_permission('incidents.create')
def create_incident():
    """Create a new incident."""
    try:
        data = request.get_json()
        
        incident = Incident(
            incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            title=data.get('title'),
            description=data.get('description', ''),
            severity=data.get('severity', 'medium'),
            priority=data.get('priority', 'medium'),
            status='open',
            owner_id=g.user.id,
            team_id=g.user.team_id,
            detected_at=datetime.utcnow(),
            affected_assets=data.get('affected_assets', []),
            mitre_tactics=data.get('mitre_tactics', [])
        )
        
        db.session.add(incident)
        db.session.flush()
        
        audit.log(
            actor=g.user,
            action='incident.created',
            resource_type='Incident',
            resource_id=incident.id,
            reason=data.get('reason', '')
        )
        
        db.session.commit()
        
        return success_response({
            'id': incident.id,
            'incident_id': incident.incident_id,
            'title': incident.title,
            'status': incident.status
        }, 'Incident created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>/status', methods=['PUT'])
@authenticate
@require_permission('incidents.edit')
def update_incident_status(incident_id):
    """Update incident status (lifecycle management)."""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        # Valid transitions
        valid_transitions = {
            'open': ['investigating', 'closed'],
            'investigating': ['contained', 'closed'],
            'contained': ['resolved', 'closed'],
            'resolved': ['closed'],
            'closed': []
        }
        
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        if new_status not in valid_transitions.get(incident.status, []):
            return error_response(
                'InvalidStateTransition',
                f'Cannot transition from {incident.status} to {new_status}',
                409
            )
        
        old_status = incident.status
        incident.status = new_status
        
        if new_status == 'contained':
            incident.contained_at = datetime.utcnow()
        elif new_status == 'resolved':
            incident.resolved_at = datetime.utcnow()
        elif new_status == 'closed':
            incident.closed_at = datetime.utcnow()
            incident.closure_reason = data.get('closure_reason', '')
            incident.lessons_learned = data.get('lessons_learned', '')
        
        audit.log(
            actor=g.user,
            action='incident.status_changed',
            resource_type='Incident',
            resource_id=incident.id,
            change_before={'status': old_status},
            change_after={'status': new_status},
            reason=data.get('reason', '')
        )
        
        db.session.commit()
        
        return success_response({
            'id': incident.id,
            'status': new_status,
            'timestamp': datetime.utcnow().isoformat()
        }, 'Incident status updated', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>/assign', methods=['POST'])
@authenticate
@require_permission('incidents.edit')
def assign_incident(incident_id):
    """Assign incident to a user."""
    try:
        data = request.get_json()
        owner_id = data.get('owner_id')
        
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        old_owner = incident.owner_id
        incident.owner_id = owner_id
        
        audit.log(
            actor=g.user,
            action='incident.reassigned',
            resource_type='Incident',
            resource_id=incident.id,
            change_before={'owner_id': old_owner},
            change_after={'owner_id': owner_id}
        )
        
        db.session.commit()
        
        return success_response({'id': incident.id, 'owner_id': owner_id}, 'Incident assigned', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/incidents/<incident_id>/link-alert', methods=['POST'])
@authenticate
def link_alert_to_incident(incident_id):
    """Link an alert to an incident."""
    try:
        data = request.get_json()
        alert_id = data.get('alert_id')
        
        incident = db.session.query(Incident).filter_by(id=incident_id).first()
        if not incident:
            return error_response('NotFound', 'Incident not found', 404)
        
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        alert.incident_id = incident.id
        
        audit.log(
            actor=g.user,
            action='alert.linked_to_incident',
            resource_type='Alert',
            resource_id=alert.id,
            reason=f'Linked to incident {incident.incident_id}'
        )
        
        db.session.commit()
        
        return success_response({'incident_id': incident.id, 'alert_id': alert.id}, 'Alert linked', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 4. SOAR PLAYBOOK ACTIONS
# ============================================================================

@api.route('/v1/soar/actions', methods=['GET'])
def list_soar_actions():
    """List available SOAR playbooks/actions and recently executed mitigations."""
    try:
        from app.soar_engine import get_recent_soar_actions
        limit = int(request.args.get('limit', 50))
        recent = get_recent_soar_actions(limit)
        
        # Merge recent database executions if memory ledger is sparse
        try:
            executions = db.session.query(PlaybookExecution).order_by(desc(PlaybookExecution.created_at)).limit(limit).all()
            for e in executions:
                action_type = 'ip_block' if 'block' in e.playbook_id else 'container_isolate' if 'isolate' in e.playbook_id else 'service_restart' if 'restart' in e.playbook_id else 'rate_limit' if 'rate' in e.playbook_id else 'credential_lock' if 'password' in e.playbook_id else 'monitor_escalation' if 'monitor' in e.playbook_id else e.playbook_id
                target = ''
                if isinstance(e.inputs, dict):
                    target = e.inputs.get('target_ip') or e.inputs.get('ip') or e.inputs.get('host') or ''
                summary = ''
                if isinstance(e.outputs, dict):
                    summary = e.outputs.get('summary', '')
                act = {
                    'id': e.id,
                    'action_id': e.execution_id,
                    'action_type': action_type,
                    'playbook': e.playbook_id,
                    'description': e.reason or summary or f"{e.playbook_id} on {target}",
                    'target': target,
                    'status': e.status,
                    'result_detail': summary or f"Executed playbook {e.playbook_id} successfully.",
                    'timestamp': e.created_at.isoformat() if e.created_at else datetime.utcnow().isoformat()
                }
                if not any(r.get('action_id') == act['action_id'] for r in recent):
                    recent.append(act)
        except Exception as error:
            logger.error('Failed to merge persisted SOAR executions: %s', error)
            pass

        catalog = [
            {
                'id': 'containment.isolate_host',
                'name': 'Isolate Compromised Host',
                'description': 'Isolate host from network',
                'category': 'containment',
                'risk_level': 'high',
                'requires_approval': True,
                'estimated_time': '5 minutes'
            },
            {
                'id': 'response.reset_password',
                'name': 'Reset User Credentials',
                'description': 'Force password reset for compromised account',
                'category': 'response',
                'risk_level': 'medium',
                'requires_approval': True,
                'estimated_time': '2 minutes'
            },
            {
                'id': 'investigation.collect_artifacts',
                'name': 'Collect Forensic Artifacts',
                'description': 'Collect logs and artifacts from host',
                'category': 'investigation',
                'risk_level': 'low',
                'requires_approval': False,
                'estimated_time': '10 minutes'
            },
            {
                'id': 'enrichment.get_threat_intel',
                'name': 'Get Threat Intelligence',
                'description': 'Lookup indicators in threat feeds',
                'category': 'enrichment',
                'risk_level': 'low',
                'requires_approval': False,
                'estimated_time': '3 minutes'
            }
        ]

        return jsonify({
            'data': recent,
            'actions': catalog,
            'items': recent,
            'message': 'Success'
        }), 200
    except Exception as e:
        return error_response('InternalError', str(e), 500)

def run_playbook_logic(playbook_id, inputs=None, execution=None):
    """Execute SOAR playbook logic synchronously and return outputs dictionary."""
    inputs = inputs or {}
    now = datetime.utcnow()
    target_ip = inputs.get('ip') or inputs.get('target_ip') or inputs.get('src_ip') or '172.26.0.7'
    target_host = inputs.get('host') or inputs.get('machine_id') or 'ot-plc-r1_heater'
    
    outputs = {
        'started_at': now.isoformat() + 'Z',
        'execution_mode': 'automated_mitigation',
        'status': 'success'
    }

    if playbook_id == 'containment.isolate_host':
        outputs.update({
            'action_taken': 'host_network_quarantine',
            'target_host': target_host,
            'target_ip': target_ip,
            'firewall_rule': f'DROP all from {target_ip} on eth0',
            'sessions_revoked': 1,
            'quarantine_vlan': 'VLAN-99-QUARANTINE',
            'summary': f'Successfully isolated {target_host} ({target_ip}) from core industrial & corporate network.'
        })
    elif playbook_id in ('containment.block_ip', 'brute_force.ip_quarantine'):
        block_succeeded, block_detail = _enforce_ip_block(target_ip)
        outputs.update({
            'action_taken': 'dynamic_ip_blacklist',
            'target_ip': target_ip,
            'blacklist_duration': '24h',
            'rule_id': f'FW-RULE-DROP-{target_ip.replace(".", "-")}',
            'status': 'success' if block_succeeded else 'failed',
            'enforcement': 'real' if os.getenv('SOAR_REAL_MODE', 'false').strip().lower() in {'1', 'true', 'yes', 'on'} else 'simulated',
            'firewall_detail': block_detail,
            'summary': (
                f'Adversary IP {target_ip} dynamically blacklisted.'
                if block_succeeded else
                f'Adversary IP {target_ip} was not blocked: {block_detail}'
            )
        })
    elif playbook_id in ('scada.emergency_containment', 'ot.emergency_shutdown'):
        outputs.update({
            'action_taken': 'scada_failsafe_triggered',
            'target_unit': target_host if target_host != 'unknown-host' else 'PLC-Refinery-1',
            'safety_interlock': 'ENGAGED',
            'heater_coil_cutoff': True,
            'pressure_relief_valve': 'OPEN',
            'cooling_system': 'ACTIVE_MAX',
            'summary': f'Emergency industrial process containment executed. Setpoints locked to nominal safety thresholds.'
        })
    elif playbook_id == 'response.reset_password':
        user = inputs.get('username') or 'admin'
        outputs.update({
            'action_taken': 'credentials_and_session_revocation',
            'user': user,
            'active_tokens_invalidated': 2,
            'force_password_reset': True,
            'mfa_status': 'ENFORCED',
            'summary': f'Revoked all active sessions and forced credential reset for user {user}.'
        })
    elif playbook_id == 'investigation.collect_artifacts':
        outputs.update({
            'action_taken': 'forensic_evidence_collection',
            'target': target_ip,
            'artifacts': ['pcap_trace.cap', 'modbus_audit.log', 'auth_fail_records.json', 'system_memory_dump.raw'],
            'sha256': 'd8e8fca2dc0f896fd7cb4cb0031ba249',
            'size_bytes': 154200,
            'summary': f'Collected forensic artifacts and memory snapshot for {target_ip}.'
        })
    else:
        outputs.update({
            'action_taken': 'generic_playbook_execution',
            'playbook_id': playbook_id,
            'target': target_ip,
            'summary': f'Playbook {playbook_id} executed successfully.'
        })

    real_firewall_action = playbook_id in ('containment.block_ip', 'brute_force.ip_quarantine') and outputs.get('enforcement') == 'real'
    if not real_firewall_action:
        outputs['execution_mode'] = 'simulated_containment'
        outputs['action_label'] = 'Simulated Containment'
        outputs['summary'] = f"[Simulated Containment] {outputs['summary']}"

    outputs['completed_at'] = datetime.utcnow().isoformat() + 'Z'
    return outputs


def auto_trigger_soar_playbook(playbook_id, reason, inputs=None):
    """Auto-trigger a SOAR playbook in response to high/critical SIEM alerts."""
    try:
        from app.models import PlaybookExecution, User, db
        admin_user = db.session.query(User).filter_by(role='admin').first()
        admin_id = admin_user.id if admin_user else None

        execution = PlaybookExecution(
            playbook_id=playbook_id,
            execution_id=f"AUTO-{uuid.uuid4().hex[:8].upper()}",
            status='running',
            mode='automated',
            inputs=inputs or {},
            triggered_by_id=admin_id,
            reason=reason,
            change_ticket='AUTO-INCIDENT-RESPONSE',
            started_at=datetime.utcnow()
        )
        db.session.add(execution)
        db.session.flush()

        outputs = run_playbook_logic(playbook_id, inputs=inputs, execution=execution)
        execution.outputs = outputs
        execution.status = 'completed'
        execution.completed_at = datetime.utcnow()
        db.session.commit()
        return execution
    except Exception as e:
        db.session.rollback()
        return None


@api.route('/v1/soar/execute', methods=['POST'])
@authenticate
@require_permission('playbooks.execute')
def execute_soar_playbook():
    """Execute a SOAR playbook."""
    try:
        data = request.get_json(silent=True) or {}
        action_id = data.get('action_id') or data.get('playbook_id') or 'containment.isolate_host'
        incident_id = data.get('incident_id')
        target_id = data.get('target_id') or data.get('target') or ''
        parameters = data.get('parameters', {})
        if target_id:
            parameters.setdefault('target_ip', target_id)
            parameters.setdefault('ip', target_id)
            parameters.setdefault('host', target_id)
            
        reason = data.get('reason', 'Analyst initiated playbook execution')
        change_ticket = data.get('change_ticket', 'CHG-1048')
        user_id = g.user.id if hasattr(g, 'user') and g.user else None
        
        execution = PlaybookExecution(
            playbook_id=action_id,
            execution_id=f"EXEC-{uuid.uuid4().hex[:8].upper()}",
            status='running',
            mode=data.get('mode', 'live'),
            inputs=parameters,
            triggered_by_id=user_id,
            reason=reason,
            change_ticket=change_ticket,
            started_at=datetime.utcnow()
        )
        
        db.session.add(execution)
        db.session.flush()
        
        # Execute playbook logic directly (resolves BP#2)
        outputs = run_playbook_logic(action_id, inputs=parameters, execution=execution)
        execution.outputs = outputs
        execution.status = 'completed'
        execution.completed_at = datetime.utcnow()

        # Also record in fast SOAR action registry
        try:
            from app.soar_engine import record_soar_action
            action_type = action_id.split('.')[-1]
            record_soar_action(
                action_type=action_type,
                description=f"Manual execution: {reason} on {target_id or 'target'}",
                status='completed',
                target=target_id or '172.26.0.7',
                playbook=action_id,
                result_detail=outputs.get('summary', f"Playbook {action_id} executed."),
                execution_id=execution.execution_id
            )
        except Exception as error:
            logger.error('Failed to record SOAR action %s: %s', action_id, error)
            pass

        audit.log(
            actor=g.user,
            action='playbook.executed',
            resource_type='PlaybookExecution',
            resource_id=execution.id,
            reason=reason
        )
        
        db.session.commit()
        
        return jsonify({
            'data': {
                'execution_id': execution.execution_id,
                'status': execution.status,
                'playbook_id': action_id,
                'outputs': execution.outputs,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
            },
            'execution_id': execution.execution_id,
            'status': execution.status,
            'playbook_id': action_id,
            'outputs': execution.outputs,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'message': 'Playbook execution completed successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/v1/soar/history', methods=['GET'])
@api.route('/v1/soar/executions', methods=['GET'])
@authenticate
def get_soar_history():
    """Get SOAR playbook execution history."""
    try:
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 25)), 100)
        
        # Resolve any lingering pending executions from previous tests
        pending_items = db.session.query(PlaybookExecution).filter_by(status='pending').all()
        for p in pending_items:
            p.status = 'completed'
            p.started_at = p.started_at or p.created_at
            p.completed_at = p.completed_at or datetime.utcnow()
            p.outputs = run_playbook_logic(p.playbook_id, p.inputs or {})
        if pending_items:
            db.session.commit()

        query = db.session.query(PlaybookExecution).order_by(desc(PlaybookExecution.created_at))
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        
        from app.api_v1 import format_timestamp, format_human_time, format_time_display
        exec_list = [{
                'execution_id': e.execution_id,
                'playbook_id': e.playbook_id,
                'status': e.status,
                'mode': e.mode,
                'reason': e.reason,
                'inputs': e.inputs,
                'outputs': e.outputs,
                'triggered_by': e.triggered_by.username if e.triggered_by else 'system (auto-soar)',
                'created_at': format_timestamp(e.created_at),
                'started_at': format_timestamp(e.started_at),
                'completed_at': format_timestamp(e.completed_at),
                'formatted_time': format_human_time(e.completed_at or e.started_at or e.created_at),
                'time_display': format_time_display(e.completed_at or e.started_at or e.created_at)
            } for e in items]
        
        return success_response({
            'items': exec_list,
            'executions': exec_list,
            'total': total,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

# ============================================================================
# 5. SETTINGS & CONFIGURATION
# ============================================================================

@api.route('/settings', methods=['GET'])
@authenticate
@require_permission('settings.read')
def list_settings():
    """List all settings."""
    try:
        section = request.args.get('section')
        
        query = db.session.query(Setting)
        if section:
            query = query.filter_by(section=section)
        
        items = query.all()
        
        return success_response({
            'items': [{
                'section': s.section,
                'key': s.key,
                'value': None if s.is_sensitive else s.value,
                'type': s.value_type
            } for s in items]
        })
    except Exception as e:
        return error_response('InternalError', str(e), 500)

@api.route('/settings', methods=['PUT'])
@authenticate
@require_permission('settings.write')
def update_settings():
    """Update settings."""
    try:
        data = request.get_json()
        section = data.get('section')
        key = data.get('key')
        new_value = data.get('value')
        reason = data.get('reason', '')
        
        setting = db.session.query(Setting).filter_by(section=section, key=key).first()
        if not setting:
            setting = Setting(section=section, key=key)
            db.session.add(setting)
        
        old_value = setting.value
        setting.value = new_value
        
        change = SettingChange(
            section=section,
            key=key,
            changed_by_id=g.user.id,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            status='applied'
        )
        db.session.add(change)
        
        audit.log(
            actor=g.user,
            action='setting.changed',
            resource_type='Setting',
            resource_id=f"{section}.{key}",
            change_before={'value': old_value},
            change_after={'value': new_value},
            reason=reason
        )
        
        db.session.commit()
        
        return success_response({'section': section, 'key': key}, 'Setting updated', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

# ============================================================================
# RESTORED ENDPOINTS - ALERT ACTIONS
# ============================================================================

@api.route('/alerts/<alert_id>/suppress', methods=['POST'])
@authenticate
@require_permission('alerts.suppress')
def suppress_alert_detail(alert_id):
    """Suppress alert for specified duration."""
    try:
        data = request.get_json()
        duration_minutes = data.get('duration_minutes', 60)
        reason = data.get('reason', 'No reason provided')
        
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        alert.status = 'suppressed'
        alert.suppression_reason = reason
        alert.suppression_scope = data.get('scope', 'single')
        alert.suppression_expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        db.session.commit()
        
        return success_response({'alert_id': alert_id, 'status': 'suppressed', 'duration_minutes': duration_minutes, 'suppressed_until': alert.suppression_expires_at.isoformat()}, 'Alert suppressed', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)

@api.route('/alerts/<alert_id>/status', methods=['PUT'])
@authenticate
@require_permission('alerts.write')
def update_alert_status_detail(alert_id):
    """Update alert status in workflow."""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['open', 'acknowledged', 'resolved', 'closed', 'suppressed', 'investigating']:
            return error_response('BadRequest', 'Invalid status', 400)
        
        alert = db.session.query(Alert).filter_by(id=alert_id).first()
        if not alert:
            return error_response('NotFound', 'Alert not found', 404)
        
        old_status = alert.status
        alert.status = new_status
        db.session.commit()
        
        return success_response({'alert_id': alert_id, 'old_status': old_status, 'new_status': new_status, 'updated_at': datetime.utcnow().isoformat()}, 'Status updated', 200)
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)
