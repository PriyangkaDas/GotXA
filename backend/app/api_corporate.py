"""Corporate Portal API endpoints.

The portal has its own lightweight session tokens so it can be used without
changing the SIEM API's demo authentication behaviour.
"""

from datetime import datetime, timedelta
from functools import wraps
import uuid

from flask import Blueprint, g, jsonify, request

from app.auth import error_response
from app.models import User, db

api = Blueprint('corporate_api', __name__, url_prefix='/api/corporate')

DEMO_PASSWORD = 'SecureP@ssw0rd'
SESSIONS = {}
SYSTEMS = [
    {'id': 'email', 'name': 'Corporate Email', 'status': 'operational', 'message': 'All systems normal'},
    {'id': 'vpn', 'name': 'Remote Access VPN', 'status': 'operational', 'message': 'All regions available'},
    {'id': 'erp', 'name': 'ERP Platform', 'status': 'degraded', 'message': 'Scheduled maintenance window'},
    {'id': 'files', 'name': 'File Storage', 'status': 'operational', 'message': 'All systems normal'},
    {'id': 'hr', 'name': 'HR Services', 'status': 'operational', 'message': 'All systems normal'},
]
ANNOUNCEMENTS = [
    {'id': 'ann-001', 'title': 'VPN maintenance', 'body': 'Brief maintenance is scheduled this weekend.', 'severity': 'info'},
    {'id': 'ann-002', 'title': 'Security awareness reminder', 'body': 'Report suspicious messages using the phishing button.', 'severity': 'medium'},
]
TASKS = [
    {'id': 'task-001', 'title': 'Review quarterly access confirmation', 'status': 'open', 'due_at': None, 'priority': 'high'},
    {'id': 'task-002', 'title': 'Complete security awareness training', 'status': 'in_progress', 'due_at': None, 'priority': 'medium'},
]


def _now():
    return datetime.utcnow().isoformat()


def _user_payload(user):
    return {
        'id': user.id,
        'name': user.username,
        'email': user.email,
        'role': user.role,
        'department': user.team.name if user.team else 'Corporate Operations',
        'last_login': _now(),
        'permissions': ['corporate.dashboard.read', 'corporate.tasks.write'] + (
            ['corporate.admin.read'] if user.role == 'admin' else []
        ),
    }


from app.auth import error_response, create_user_session, revoke_user_session
from app.models import User, UserSession, SecurityEvent, Device, LogSource, Alert, AuditEvent, db
from app.audit import AuditLogger
from app.telemetry import register_connecting_host

