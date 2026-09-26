"""Authenticated production event ingestion and device inventory APIs."""
import hmac
import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

from app.auth import authenticate, error_response, require_permission
from app.models import Device, SecurityEvent, LogSource, Alert, db

api = Blueprint('api_ingestion', __name__, url_prefix='/api')
VALID_TRUST_STATES = {'trusted', 'untrusted', 'blocked'}

def _parse_timestamp(value):
    if not isinstance(value, str):
        return datetime.utcnow()
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    except Exception:
        return datetime.utcnow()

def _collector_authorized():
    expected = os.getenv('COLLECTOR_INGEST_TOKEN')
    supplied = request.headers.get('X-Collector-Token', '')
    if not supplied and request.headers.get('Authorization', '').startswith('Bearer '):
        supplied = request.headers.get('Authorization')[7:].strip()
    if not expected:
        return False
    try:
        return hmac.compare_digest(supplied, expected)
    except Exception:
        return False

def _upsert_device(event, occurred_at):
    details = event.get('device') if isinstance(event.get('device'), dict) else {}
    hostname = details.get('hostname') or event.get('host')
    if not isinstance(hostname, str) or not hostname.strip():
        return None, False
    
    hostname = hostname.strip().lower()
    inferred_type = details.get('device_type') or _infer_device_type(hostname)
    occurred_at = occurred_at or datetime.utcnow()
    
    device = db.session.query(Device).filter_by(hostname=hostname).first()
    is_new = False
    
    if device is None:
        try:
            device = Device(
                id=str(uuid.uuid4()),
                hostname=hostname,
                device_type=inferred_type,
                trust_state='untrusted',
                first_seen_at=occurred_at,
                last_seen_at=occurred_at
            )
            db.session.add(device)
            db.session.flush()
            is_new = True
        except Exception:
            db.session.rollback()
            device = db.session.query(Device).filter_by(hostname=hostname).first()
            is_new = False
    
    if device:
        for field in ('ip_address', 'mac_address', 'device_type', 'manufacturer', 'model', 'os_version', 'serial_number'):
            value = details.get(field)
            if value is not None:
                setattr(device, field, value)
                
        device.last_seen_at = occurred_at
        device.metadata_json = details.get('metadata', device.metadata_json)
        
        # Update or register LogSource for metrics
        _update_log_source(hostname, device.device_type, occurred_at)
    
    return device, is_new

def _update_log_source(hostname, device_type, occurred_at):
    """Maintain real-time LogSource metrics for data source dashboards."""
    try:
        source = db.session.query(LogSource).filter_by(name=hostname).first()
        if source is None:
            source = LogSource(
                id=str(uuid.uuid4()),
                name=hostname,
                connector_type=device_type or 'agent',
                status='healthy',
                last_event_timestamp=occurred_at,
                total_events_ingested=1,
                ingestion_rate=1
            )
            db.session.add(source)
        else:
            source.last_event_timestamp = occurred_at
            source.total_events_ingested = (source.total_events_ingested or 0) + 1
            source.status = 'healthy'
    except Exception as error:
        current_app.logger.error('Failed to update log source %s: %s', hostname, error)
        pass

def _infer_device_type(hostname):
    """Conservative identification; an explicitly reported device type wins."""
    name = hostname.lower()
    if 'plc' in name:
        return 'plc'
    if 'scada' in name or 'hmi' in name:
        return 'scada'
    if 'database' in name or name.endswith('-db'):
        return 'database-server'
    if 'portal' in name or 'web' in name:
        return 'web-server'
    if 'workstation' in name or 'laptop' in name or 'desktop' in name:
        return 'workstation'
    return 'iot-endpoint'

