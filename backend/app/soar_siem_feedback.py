#!/usr/bin/env python3
"""
SOAR to SIEM Feedback Integration
Sends automation results back to SIEM via REST API endpoints
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger('soar_siem_feedback')
logger.setLevel(logging.INFO)

# SIEM API Configuration
SIEM_BASE_URL = 'http://localhost:5000/api'
SIEM_AUTH_HEADER = {'X-User-ID': 'admin', 'Content-Type': 'application/json'}
REQUEST_TIMEOUT = 10

# Session with retry strategy for resilience
def get_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "PUT", "GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

session = get_session()

def send_feedback_to_siem(feedback_type: str, data: Dict[str, Any]) -> bool:
    """
    Send SOAR automation feedback to SIEM
    
    feedback_type options:
    - 'alert_status_update': Update alert status after SOAR action
    - 'incident_created': Notify SIEM of auto-created incident
    - 'task_created': Notify SIEM of auto-created task
    - 'soar_action_completed': Report playbook execution result
    - 'containment_status': Report containment action status
    """
    try:
        if feedback_type == 'alert_status_update':
            return _update_alert_status(data)
        elif feedback_type == 'incident_created':
            return _notify_incident_created(data)
        elif feedback_type == 'task_created':
            return _notify_task_created(data)
        elif feedback_type == 'soar_action_completed':
            return _report_soar_action(data)
        elif feedback_type == 'containment_status':
            return _report_containment(data)
        else:
            logger.warning(f"Unknown feedback type: {feedback_type}")
            return False
    except Exception as e:
        logger.error(f"SOAR feedback error ({feedback_type}): {str(e)}")
        return False

def _update_alert_status(data: Dict[str, Any]) -> bool:
    """Update alert status in SIEM after SOAR action"""
    alert_id = data.get('alert_id')
    status = data.get('status', 'investigating')
    notes = data.get('notes', 'SOAR automation executed')
    
    if not alert_id:
        logger.warning("Missing alert_id for status update")
        return False
    
    try:
        url = f"{SIEM_BASE_URL}/alerts/{alert_id}/status"
        payload = {
            'status': status,
            'notes': notes,
            'soar_processed': True,
            'soar_action': data.get('action_type'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        response = session.put(url, json=payload, headers=SIEM_AUTH_HEADER, timeout=REQUEST_TIMEOUT)
        
        if response.status_code in [200, 204]:
            logger.info(f"✓ Alert {alert_id} status updated to '{status}' in SIEM")
            return True
        else:
            logger.warning(f"Alert status update failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to update alert status: {str(e)}")
        return False

def _notify_incident_created(data: Dict[str, Any]) -> bool:
    """Notify SIEM when SOAR creates an incident"""
    incident_id = data.get('incident_id')
    alert_ids = data.get('source_alert_ids', [])
    
    if not incident_id:
        logger.warning("Missing incident_id for notification")
        return False
    
    try:
        # Use status endpoint to update incident with SOAR metadata
        url = f"{SIEM_BASE_URL}/incidents/{incident_id}/status"
        payload = {
            'status': data.get('status', 'investigating'),
            'soar_auto_created': True,
            'soar_created_at': datetime.utcnow().isoformat(),
            'soar_reason': data.get('reason', 'Automatic incident creation from alert correlation'),
            'linked_alerts': alert_ids,
            'automation_metadata': {
                'source': 'SOAR',
                'trigger': data.get('trigger', 'alert_correlation'),
                'playbooks_executed': data.get('playbooks', [])
            }
        }
        
        # Update incident status via PUT endpoint
        response = session.put(url, json=payload, headers=SIEM_AUTH_HEADER, timeout=REQUEST_TIMEOUT)
        
        if response.status_code in [200, 204]:
            logger.info(f"✓ Incident {incident_id} created notification sent to SIEM")
            return True
        else:
            logger.warning(f"Incident notification failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to notify incident creation: {str(e)}")
        return False

def _notify_task_created(data: Dict[str, Any]) -> bool:
    """Notify SIEM when SOAR creates a task"""
    incident_id = data.get('incident_id')
    task_data = data.get('task_data', {})
    
    if not incident_id:
        logger.warning("Missing incident_id for task notification")
        return False
    
    try:
        url = f"{SIEM_BASE_URL}/incidents/{incident_id}/tasks"
        payload = {
            'title': task_data.get('title', 'SOAR Automated Task'),
            'description': task_data.get('description', 'Auto-generated from SOAR playbook'),
            'priority': task_data.get('priority', 'high'),
            'status': task_data.get('status', 'open'),
            'soar_generated': True,
            'playbook_id': data.get('playbook_id'),
            'execution_id': data.get('execution_id'),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        response = session.post(url, json=payload, headers=SIEM_AUTH_HEADER, timeout=REQUEST_TIMEOUT)
        
        if response.status_code in [200, 201]:
            logger.info(f"✓ Task notification sent to SIEM for incident {incident_id}")
            return True
        else:
            logger.warning(f"Task notification failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to notify task creation: {str(e)}")
        return False

def _report_soar_action(data: Dict[str, Any]) -> bool:
    """Report SOAR action completion to SIEM"""
    alert_id = data.get('alert_id')
    
    try:
        url = f"{SIEM_BASE_URL}/alerts/{alert_id}/status"
        payload = {
            'status': data.get('status', 'investigating'),
            'soar_action': {
                'type': data.get('action_type'),
                'playbook': data.get('playbook_id'),
                'execution_id': data.get('execution_id'),
                'result': data.get('result', 'success'),
                'detail': data.get('detail'),
                'completed_at': datetime.utcnow().isoformat()
            }
        }
        
        response = session.put(url, json=payload, headers=SIEM_AUTH_HEADER, timeout=REQUEST_TIMEOUT)
        
        if response.status_code in [200, 204]:
            logger.info(f"✓ SOAR action result reported to SIEM for alert {alert_id}")
            return True
        else:
            logger.warning(f"SOAR action report failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to report SOAR action: {str(e)}")
        return False

def _report_containment(data: Dict[str, Any]) -> bool:
    """Report containment action status to SIEM"""
    alert_id = data.get('alert_id')
    incident_id = data.get('incident_id')
    
    try:
        # Report to alert
        if alert_id:
            url = f"{SIEM_BASE_URL}/alerts/{alert_id}/status"
            payload = {
                'status': 'contained',
                'containment': {
                    'type': data.get('containment_type'),
                    'target': data.get('target'),
                    'action': data.get('action'),
                    'status': data.get('containment_status', 'success'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            response = session.put(url, json=payload, headers=SIEM_AUTH_HEADER, timeout=REQUEST_TIMEOUT)
            
            if response.status_code in [200, 204]:
                logger.info(f"✓ Containment status reported to SIEM for alert {alert_id}")
                return True
        
        return False
    except Exception as e:
        logger.error(f"Failed to report containment: {str(e)}")
        return False

def sync_soar_incident_to_siem(incident_id: str, incident_data: Dict[str, Any]) -> bool:
    """
    Full sync of SOAR incident data to SIEM via status endpoint
    """
    try:
        url = f"{SIEM_BASE_URL}/incidents/{incident_id}/status"
        payload = {
            'status': incident_data.get('status', 'investigating'),
            'soar_metadata': {
                'auto_created': True,
                'created_at': incident_data.get('created_at'),
                'tasks_count': incident_data.get('tasks_count', 0),
                'playbooks_executed': incident_data.get('playbooks_executed', []),
                'containment_status': incident_data.get('containment_status'),
                'evidence_collected': incident_data.get('evidence_collected', False)
            }
        }
        
        response = session.put(url, json=payload, headers=SIEM_AUTH_HEADER, timeout=REQUEST_TIMEOUT)
        
        if response.status_code in [200, 204]:
            logger.info(f"✓ Incident {incident_id} synced to SIEM")
            return True
        else:
            logger.warning(f"Incident sync failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to sync incident to SIEM: {str(e)}")
        return False

def query_siem_for_high_priority_incidents() -> list:
    """
    Query SIEM for high-priority incidents that need SOAR action
    """
    try:
        url = f"{SIEM_BASE_URL}/incidents?severity=critical&status=open&page_size=50"
        response = session.get(url, headers=SIEM_AUTH_HEADER, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            incidents = data.get('data', [])
            logger.info(f"✓ Queried SIEM: Found {len(incidents)} critical incidents")
            return incidents
        else:
            logger.warning(f"SIEM query failed: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Failed to query SIEM: {str(e)}")
        return []

def get_alert_context_from_siem(alert_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve alert context from SIEM for enriched processing
    """
    try:
        url = f"{SIEM_BASE_URL}/alerts/{alert_id}"
        response = session.get(url, headers=SIEM_AUTH_HEADER, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            alert = response.json().get('data', {})
            logger.info(f"✓ Retrieved alert context for {alert_id}")
            return alert
        else:
            logger.warning(f"Alert context retrieval failed: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Failed to get alert context: {str(e)}")
        return None

if __name__ == '__main__':
    # Test the integration
    print("SOAR-SIEM Feedback Integration Module Loaded")
    print("Available functions:")
    print("  - send_feedback_to_siem()")
    print("  - sync_soar_incident_to_siem()")
    print("  - query_siem_for_high_priority_incidents()")
    print("  - get_alert_context_from_siem()")
