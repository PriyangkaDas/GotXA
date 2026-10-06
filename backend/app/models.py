#!/usr/bin/env python3
"""
SQLAlchemy ORM models for GOTXA SIEM/SOAR platform.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='analyst')
    team_id = db.Column(db.String(36), db.ForeignKey('teams.id'))
    is_active = db.Column(db.Boolean, default=True)
    mfa_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    team = db.relationship('Team', back_populates='members')
    alerts_assigned = db.relationship('Alert', foreign_keys='Alert.assignee_id', back_populates='assignee')
    incidents_owned = db.relationship('Incident', foreign_keys='Incident.owner_id', back_populates='owner')

class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('User', back_populates='team')

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(20), nullable=False, index=True)
    status = db.Column(db.String(50), default='open', index=True)
    source = db.Column(db.String(255), nullable=False, index=True)
    rule_id = db.Column(db.String(255), index=True)
    
    assignee_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True, index=True)
    team_id = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=True, index=True)
    
    is_suppressed = db.Column(db.Boolean, default=False)
    suppression_reason = db.Column(db.Text)
    suppression_expires_at = db.Column(db.DateTime, nullable=True)
    suppression_scope = db.Column(db.String(50))
    
    raw_event = db.Column(db.JSON)
    normalized_event = db.Column(db.JSON)
    entities = db.Column(db.JSON)
    mitre_tactics = db.Column(db.JSON)
    
    incident_id = db.Column(db.String(36), db.ForeignKey('incidents.id'), nullable=True, index=True)
    
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    assignee = db.relationship('User', back_populates='alerts_assigned', foreign_keys=[assignee_id])
    incident = db.relationship('Incident', back_populates='alerts', foreign_keys=[incident_id])
    team = db.relationship('Team')

class Incident(db.Model):
    __tablename__ = 'incidents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    status = db.Column(db.String(50), default='open', index=True)
    severity = db.Column(db.String(20), nullable=False)
    priority = db.Column(db.String(20), default='medium')
    
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    team_id = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=True)
    
    root_cause = db.Column(db.Text)
    affected_assets = db.Column(db.JSON)
    response_actions = db.Column(db.JSON)
    mitre_tactics = db.Column(db.JSON)
    
    resolution_notes = db.Column(db.Text)
    closure_reason = db.Column(db.String(255))
    lessons_learned = db.Column(db.Text)
    
    detected_at = db.Column(db.DateTime, nullable=False)
    contained_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = db.relationship('User', back_populates='incidents_owned', foreign_keys=[owner_id])
    team = db.relationship('Team')
    alerts = db.relationship('Alert', back_populates='incident')
    tasks = db.relationship('Task', back_populates='incident', cascade='all, delete-orphan')
    evidence = db.relationship('Evidence', back_populates='incident', cascade='all, delete-orphan')

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = db.Column(db.String(36), db.ForeignKey('incidents.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='open')
    assigned_to_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    due_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    incident = db.relationship('Incident', back_populates='tasks')
    assigned_to = db.relationship('User')

class Evidence(db.Model):
    __tablename__ = 'evidence'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = db.Column(db.String(36), db.ForeignKey('incidents.id'), nullable=False)
    type = db.Column(db.String(50))
    source = db.Column(db.String(255))
    url = db.Column(db.Text)
    hash_value = db.Column(db.String(255))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    incident = db.relationship('Incident', back_populates='evidence')

class PlaybookExecution(db.Model):
    __tablename__ = 'playbook_executions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    playbook_id = db.Column(db.String(255), nullable=False, index=True)
    execution_id = db.Column(db.String(50), unique=True, nullable=False)
    
    status = db.Column(db.String(50), default='pending')
    mode = db.Column(db.String(50), default='live')
    
    inputs = db.Column(db.JSON)
    outputs = db.Column(db.JSON)
    
    triggered_by_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    approved_by_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    reason = db.Column(db.Text)
    change_ticket = db.Column(db.String(50))
    
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    triggered_by = db.relationship('User', foreign_keys=[triggered_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])

class AuditEvent(db.Model):
    __tablename__ = 'audit_events'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    correlation_id = db.Column(db.String(50), nullable=False, index=True)
    actor_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False, index=True)
    resource_type = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.String(255), nullable=False, index=True)
    
    status = db.Column(db.String(50))
    change_before = db.Column(db.JSON)
    change_after = db.Column(db.JSON)
    reason = db.Column(db.Text)
    
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    actor = db.relationship('User')

class Setting(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    section = db.Column(db.String(100), nullable=False, index=True)
    key = db.Column(db.String(255), nullable=False)
    value = db.Column(db.JSON)
    value_type = db.Column(db.String(50))
    is_sensitive = db.Column(db.Boolean, default=False)
    
    __table_args__ = (db.UniqueConstraint('section', 'key', name='uq_section_key'),)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SettingChange(db.Model):
    __tablename__ = 'setting_changes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    section = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(255), nullable=False)
    changed_by_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    old_value = db.Column(db.JSON)
    new_value = db.Column(db.JSON)
    reason = db.Column(db.Text)
    change_ticket = db.Column(db.String(50))
    rollback_plan = db.Column(db.Text)
    
    status = db.Column(db.String(50), default='approved')
    requires_approval = db.Column(db.Boolean, default=False)
    approved_by_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    applied_at = db.Column(db.DateTime, nullable=True)
    
    changed_by = db.relationship('User', foreign_keys=[changed_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = db.Column(db.String(50), unique=True, nullable=False)
    
    type = db.Column(db.String(50))
    format = db.Column(db.String(20))
    title = db.Column(db.String(255))
    
    requested_by_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    date_from = db.Column(db.DateTime)
    date_to = db.Column(db.DateTime)
    
    status = db.Column(db.String(50), default='pending', index=True)
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer, default=0)
    file_url = db.Column(db.String(500))
    
    filters = db.Column(db.JSON)
    data = db.Column(db.JSON)
    error_message = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    generated_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    requested_by = db.relationship('User')

class LogSource(db.Model):
    """Data source connector ingestion metrics."""
    __tablename__ = 'log_sources'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False, index=True)
    connector_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='healthy', index=True)
    
    last_event_timestamp = db.Column(db.DateTime)
    ingestion_rate = db.Column(db.Integer, default=0)
    drop_count = db.Column(db.Integer, default=0)
    parse_error_count = db.Column(db.Integer, default=0)
    ingest_delay_seconds = db.Column(db.Float, default=0)
    total_events_ingested = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Device(db.Model):
    """Inventory of devices observed in authenticated production telemetry."""
    __tablename__ = 'devices'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hostname = db.Column(db.String(255), nullable=False, unique=True, index=True)
    ip_address = db.Column(db.String(45), index=True)
    mac_address = db.Column(db.String(17), unique=True, index=True)
    device_type = db.Column(db.String(100), nullable=False, default='unknown', index=True)
    manufacturer = db.Column(db.String(255))
    model = db.Column(db.String(255))
    os_version = db.Column(db.String(255))
    serial_number = db.Column(db.String(255), unique=True)
    trust_state = db.Column(db.String(20), nullable=False, default='untrusted', index=True)
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    metadata_json = db.Column(db.JSON)

class SecurityEvent(db.Model):
    """Immutable, normalized events received from approved collectors."""
    __tablename__ = 'security_events'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = db.Column(db.String(36), db.ForeignKey('devices.id'), nullable=True, index=True)
    source = db.Column(db.String(255), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, default='info', index=True)
    message = db.Column(db.Text, nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False, index=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    raw_event = db.Column(db.JSON, nullable=False)

    device = db.relationship('Device')

class ThreatIntelligenceFeed(db.Model):
    """Threat intelligence feed status and metrics."""
    __tablename__ = 'threat_intelligence_feeds'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    feed_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='active', index=True)
    
    feed_url = db.Column(db.String(500))
    last_sync = db.Column(db.DateTime, nullable=True)
    sync_interval_hours = db.Column(db.Integer, default=24)
    
    indicators_count = db.Column(db.Integer, default=0)
    last_error = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class JITSession(db.Model):
    """Just-In-Time (JIT) privilege elevation sessions."""
    __tablename__ = 'jit_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    reason = db.Column(db.Text, nullable=False)
    ticket_id = db.Column(db.String(50))
    
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    
    status = db.Column(db.String(50), default='pending', index=True)
    elevated_role = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])

class SystemMetric(db.Model):
    """Global system metrics (ingestion rate, source health, SLA risk)."""
    __tablename__ = 'system_metrics'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_name = db.Column(db.String(100), nullable=False, index=True)
    metric_value = db.Column(db.Float, nullable=False)
    metric_data = db.Column(db.JSON)
    
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class UserSession(db.Model):
    """Real user authentication session model with tracking and audit recording."""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    last_accessed_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', foreign_keys=[user_id])