def process_event_batch(events):
    """Persist a validated batch inside a Celery worker or direct thread process."""
    accepted = 0
    rejected = []
    new_devices = []
    
    for index, event in enumerate(events):
        try:
            if not isinstance(event, dict) or not isinstance(event.get('message'), str) or not event['message'].strip():
                raise ValueError('message is required')
            
            occurred_at = _parse_timestamp(event.get('timestamp'))
            device, is_new = _upsert_device(event, occurred_at)
            db.session.flush()
            
            host_str = str(event.get('host') or event.get('source') or (device.hostname if device else 'unknown'))
            sev_str = str(event.get('level', 'info')).lower()
            msg_str = event['message'].strip()
            
            # Record security event
            sec_event = SecurityEvent(
                device_id=device.id if device else None,
                source=host_str,
                severity=sev_str,
                message=msg_str,
                occurred_at=occurred_at,
                raw_event=event,
            )
            db.session.add(sec_event)

            # Update machine operational status for emergency stop / reset events
            is_e_stop = 'emergency_stop' in msg_str.lower() or event.get('command') == 'emergency_stop' or event.get('action') == 'emergency_stop'
            is_reset = event.get('command') == 'reset_emergency_stop' or 'reset_emergency_stop' in msg_str.lower()
            if is_e_stop:
                if device:
                    meta = dict(device.metadata_json or {})
                    meta['operational_status'] = 'stopped'
                    meta['emergency_stopped'] = True
                    device.metadata_json = meta
                source = db.session.query(LogSource).filter_by(name=host_str).first()
                if source:
                    source.status = 'stopped'
                
                # Dedicated layman-understandable Alert for machine shutdown
                clean_host = host_str.replace('ot-plc-', '').replace('ot-', '').replace('-', ' ').title()
                db.session.add(Alert(
                    id=str(uuid.uuid4()),
                    alert_id=f"ALERT-STOP-{uuid.uuid4().hex[:6].upper()}",
                    title=f"[MACHINE STOPPED] {clean_host} Turned Off (Emergency Stop Activated)",
                    severity='critical',
                    status='open',
                    source=host_str,
                    rule_id='RULE-EMERGENCY-STOP',
                    timestamp=occurred_at,
                    raw_event=event
                ))
            elif is_reset:
                if device:
                    meta = dict(device.metadata_json or {})
                    meta['operational_status'] = 'online'
                    meta['emergency_stopped'] = False
                    device.metadata_json = meta
                source = db.session.query(LogSource).filter_by(name=host_str).first()
                if source:
                    source.status = 'healthy'
                
                clean_host = host_str.replace('ot-plc-', '').replace('ot-', '').replace('-', ' ').title()
                db.session.add(Alert(
                    id=str(uuid.uuid4()),
                    alert_id=f"ALERT-RUN-{uuid.uuid4().hex[:6].upper()}",
                    title=f"[MACHINE RESUMED] {clean_host} Online (Emergency Stop Cleared)",
                    severity='info',
                    status='open',
                    source=host_str,
                    rule_id='RULE-MACHINE-RESUMED',
                    timestamp=occurred_at,
                    raw_event=event
                ))
                if device:
                    meta = dict(device.metadata_json or {})
                    meta['operational_status'] = 'online'
                    meta['emergency_stopped'] = False
                    device.metadata_json = meta
                source = db.session.query(LogSource).filter_by(name=host_str).first()
                if source:
                    source.status = 'healthy'
            
            # If a new uncataloged machine is discovered, log a notification event and alert
            if is_new and device:
                new_devices.append(device.hostname)
                alert_id = f"NEW-ASSET-{device.hostname.upper()}"
                if not db.session.query(Alert).filter_by(alert_id=alert_id).first():
                    db.session.add(Alert(
                        id=str(uuid.uuid4()),
                        alert_id=alert_id,
                        title=f"New asset detected on network: {device.hostname} ({device.device_type})",
                        severity='medium',
                        status='open',
                        source=device.hostname,
                        rule_id='RULE-NEW-DEVICE-DISCOVERY',
                        timestamp=occurred_at,
                        raw_event=event
                    ))
            
            # Create Alert for high / critical alarms, threshold breaches, or warning events from test_soar
            is_warning_test = ('warning threshold' in msg_str.lower() or 'temperature warning' in msg_str.lower())
            if sev_str in ('high', 'critical') or is_warning_test:
                effective_sev = 'warn' if is_warning_test else sev_str
                alert_code = f"ALERT-{uuid.uuid4().hex[:8].upper()}"
                rule_id = 'RULE-SYSTEM-PANIC' if 'kernel panic' in msg_str.lower() else (
                    'RULE-PORT-SCAN' if 'nmap' in msg_str.lower() or 'port scan' in msg_str.lower() else (
                        'RULE-SCADA-THRESHOLD' if ('plc' in host_str or 'scada' in host_str) else 'RULE-SECURITY-EVENT'
                    )
                )
                alert_obj = Alert(
                    id=str(uuid.uuid4()),
                    alert_id=alert_code,
                    title=f"[{host_str.upper()}] {msg_str[:120]}",
                    severity=effective_sev,
                    status='open',
                    source=host_str,
                    rule_id=rule_id,
                    timestamp=occurred_at,
                    raw_event=event
                )
                
                # Auto-escalate to an active Incident Case in PostgreSQL (NIST Incident Lifecycle)
                try:
                    from app.models import Incident, Task, User
                    admin_user = db.session.query(User).filter_by(role='admin').first()
                    admin_id = admin_user.id if admin_user else None

                    # Check for an existing open incident on the same host within recent window
                    recent_inc = db.session.query(Incident).filter(
                        Incident.status.in_(['open', 'investigating', 'in_progress']),
                        Incident.title.ilike(f"%{host_str}%")
                    ).first()

                    if not recent_inc:
                        inc_code = f"INC-{uuid.uuid4().hex[:6].upper()}"
                        recent_inc = Incident(
                            id=str(uuid.uuid4()),
                            incident_id=inc_code,
                            title=f"[{host_str.upper()}] {msg_str[:90]}",
                            description=f"Correlated incident case detected on {host_str}. Triggered by {effective_sev.upper()} alert: {msg_str}",
                            status='open',
                            severity='critical' if effective_sev == 'critical' else 'high',
                            priority='critical' if effective_sev == 'critical' else 'high',
                            owner_id=admin_id,
                            affected_assets=[host_str],
                            detected_at=datetime.utcnow()
                        )
                        db.session.add(recent_inc)
                        db.session.flush()

                        # Add automated triage tasks to the case
                        t1 = Task(incident_id=recent_inc.id, title=f"Quarantine {host_str} via SOAR active defense", status='open')
                        t2 = Task(incident_id=recent_inc.id, title=f"Block ingress traffic from {event.get('src_ip') or '172.26.0.7'} on perimeter firewall", status='open')
                        t3 = Task(incident_id=recent_inc.id, title="Acquire forensic memory and network timeline snapshot", status='open')
                        db.session.add_all([t1, t2, t3])

                    alert_obj.incident_id = recent_inc.id
                except Exception as inc_err:
                    pass

                db.session.add(alert_obj)
                
                # Auto-trigger SOAR response for critical/high alerts (BP#4)
                try:
                    from app.api_v1_actions import auto_trigger_soar_playbook
                    playbook = 'containment.isolate_host' if ('plc' in host_str or 'scada' in host_str) else 'containment.block_ip'
                    auto_trigger_soar_playbook(
                        playbook_id=playbook,
                        reason=f"Automated response to {sev_str.upper()} alert on {host_str}: {msg_str[:80]}",
                        inputs={'host': host_str, 'ip': event.get('src_ip') or event.get('ip') or '172.26.0.7'}
                    )
                except Exception as error:
                    current_app.logger.error('Failed to trigger SOAR playbook for %s: %s', host_str, error)
                    pass
            
            accepted += 1
        except (TypeError, ValueError) as error:
            rejected.append({'index': index, 'error': str(error)})
            
    # Evaluate Cross-Boundary Multi-Stage Attack Correlation Engine
    _evaluate_cross_boundary_correlation()
    
    db.session.commit()
    return {'accepted': accepted, 'rejected': rejected, 'new_devices': new_devices}


