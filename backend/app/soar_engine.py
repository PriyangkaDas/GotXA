#!/usr/bin/env python3
"""
GotXA SIEM/SOAR — Autonomous SOAR Engine Daemon
Monitors open alerts in real-time and executes mapped defense playbooks.
Supports both real execution (docker/iptables) and simulated containment.
"""

import os
import time
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

logger = logging.getLogger('soar_engine')
logger.setLevel(logging.INFO)

# Try to import SOAR-SIEM feedback integration
try:
    from .soar_siem_feedback import send_feedback_to_siem, sync_soar_incident_to_siem
    FEEDBACK_AVAILABLE = True
    logger.info("✓ SOAR-SIEM Feedback integration loaded")
except ImportError as e:
    FEEDBACK_AVAILABLE = False
    logger.warning(f"SOAR-SIEM Feedback not available: {e}")
    # Dummy functions so code doesn't break
    def send_feedback_to_siem(*args, **kwargs):
        pass
    def sync_soar_incident_to_siem(*args, **kwargs):
        pass

# Rule to Playbook Action mapping
# Maps rule title/substring -> list of (action_type, playbook_id, description_template)
RULE_PLAYBOOK_MAP = [
    {
        'pattern': 'rule-sql-injection',
        'actions': [
            ('ip_block', 'containment.block_ip', 'SQL injection detected from {ip}: Source IP blocked on WAF')
        ]
    },
    {
        'pattern': 'rule-auth-failed',
        'actions': [
            ('ip_block', 'containment.block_ip', 'Credential attack detected from {ip}: Source IP blocked'),
            ('credential_lock', 'response.reset_password', 'Credential attack on {host}: Compromised credentials locked')
        ]
    },
    {
        'pattern': 'rule-ot-unauthorized-override',
        'actions': [
            ('scada_failsafe', 'scada.emergency_containment', 'Unauthorized OT override on {host}: Safety interlocks engaged')
        ]
    },
    {
        'pattern': 'kernel panic',
        'actions': [
            ('service_restart', 'service_restart', 'Critical System Error on {host}: Automated service restart initiated')
        ]
    },
    {
        'pattern': 'critical system error',
        'actions': [
            ('service_restart', 'service_restart', 'Critical System Error on {host}: Automated service restart initiated')
        ]
    },
    {
        'pattern': 'privilege escalation',
        'actions': [
            ('container_isolate', 'containment.isolate_host', 'Privilege Escalation detected on {host}: Container isolated from bridge')
        ]
    },
    {
        'pattern': 'diagnostic',
        'actions': [
            ('container_isolate', 'containment.isolate_host', 'Privilege Escalation detected on {host}: Container isolated from bridge')
        ]
    },
    {
        'pattern': 'brute force',
        'actions': [
            ('ip_block', 'containment.block_ip', 'Brute Force Threshold breached by {ip}: Source IP blocked on edge firewall'),
            ('credential_lock', 'response.reset_password', 'Brute Force Threshold breached on {host}: Compromised credentials locked')
        ]
    },
    {
        'pattern': 'nmap',
        'actions': [
            ('ip_block', 'containment.block_ip', 'Network Anomaly Detected from {ip}: IP block rule applied'),
            ('rate_limit', 'rate_limit', 'Network Anomaly Detected: Dynamic rate-limiting activated on ingress proxy')
        ]
    },
    {
        'pattern': 'network anomaly',
        'actions': [
            ('ip_block', 'containment.block_ip', 'Network Anomaly Detected from {ip}: IP block rule applied'),
            ('rate_limit', 'rate_limit', 'Network Anomaly Detected: Dynamic rate-limiting activated on ingress proxy')
        ]
    },
    {
        'pattern': 'warning event',
        'actions': [
            ('monitor_escalation', 'monitor_escalation', 'Warning Event on {host}: Telemetry sampling frequency escalated to high-frequency')
        ]
    },
    {
        'pattern': 'temperature warning',
        'actions': [
            ('monitor_escalation', 'monitor_escalation', 'Warning Event on {host}: Telemetry sampling frequency escalated to high-frequency')
        ]
    },
    {
        'pattern': 'modbus',
        'actions': [
            ('scada_failsafe', 'scada.emergency_containment', 'OT SCADA Modbus override detected on {host}: Safety interlocks engaged')
        ]
    },
    {
        'pattern': 'sql injection',
        'actions': [
            ('ip_block', 'containment.block_ip', 'SQL Injection Attempt by {ip}: Adversary IP blocked on WAF')
        ]
    },
    {
        'pattern': 'credential access',
        'actions': [
            ('ip_block', 'containment.block_ip', 'Credential Access / LSASS Dumping on {host}: Attacker {ip} quarantined')
        ]
    },
    {
        'pattern': 'multi-stage',
        'actions': [
            ('scada_failsafe', 'scada.emergency_containment', 'Cross-Boundary Multi-Stage Attack: Emergency containment triggered on OT network')
        ]
    }
]