def _log_corp_security_event(level, message, details=None, is_failed_auth=False):
    """Log an actual security and audit event for Corporate Portal monitoring."""
    try:
        details = details or {}
        rule_id = details.get('rule_id') or ('RULE-AUTH-FAILED' if is_failed_auth else 'RULE-SECURITY-EVENT')
        alert_severity = 'critical' if rule_id == 'RULE-SQL-INJECTION' else ('high' if is_failed_auth else level.lower())
        occurred_at = datetime.utcnow()
        host = 'corp-portal'
        client_ip = (details or {}).get('ip_address') or (request.headers.get('X-Forwarded-For', request.remote_addr) if request else '127.0.0.1')
        u_agent = (details or {}).get('user_agent') or (request.headers.get('User-Agent', 'Mozilla/5.0') if request else 'Unknown')
        
        # Auto-discover and register the connecting client machine in SIEM Device Inventory
        if client_ip and client_ip not in ('127.0.0.1', 'localhost', '::1'):
            register_connecting_host(client_ip, user_agent=u_agent, source_hint='corp-portal')
            
        # Update server device tracking
        device = db.session.query(Device).filter_by(hostname=host).first()
        if not device:
            device = Device(
                hostname=host,
                device_type='web-server',
                trust_state='trusted',
                first_seen_at=occurred_at,
                last_seen_at=occurred_at
            )
            db.session.add(device)
        else:
            device.last_seen_at = occurred_at
            
        # Update LogSource
        source = db.session.query(LogSource).filter_by(name=host).first()
        if not source:
            source = LogSource(
                id=str(uuid.uuid4()),
                name=host,
                connector_type='web-application',
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

        timestamp_iso = occurred_at.isoformat() + 'Z'
        target_user = (details or {}).get('username') or (details or {}).get('user') or 'anonymous'
        action_name = (details or {}).get('action') or ('Login_Failed' if is_failed_auth else 'Web_Access')
        event_type_name = (details or {}).get('event_type') or ('Auth_Event' if 'auth' in action_name.lower() or is_failed_auth else 'Web_Access')
        req_uri = (details or {}).get('request_uri') or (request.path if request else '/api/corporate/auth/login')
        http_meth = (details or {}).get('http_method') or (request.method if request else 'POST')
        u_agent = (details or {}).get('user_agent') or (request.headers.get('User-Agent', 'Mozilla/5.0') if request else 'Unknown')

        event_payload = {
            'timestamp': timestamp_iso,
            'log_source': (details or {}).get('log_source') or 'Corp_Vendor_Portal_WAF',
            'event_type': event_type_name,
            'severity': level.capitalize() if level else 'Info',
            'user': target_user,
            'src_ip': client_ip,
            'geoip_country': (details or {}).get('geoip_country', 'US'),
            'action': action_name,
            'reason': (details or {}).get('reason', 'N/A'),
            'http_method': http_meth,
            'request_uri': req_uri,
            'user_agent': u_agent,
            'mfa_method': (details or {}).get('mfa_method', 'Password'),
            'host': host,
            'level': level,
            'message': message,
            'category': 'CORP_PORTAL',
            **(details or {})
        }

        event = SecurityEvent(
            device_id=device.id if device else None,
            source=host,
            severity=level.lower(),
            message=message,
            occurred_at=occurred_at,
            raw_event=event_payload
        )
        db.session.add(event)

        # Trigger SIEM alert for failed authentication attempts
        if is_failed_auth or level.upper() in ('HIGH', 'CRITICAL'):
            alert_prefix = 'SQLI' if rule_id == 'RULE-SQL-INJECTION' else 'AUTH-FAIL'
            alert_id = f"{alert_prefix}-{uuid.uuid4().hex[:8].upper()}"
            db.session.add(Alert(
                id=str(uuid.uuid4()),
                alert_id=alert_id,
                title=f"[CORP AUTH ALERT] {message}",
                severity=alert_severity,
                status='open',
                source=host,
                rule_id=rule_id,
                timestamp=occurred_at,
                raw_event=event_payload
            ))

        db.session.commit()
    except Exception as ex:
        try:
            db.session.rollback()
        except Exception:
            pass

def corporate_authenticate(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        if not token:
            _log_corp_security_event('WARN', f"Unauthenticated request to {request.path} from {request.remote_addr}", {'path': request.path, 'ip_address': request.remote_addr})
            return error_response('Unauthorized', 'A valid Corporate Portal session token is required', 401)
            
        session = db.session.query(UserSession).filter_by(token=token, is_active=True).first()
        if not session or session.expires_at <= datetime.utcnow():
            _log_corp_security_event('WARN', f"Expired or invalid session access attempt to {request.path} from {request.remote_addr}", {'path': request.path, 'ip_address': request.remote_addr})
            return error_response('Unauthorized', 'A valid Corporate Portal session is required', 401)
            
        user = session.user
        if not user or not user.is_active:
            _log_corp_security_event('HIGH', f"Access attempt by deactivated user from {request.remote_addr}", {'username': user.username if user else 'unknown', 'ip_address': request.remote_addr})
            return error_response('Unauthorized', 'User account is unavailable', 401)
            
        session.last_accessed_at = datetime.utcnow()
        db.session.commit()
        
        g.corporate_user = user
        g.corporate_session = session
        return handler(*args, **kwargs)
    return wrapped


CORP_DIRECTORY_USERS = {
    'admin': {
        'password': DEMO_PASSWORD,
        'aliases': [DEMO_PASSWORD, 'admin', 'admin123', 'password', 'password123', 'demo', 'SecureP@ssw0rd'],
        'name': 'Administrator',
        'role': 'admin',
        'email': 'admin@gotxa.local',
        'department': 'Executive'
    },
    'alex.rivera': {
        'password': 'Admin@2026!',
        'aliases': ['Admin@2026!', 'admin@2026!', 'admin', 'alex', 'password123'],
        'name': 'Alex Rivera',
        'role': 'Administrator',
        'email': 'alex.rivera@corp.internal',
        'department': 'Operations & Engineering'
    },
    'sarah.chen': {
        'password': 'Staff@2026!',
        'aliases': ['Staff@2026!', 'staff@2026!', 'sarah', 'password', 'password123'],
        'name': 'Sarah Chen',
        'role': 'Senior Staff Engineer',
        'email': 'sarah.chen@corp.internal',
        'department': 'Platform Engineering'
    },
    'marcus.brody': {
        'password': 'Secure@2026!',
        'aliases': ['Secure@2026!', 'secure@2026!', 'marcus', 'password123'],
        'name': 'Marcus Brody',
        'role': 'Security Lead',
        'email': 'marcus.brody@corp.internal',
        'department': 'Security & Compliance'
    },
    'david.kim': {
        'password': 'David@2026!',
        'aliases': ['David@2026!', 'david@2026!', 'david', 'password123'],
        'name': 'David Kim',
        'role': 'Cloud Operations Engineer',
        'email': 'david.kim@corp.internal',
        'department': 'DevOps & SRE'
    },
    'elena.rostova': {
        'password': 'Elena@2026!',
        'aliases': ['Elena@2026!', 'elena@2026!', 'elena', 'password123'],
        'name': 'Elena Rostova',
        'role': 'Integration Specialist',
        'email': 'elena.rostova@corp.internal',
        'department': 'Corporate IT Ops'
    },
    'user1': {
        'password': 'password123',
        'aliases': ['password123', 'user1', 'demo'],
        'name': 'User One',
        'role': 'user',
        'email': 'user1@gotxa.local',
        'department': 'Engineering'
    },
    'user2': {
        'password': 'password456',
        'aliases': ['password456', 'user2', 'demo'],
        'name': 'User Two',
        'role': 'user',
        'email': 'user2@gotxa.local',
        'department': 'Marketing'
    },
}


@api.route('/auth/login', methods=['POST'])
def login():
    body = request.get_json(silent=True) or request.form or {}
    raw_identifier = (body.get('username') or body.get('identifier') or '').strip()
    password = (body.get('password') or '').strip()
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    sql_markers = ("' or ", ' union ', 'select ', '--', '/*', '*/', '1=1', 'drop table', 'sleep(')
    is_sql_injection = any(marker in raw_identifier.lower() for marker in sql_markers)
    
    if not raw_identifier or not password:
        _log_corp_security_event(
            'WARN',
            f"Corporate Portal login attempted with missing credentials from {client_ip}",
            {'action': 'auth.login.failed', 'reason': 'Missing username or password', 'ip_address': client_ip, 'user_agent': user_agent},
            is_failed_auth=True
        )
        return error_response('BadRequest', 'username and password are required', 400)
    
    clean_id = raw_identifier.lower()
    matched_key = None
    user_data = None
    
    for key, data in CORP_DIRECTORY_USERS.items():
        if key.lower() == clean_id or data['email'].lower() == clean_id or clean_id in (key.split('.')[0], data['email'].split('@')[0]):
            matched_key = key
            user_data = data
            break
            
    if not matched_key:
        failure_reason = 'user not found in corporate directory'
        _log_corp_security_event(
            'HIGH',
            f"Failed Corporate Portal login attempt for user '{raw_identifier}' from {client_ip} (Invalid credentials: {failure_reason})",
            {
                'action': 'auth.login.failed',
                'event_type': 'SQL_Injection_Attempt' if is_sql_injection else 'Auth_Event',
                'rule_id': 'RULE-SQL-INJECTION' if is_sql_injection else 'RULE-AUTH-FAILED',
                'username': raw_identifier,
                'reason': failure_reason,
                'ip_address': client_ip,
                'user_agent': user_agent
            },
            is_failed_auth=True
        )
        return error_response('InvalidCredentials', f"Invalid credentials: {failure_reason}", 401)
        
    valid_passwords = user_data.get('aliases', [user_data['password']])
    if password != user_data['password'] and password not in valid_passwords:
        failure_reason = 'password does not match corporate records'
        _log_corp_security_event(
            'HIGH',
            f"Failed Corporate Portal login attempt for user '{raw_identifier}' from {client_ip} (Invalid credentials: {failure_reason})",
            {
                'action': 'auth.login.failed',
                'event_type': 'SQL_Injection_Attempt' if is_sql_injection else 'Auth_Event',
                'rule_id': 'RULE-SQL-INJECTION' if is_sql_injection else 'RULE-AUTH-FAILED',
                'username': raw_identifier,
                'reason': failure_reason,
                'ip_address': client_ip,
                'user_agent': user_agent
            },
            is_failed_auth=True
        )
        return error_response('InvalidCredentials', f"Invalid credentials: {failure_reason}", 401)

    # Valid user authenticated
    user = db.session.query(User).filter_by(username=matched_key).first()
    if not user:
        user = User(
            username=matched_key,
            email=user_data['email'],
            password_hash='demo',
            role=user_data['role']
        )
        db.session.add(user)
        db.session.commit()

    # Create and record real persistent session in database with audit event
    session = create_user_session(user, duration_hours=8, ip_address=client_ip, user_agent=user_agent)
    
    _log_corp_security_event(
        'INFO',
        f"Corporate Portal user '{matched_key}' ({user_data['name']}) successfully authenticated from {client_ip} (Session established: {session.token[:15]}...)",
        {
            'action': 'auth.login.success',
            'username': matched_key,
            'user_name': user_data['name'],
            'user_id': user.id,
            'session_id': session.id,
            'token_preview': session.token[:16] + '...',
            'ip_address': client_ip,
            'user_agent': user_agent
        }
    )
    
    payload = _user_payload(user)
    payload['name'] = user_data['name']
    payload['department'] = user_data['department']
    
    return jsonify({
        'user': payload,
        'access_token': session.token,
        'expires_at': session.expires_at.isoformat(),
        'session_id': session.id
    }), 200


@api.route('/auth/logout', methods=['POST'])
@corporate_authenticate
def logout():
    token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    user = g.corporate_user
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    revoke_user_session(token)
    _log_corp_security_event(
        'INFO',
        f"Corporate Portal user '{user.username}' logged out (Session terminated) from {client_ip}",
        {'action': 'auth.logout', 'username': user.username, 'ip_address': client_ip}
    )
    return '', 204


@api.route('/sessions', methods=['GET'])
def get_sessions():
    """List all corporate portal user sessions for SIEM monitoring."""
    try:
        sessions = db.session.query(UserSession).order_by(UserSession.created_at.desc()).limit(100).all()
        now = datetime.utcnow()
        result = []
        for s in sessions:
            status = 'active' if s.is_active and s.expires_at > now else ('expired' if s.is_active and s.expires_at <= now else 'revoked')
            result.append({
                'id': s.id,
                'token_preview': s.token[:16] + '...' if s.token else 'N/A',
                'user_id': s.user_id,
                'username': s.user.username if s.user else 'Unknown',
                'role': s.user.role if s.user else 'User',
                'ip_address': s.ip_address or '127.0.0.1',
                'user_agent': s.user_agent or 'Browser',
                'status': status,
                'is_active': s.is_active and s.expires_at > now,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'last_accessed_at': s.last_accessed_at.isoformat() if s.last_accessed_at else None,
                'expires_at': s.expires_at.isoformat() if s.expires_at else None,
                'revoked_at': s.revoked_at.isoformat() if s.revoked_at else None,
            })
        return jsonify({'sessions': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/sessions/<session_id>/revoke', methods=['POST'])
def revoke_session_by_id(session_id):
    """Revoke a specific user session from SIEM console."""
    try:
        session = db.session.get(UserSession, session_id)
        if not session:
            return error_response('NotFound', 'Session not found', 404)
            
        session.is_active = False
        session.revoked_at = datetime.utcnow()
        db.session.commit()
        
        username = session.user.username if session.user else 'Unknown'
        _log_corp_security_event(
            'WARN',
            f"SIEM Admin revoked session for user '{username}' (Session ID: {session_id[:8]}...)",
            {'action': 'session.revoked_by_admin', 'session_id': session_id, 'username': username}
        )
        return jsonify({'status': 'success', 'message': f"Session {session_id} revoked"}), 200
    except Exception as e:
        return error_response('InternalError', str(e), 500)


@api.route('/auth-stats', methods=['GET'])
def get_auth_stats():
    """Retrieve auth telemetry stats for SIEM dashboard."""
    try:
        now = datetime.utcnow()
        total_sessions = db.session.query(UserSession).count()
        active_sessions = db.session.query(UserSession).filter(UserSession.is_active == True, UserSession.expires_at > now).count()
        
        # Query failed login security events
        failed_events = db.session.query(SecurityEvent).filter(
            SecurityEvent.source == 'corp-portal',
            SecurityEvent.message.ilike('%Failed Corporate Portal login%')
        ).order_by(SecurityEvent.occurred_at.desc()).limit(50).all()
        
        # Query successful logins
        login_events = db.session.query(SecurityEvent).filter(
            SecurityEvent.source == 'corp-portal',
            SecurityEvent.message.ilike('%successfully authenticated%')
        ).order_by(SecurityEvent.occurred_at.desc()).limit(50).all()

        failed_list = []
        for fe in failed_events:
            raw = fe.raw_event or {}
            failed_list.append({
                'id': fe.id,
                'timestamp': fe.occurred_at.isoformat() if fe.occurred_at else None,
                'username': raw.get('username') or 'admin',
                'ip_address': raw.get('ip_address') or fe.source,
                'reason': raw.get('reason') or 'Invalid credentials',
                'message': fe.message
            })

        login_list = []
        for le in login_events:
            raw = le.raw_event or {}
            login_list.append({
                'id': le.id,
                'timestamp': le.occurred_at.isoformat() if le.occurred_at else None,
                'username': raw.get('username') or 'admin',
                'ip_address': raw.get('ip_address') or '127.0.0.1',
                'message': le.message
            })

        return jsonify({
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_failed_logins': len(failed_events),
            'recent_failed_attempts': failed_list,
            'recent_successful_logins': login_list,
            'brute_force_alert': len(failed_events) >= 3
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/me', methods=['GET'])
@corporate_authenticate
def me():
    return jsonify(_user_payload(g.corporate_user))


@api.route('/dashboard', methods=['GET'])
@corporate_authenticate
def dashboard():
    user = g.corporate_user
    _log_corp_security_event('INFO', f"User '{user.username}' accessed Corporate Portal dashboard")
    activity = [
        {'id': 'act-001', 'type': 'sign_in', 'message': 'Signed in to Corporate Portal', 'created_at': _now()},
        {'id': 'act-002', 'type': 'task', 'message': 'Access review task assigned', 'created_at': _now()},
    ]
    payload = {
        'system_summary': SYSTEMS,
        'my_tasks': TASKS,
        'announcements': [{**item, 'published_at': _now()} for item in ANNOUNCEMENTS],
        'activity': activity,
    }
    if user.role == 'admin':
        payload['admin_summary'] = {
            'kpis': {'active_systems': 5, 'open_service_issues': 1, 'task_completion_rate': 78, 'average_response_minutes': 14},
            'team_workload': [{'team': 'Corporate Operations', 'open': 2, 'in_progress': 1}],
            'access_review_count': 1,
        }
    return jsonify(payload)


@api.route('/systems', methods=['GET'])
@corporate_authenticate
def systems():
    return jsonify({'items': [{**item, 'updated_at': _now()} for item in SYSTEMS]})


@api.route('/systems/<system_id>', methods=['PATCH'])
@corporate_authenticate
def update_system_status(system_id):
    body = request.get_json(silent=True) or {}
    status = body.get('status')
    message = body.get('message', '')
    sys_item = next((s for s in SYSTEMS if s['id'] == system_id), None)
    if not sys_item:
        return error_response('NotFound', 'System not found', 404)
    old_status = sys_item['status']
    sys_item['status'] = status or sys_item['status']
    if message:
        sys_item['message'] = message
    sys_item['updated_at'] = _now()
    _log_corp_security_event(
        'INFO',
        f"User '{g.corporate_user.username}' updated system '{sys_item['name']}' status from '{old_status}' to '{sys_item['status']}'",
        {'system_id': system_id, 'old_status': old_status, 'new_status': sys_item['status'], 'message': sys_item['message']}
    )
    return jsonify(sys_item)


@api.route('/tasks', methods=['GET'])
@corporate_authenticate
def tasks():
    status = request.args.get('status')
    items = [task for task in TASKS if not status or task['status'] == status]
    return jsonify({'items': items})


@api.route('/tasks', methods=['POST'])
@corporate_authenticate
def create_task():
    body = request.get_json(silent=True) or {}
    title = (body.get('title') or '').strip()
    priority = body.get('priority', 'medium')
    if not title:
        return error_response('BadRequest', 'title is required', 400)
    new_task = {
        'id': f"task-{uuid.uuid4().hex[:6]}",
        'title': title,
        'status': 'open',
        'due_at': None,
        'priority': priority,
        'created_at': _now(),
        'updated_at': _now()
    }
    TASKS.append(new_task)
    _log_corp_security_event(
        'INFO',
        f"User '{g.corporate_user.username}' created new corporate task '{title}' [Priority: {priority}]",
        {'task_id': new_task['id'], 'title': title, 'priority': priority}
    )
    return jsonify(new_task), 201


@api.route('/tasks/<task_id>', methods=['PATCH'])
@corporate_authenticate
def update_task(task_id):
    body = request.get_json(silent=True) or {}
    status = body.get('status')
    title = body.get('title')
    priority = body.get('priority')
    task = next((item for item in TASKS if item['id'] == task_id), None)
    if not task:
        return error_response('NotFound', 'Task not found', 404)
    
    old_state = {'status': task['status'], 'title': task['title'], 'priority': task.get('priority')}
    if status:
        if status not in {'open', 'in_progress', 'completed'}:
            return error_response('BadRequest', 'status must be open, in_progress, or completed', 400)
        task['status'] = status
    if title:
        task['title'] = title
    if priority:
        task['priority'] = priority
    task['updated_at'] = _now()
    
    _log_corp_security_event(
        'INFO',
        f"User '{g.corporate_user.username}' modified corporate task '{task['title']}' (Status: {task['status']}, Priority: {task.get('priority')})",
        {'task_id': task_id, 'old_state': old_state, 'new_state': {'status': task['status'], 'title': task['title'], 'priority': task.get('priority')}}
    )
    return jsonify(task)


@api.route('/announcements', methods=['GET'])
@corporate_authenticate
def announcements():
    return jsonify({'items': [{**item, 'published_at': _now()} for item in ANNOUNCEMENTS]})


@api.route('/announcements', methods=['POST'])
@corporate_authenticate
def create_announcement():
    body = request.get_json(silent=True) or {}
    title = (body.get('title') or '').strip()
    content = (body.get('body') or '').strip()
    severity = body.get('severity', 'info')
    if not title or not content:
        return error_response('BadRequest', 'title and body are required', 400)
    new_ann = {
        'id': f"ann-{uuid.uuid4().hex[:6]}",
        'title': title,
        'body': content,
        'severity': severity,
        'published_at': _now()
    }
    ANNOUNCEMENTS.append(new_ann)
    _log_corp_security_event(
        'INFO',
        f"User '{g.corporate_user.username}' published new announcement: '{title}' [{severity.upper()}]",
        {'announcement_id': new_ann['id'], 'title': title, 'severity': severity}
    )
    return jsonify(new_ann), 201


@api.route('/activity', methods=['GET'])
@corporate_authenticate
def activity():
    return jsonify({'items': [{'id': 'act-001', 'type': 'sign_in', 'message': 'Signed in to Corporate Portal', 'created_at': _now()}]})


@api.route('/admin/overview', methods=['GET'])
@corporate_authenticate
def admin_overview():
    if g.corporate_user.role != 'admin':
        _log_corp_security_event('HIGH', f"Unauthorized access attempt to admin overview by user '{g.corporate_user.username}'", {'username': g.corporate_user.username})
        return error_response('Forbidden', 'Administrator access is required', 403)
    _log_corp_security_event('INFO', f"Admin '{g.corporate_user.username}' accessed administrative operations overview")
    return jsonify({
        'kpis': {'active_systems': 5, 'open_service_issues': 1, 'task_completion_rate': 78, 'average_response_minutes': 14},
        'team_workload': [{'team': 'Corporate Operations', 'open': 2, 'in_progress': 1}],
        'access_review_count': 1,
    })


@api.route('/users', methods=['GET'])
def list_corporate_users():
    """List corporate directory users for user directory / assignment UI."""
    items = []
    for username, data in CORP_DIRECTORY_USERS.items():
        items.append({
            'id': username,
            'username': username,
            'name': data.get('name', username),
            'email': data.get('email', f"{username}@gotxa.local"),
            'role': data.get('role', 'user'),
            'department': data.get('department', 'Corporate Operations'),
            'status': 'active'
        })
    return jsonify({'items': items, 'total': len(items)}), 200