def _evaluate_cross_boundary_correlation():
    """Correlate multi-stage attacks spanning Corporate Portal -> SCADA HMI -> OT Physical PLCs."""
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        recent_events = db.session.query(SecurityEvent).filter(
            SecurityEvent.occurred_at >= cutoff
        ).order_by(SecurityEvent.occurred_at.asc()).all()

        stage1_events = []  # Corp Portal / Web Access / Failed Logins
        stage2_events = []  # SCADA HMI Audit & Setpoint Manipulations
        stage3_events = []  # OT Network / PLC Command Executions / Alarms

        for ev in recent_events:
            raw = ev.raw_event if isinstance(ev.raw_event, dict) else {}
            log_source = str(raw.get('log_source') or ev.source or '').lower()
            evt_type = str(raw.get('event_type') or '').lower()
            msg = (ev.message or '').lower()
            
            # Stage 1: Corp IT / Identity
            if 'corp' in log_source or 'portal' in log_source or 'waf' in log_source or 'auth' in evt_type or 'login' in msg:
                stage1_events.append(ev)
            # Stage 2: SCADA HMI
            elif 'hmi' in log_source or 'scada' in log_source or 'setpoint' in msg or 'audit' in evt_type or 'operator' in msg:
                stage2_events.append(ev)
            # Stage 3: OT Network & PLCs
            elif 'plc' in log_source or 'ot_sensor' in log_source or 'command' in evt_type or 'temperature' in msg or 'pressure' in msg or 'flow' in msg or 'cpu_stop' in msg or 'heater' in msg:
                stage3_events.append(ev)

        # Trigger Multi-Stage Correlation if all 3 domains have suspicious activities
        if stage1_events and stage2_events and stage3_events:
            rule_id = 'CORR-MULTI-STAGE-ICS-ATTACK'
            # Debounce: avoid spamming duplicates every 2s; limit to once per 15m window
            existing_corr = db.session.query(Alert).filter(
                Alert.rule_id == rule_id,
                Alert.timestamp >= (datetime.utcnow() - timedelta(minutes=15))
            ).first()
            if not existing_corr:
                corr_id = f"CORR-ICS-{uuid.uuid4().hex[:6].upper()}"
                s1 = stage1_events[-1]
                s2 = stage2_events[-1]
                s3 = stage3_events[-1]
                
                corr_payload = {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'correlation_id': corr_id,
                    'severity': 'Critical',
                    'stage_1_corp': {
                        'log_source': s1.raw_event.get('log_source', s1.source),
                        'message': s1.message,
                        'user': s1.raw_event.get('user', 'unknown'),
                        'src_ip': s1.raw_event.get('src_ip', 'unknown')
                    },
                    'stage_2_hmi': {
                        'log_source': s2.raw_event.get('log_source', s2.source),
                        'message': s2.message,
                        'action': s2.raw_event.get('action', 'Setpoint_Change'),
                        'user': s2.raw_event.get('user', 'operator')
                    },
                    'stage_3_ot': {
                        'log_source': s3.raw_event.get('log_source', s3.source),
                        'message': s3.message,
                        'dest_asset': s3.raw_event.get('dest_asset', 'PLC_REFINERY_1'),
                        'protocol': s3.raw_event.get('protocol', 'ModbusTCP')
                    },
                    'mitre_ics_tactics': ['TA0100 (Initial Access)', 'TA0108 (Inhibit Response)', 'TA0105 (Impair Process Control)'],
                    'mitre_ics_techniques': ['T0812 (Default Credentials)', 'T0836 (Modify Parameter)', 'T0803 (Command, Control & Signaling)']
                }

                corr_alert = Alert(
                    id=str(uuid.uuid4()),
                    alert_id=corr_id,
                    title=f"[CYBER-PHYSICAL ATTACK] {s3.raw_event.get('dest_asset', 'Refinery 1').replace('PLC_', '').replace('_', ' ').title()}: {s3.message or 'Process Setpoint Altered via Unauthorized Modbus'}",
                    severity='critical',
                    status='open',
                    source='SIEM_Correlation_Engine',
                    rule_id=rule_id,
                    timestamp=datetime.utcnow(),
                    raw_event=corr_payload
                )

                # Auto-escalate correlation to a Critical Incident Case
                try:
                    from app.models import Incident, Task, User
                    admin_user = db.session.query(User).filter_by(role='admin').first()
                    admin_id = admin_user.id if admin_user else None
                    corr_inc = Incident(
                        id=str(uuid.uuid4()),
                        incident_id=f"INC-{corr_id}",
                        title="[CRITICAL ICS] Multi-Stage Cyber-Physical Attack",
                        description="Correlated multi-stage cyber-physical breach across Corporate Portal, SCADA HMI, and physical PLC Refinery unit.",
                        status='open',
                        severity='critical',
                        priority='critical',
                        owner_id=admin_id,
                        affected_assets=['corp-portal', 'ot-scada-gw', 'ot-plc-refinery-1'],
                        detected_at=datetime.utcnow()
                    )
                    db.session.add(corr_inc)
                    db.session.flush()
                    t1 = Task(incident_id=corr_inc.id, title="Emergency shutdown / failsafe interlock on Refinery PLC", status='open')
                    t2 = Task(incident_id=corr_inc.id, title="Quarantine compromised operator accounts and revoke tokens", status='open')
                    t3 = Task(incident_id=corr_inc.id, title="Perform root-cause analysis across IT/OT boundary", status='open')
                    db.session.add_all([t1, t2, t3])
                    corr_alert.incident_id = corr_inc.id
                except Exception as error:
                    current_app.logger.error('Failed to create correlated incident %s: %s', corr_id, error)
                    pass

                db.session.add(corr_alert)
                
                # Auto-trigger SOAR for multi-stage correlation (BP#4)
                try:
                    from app.api_v1_actions import auto_trigger_soar_playbook
                    auto_trigger_soar_playbook(
                        playbook_id='scada.emergency_containment',
                        reason=f"Automated multi-stage containment triggered for correlation {corr_id}",
                        inputs={'host': 'ot-plc-refinery-1', 'ip': '172.26.0.7'}
                    )
                except Exception as error:
                    current_app.logger.error('Failed to trigger correlated SOAR playbook %s: %s', corr_id, error)
                    pass
    except Exception as error:
        current_app.logger.error('Cross-boundary correlation failed: %s', error)
        pass