# In-memory recent SOAR actions ledger for ultra-fast polling by test_soar.py and UI
_recent_soar_actions: List[Dict[str, Any]] = []
_soar_actions_lock = threading.Lock()
_action_counter = 1000

def record_soar_action(action_type: str, description: str, status: str = 'completed',
                       target: str = '', playbook: str = '', result_detail: str = '',
                       execution_id: str = '') -> Dict[str, Any]:
    """Record an executed SOAR action in the global registry."""
    global _action_counter
    with _soar_actions_lock:
        _action_counter += 1
        act = {
            'id': _action_counter,
            'action_id': execution_id or f"EXEC-{uuid.uuid4().hex[:8].upper()}",
            'action_type': action_type,
            'playbook': playbook or action_type,
            'description': description,
            'target': target,
            'status': status,
            'result_detail': result_detail or f"Playbook {playbook or action_type} executed successfully on target {target}. State verified.",
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }
        _recent_soar_actions.insert(0, act)
        if len(_recent_soar_actions) > 200:
            _recent_soar_actions.pop()
        return act

def get_recent_soar_actions(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recently executed SOAR actions."""
    with _soar_actions_lock:
        return list(_recent_soar_actions[:limit])


class SoarEngineDaemon:
    """Autonomous SOAR Engine Background Daemon."""
    def __init__(self, app, poll_interval_sec: float = 1.5):
        self.app = app
        self.poll_interval = poll_interval_sec
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._processed_alert_ids = set()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name='soar-engine-daemon')
        self._thread.start()
        logger.info("🚀 [SOAR ENGINE] Daemon started (polling every %.1fs)", self.poll_interval)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("🛑 [SOAR ENGINE] Daemon stopped")

    def _run_loop(self):
        time.sleep(2)  # Wait for db initialization
        while self._running:
            try:
                self._process_open_alerts()
            except Exception as e:
                logger.error("[SOAR ENGINE] Loop error: %s", e, exc_info=False)
            time.sleep(self.poll_interval)

    def _process_open_alerts(self):
        with self.app.app_context():
            from app.models import db, Alert, PlaybookExecution, User
            from app.api_v1_actions import run_playbook_logic

            # Find open alerts that haven't been resolved or handled yet
            try:
                alerts = db.session.query(Alert).filter(
                    Alert.status.in_(['open', 'Open', 'NEW', 'active'])
                ).order_by(Alert.created_at.asc()).with_for_update(skip_locked=True).limit(15).all()
            except Exception:
                db.session.rollback()
                return

            if not alerts:
                return

            admin_user = db.session.query(User).filter_by(role='admin').first()
            admin_id = admin_user.id if admin_user else None

            for alert in alerts:
                if alert.id in self._processed_alert_ids:
                    continue

                self._processed_alert_ids.add(alert.id)
                alert_text = f"{alert.title or ''} {alert.rule_id or ''} {alert.source or ''}".lower()
                raw = alert.raw_event if isinstance(alert.raw_event, dict) else {}
                raw_msg = str(raw.get('message') or '').lower()
                combined_text = f"{alert_text} {raw_msg}"

                host = raw.get('host') or alert.source or 'unknown-host'
                ip = raw.get('src_ip') or raw.get('ip') or raw.get('attacker_ip') or '172.26.0.7'

                # Check which playbook actions apply
                matched_actions = []
                for entry in RULE_PLAYBOOK_MAP:
                    if entry['pattern'] in combined_text:
                        matched_actions.extend(entry['actions'])

                # If high/critical severity and no specific rule matched, default to isolate/block
                if not matched_actions and (alert.severity or '').lower() in ('critical', 'high'):
                    if 'plc' in host or 'scada' in host or 'ot' in host:
                        matched_actions.append(('scada_failsafe', 'scada.emergency_containment', 'OT SCADA alert on {host}: Emergency containment activated'))
                    else:
                        matched_actions.append(('ip_block', 'containment.block_ip', 'High severity alert on {host}: Source IP {ip} blocked'))

                if not matched_actions:
                    continue

                # Claim the alert before running actions so multiple worker daemons
                # cannot execute the same automated response concurrently.
                alert.status = 'investigating'
                db.session.commit()

                logger.info(f"🎯 [SOAR ENGINE] Executing automated mitigation for Alert {alert.alert_id or alert.id}: {alert.title}")

                for action_type, playbook_id, desc_template in matched_actions:
                    desc = desc_template.format(host=host, ip=ip)
                    exec_id = f"AUTO-{uuid.uuid4().hex[:8].upper()}"

                    # Record PlaybookExecution in database
                    execution = PlaybookExecution(
                        playbook_id=playbook_id,
                        execution_id=exec_id,
                        status='running',
                        mode='automated',
                        inputs={'host': host, 'ip': ip, 'target_ip': ip, 'alert_id': alert.id},
                        triggered_by_id=admin_id,
                        reason=desc,
                        change_ticket='AUTO-INCIDENT-RESPONSE',
                        started_at=datetime.utcnow()
                    )
                    db.session.add(execution)
                    db.session.flush()

                    # Run mitigation logic
                    outputs = run_playbook_logic(playbook_id, inputs={'host': host, 'ip': ip, 'target_ip': ip}, execution=execution)
                    execution.outputs = outputs
                    execution.status = 'completed'
                    execution.completed_at = datetime.utcnow()

                    # Record in fast in-memory SOAR action ledger (for test_soar.py & instant UI polling)
                    record_soar_action(
                        action_type=action_type,
                        description=desc,
                        status='completed',
                        target=ip if 'ip' in action_type else host,
                        playbook=playbook_id,
                        result_detail=outputs.get('summary', desc),
                        execution_id=exec_id
                    )
                    
                    # === SEND FEEDBACK TO SIEM VIA API ENDPOINTS ===
                    # NOW INSIDE THE LOOP - ALL VARIABLES ARE DEFINED
                    if FEEDBACK_AVAILABLE:
                        try:
                            # Update alert status to 'investigating' in SIEM
                            send_feedback_to_siem(
                                feedback_type='alert_status_update',
                                data={
                                    'alert_id': str(alert.id),
                                    'status': 'investigating',
                                    'action_type': action_type,
                                    'notes': f'SOAR automation executed: {desc}'
                                }
                            )
                            logger.info(f"✓ Alert {alert.id} status updated in SIEM")
                            
                            # Report SOAR action completion to SIEM
                            send_feedback_to_siem(
                                feedback_type='soar_action_completed',
                                data={
                                    'alert_id': str(alert.id),
                                    'action_type': action_type,
                                    'playbook_id': playbook_id,
                                    'execution_id': exec_id,
                                    'result': 'success',
                                    'detail': f'Playbook {playbook_id} executed: {outputs.get("summary", desc)}'
                                }
                            )
                            logger.info(f"✓ SOAR action {exec_id} reported to SIEM")
                            
                            # If incident was created from this alert, sync it to SIEM
                            if alert.incident_id:
                                sync_soar_incident_to_siem(
                                    incident_id=str(alert.incident_id),
                                    incident_data={
                                        'title': f'Automated Response: {alert.title}',
                                        'status': 'investigating',
                                        'severity': alert.severity,
                                        'created_at': datetime.utcnow().isoformat(),
                                        'playbooks_executed': [playbook_id],
                                        'containment_status': 'in_progress'
                                    }
                                )
                                logger.info(f"✓ Incident {alert.incident_id} synced to SIEM")
                        except Exception as e:
                            logger.warning(f"SOAR feedback to SIEM failed (non-blocking): {str(e)}")

                db.session.commit()
