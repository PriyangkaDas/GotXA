#!/usr/bin/env python3
"""
Immutable audit logging system.
"""

from datetime import datetime
import uuid
from app.models import AuditEvent, db

class AuditLogger:
    """Logs all mutations with correlation IDs."""
    
    def log(self, actor, action, resource_type, resource_id, change_before=None, 
            change_after=None, reason='', status='success', ip_address=None, user_agent=None):
        """
        Log an audit event.
        
        Args:
            actor: User object performing the action
            action: Action name (e.g., 'alert.suppressed')
            resource_type: Type of resource (Alert, Incident, etc.)
            resource_id: ID of the resource
            change_before: State before change
            change_after: State after change
            reason: Why the action was performed
            status: success/failed
            ip_address: Client IP
            user_agent: Client user agent
        """
        from flask import g, request
        
        event = AuditEvent(
            correlation_id=getattr(g, 'correlation_id', str(uuid.uuid4())),
            actor_id=actor.id if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            change_before=change_before or {},
            change_after=change_after or {},
            reason=reason,
            ip_address=ip_address or (request.remote_addr if request else None),
            user_agent=user_agent or (request.headers.get('User-Agent') if request else None)
        )

        
        db.session.add(event)
        db.session.flush()