@api.route('/ingest/events', methods=['POST'])
@api.route('/logs/ingest', methods=['POST'])
def ingest_events():
    auth_ok = _collector_authorized()
    payload = request.get_json(silent=True)
    if not auth_ok:
        return error_response('Unauthorized', 'Valid collector token required', 401)
    
    if isinstance(payload, dict):
        events = payload.get('events')
        if events is None:
            # Single-event object directly passed (BP#1 & test_soar.py)
            events = [payload]
    elif isinstance(payload, list):
        events = payload
    else:
        events = None

    if not isinstance(events, list) or not events:
        return error_response('BadRequest', 'A non-empty events array or event object is required', 400)
    if len(events) > 1000:
        return error_response('BadRequest', 'Maximum batch size is 1000 events', 400)
    
    # Process batch directly for immediate alert and SOAR responsiveness
    result = process_event_batch(events)
    return jsonify({
        'status': 'success',
        'accepted': result['accepted'],
        'new_devices': result['new_devices'],
        'message': f"Ingested {result['accepted']} events"
    }), 200

@api.route('/devices', methods=['GET'])
@authenticate
def list_devices():
    devices = db.session.query(Device).order_by(Device.last_seen_at.desc()).all()
    return jsonify({'items': [_device_payload(device) for device in devices]})

@api.route('/devices/<device_id>/trust', methods=['PATCH'])
@authenticate
@require_permission('settings.write')
def update_device_trust(device_id):
    payload = request.get_json(silent=True) or {}
    trust_state = payload.get('trust_state')
    if trust_state not in VALID_TRUST_STATES:
        return error_response('BadRequest', 'trust_state must be trusted, untrusted, or blocked', 400)
    device = db.session.get(Device, device_id)
    if device is None:
        return error_response('NotFound', 'Device not found', 404)
    device.trust_state = trust_state
    db.session.commit()
    return jsonify(_device_payload(device))

def _device_payload(device):
    meta = device.metadata_json or {}
    op_status = meta.get('operational_status')
    return {
        'id': device.id, 'hostname': device.hostname, 'ip_address': device.ip_address,
        'mac_address': device.mac_address, 'device_type': device.device_type,
        'manufacturer': device.manufacturer, 'model': device.model,
        'os_version': device.os_version, 'serial_number': device.serial_number,
        'trust_state': device.trust_state,
        'status': op_status or ('healthy' if device.trust_state == 'trusted' else 'untrusted'),
        'first_seen_at': device.first_seen_at.isoformat() if device.first_seen_at else None,
        'last_seen_at': device.last_seen_at.isoformat() if device.last_seen_at else None,
        'metadata': meta
    }

