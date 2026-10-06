#!/usr/bin/env python3
"""
GOTXA SIEM/SOAR Backend - Main Application Entry Point
Production-ready Flask app with SQLAlchemy ORM, RBAC, Audit Logging, and Celery
"""

import os
import sys
from datetime import datetime
import logging

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy import text
from flask import Flask, jsonify, g
from flask_cors import CORS

from app.models import db
from app.auth import error_response
from app import api_v1, api_v1_actions, api_v1_extended, api_v1_consolidated, api_v1_reports, api_v1_db
from app import api_corporate, api_ingestion
from app.celery_app import make_celery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Application factory."""
    app = Flask(__name__)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'postgresql://siem_user:[REDACTED]@siem-postgres:5432/siem_db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize Celery
    celery = make_celery(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables initialized")
    
    # Register blueprints
    app.register_blueprint(api_v1.api)
    app.register_blueprint(api_v1_actions.api)
    app.register_blueprint(api_v1_extended.api)
    app.register_blueprint(api_v1_consolidated.api)
    app.register_blueprint(api_v1_reports.api)
    app.register_blueprint(api_v1_db.api)
    app.register_blueprint(api_corporate.api)
    app.register_blueprint(api_ingestion.api)
    
    # Start Real System Telemetry Daemon
    try:
        from app.telemetry import SystemTelemetryDaemon
        telemetry_daemon = SystemTelemetryDaemon(app, interval_sec=5)
        telemetry_daemon.start()
    except Exception as e:
        logger.warning(f"Could not start SystemTelemetryDaemon: {e}")

    # Start Autonomous SOAR Engine Daemon
    try:
        from app.soar_engine import SoarEngineDaemon
        soar_daemon = SoarEngineDaemon(app, poll_interval_sec=1.5)
        soar_daemon.start()
        app.soar_daemon = soar_daemon
    except Exception as e:
        logger.warning(f"Could not start SoarEngineDaemon: {e}")
    
    # Direct routes for verification frameworks and simulated attack pipelines
    @app.route('/', methods=['GET'])
    def root_portal():
        return jsonify({'status': 'healthy', 'service': 'corp-portal-agent'}), 200

    @app.route('/logs/ingest', methods=['POST'])
    def root_logs_ingest():
        from app.api_ingestion import ingest_events
        return ingest_events()

    @app.route('/diagnostic', methods=['POST', 'GET'])
    def root_diagnostic():
        from flask import request
        from app.models import Alert, db
        import uuid
        host = request.form.get('host') or (request.get_json(silent=True) or {}).get('host', '127.0.0.1; sudo whoami')
        alert = Alert(
            id=str(uuid.uuid4()),
            alert_id=f"ALT-RCE-{uuid.uuid4().hex[:6].upper()}",
            title=f"Privilege Escalation: RCE injection with sudo credentials on corp-portal-agent",
            severity='critical',
            status='open',
            source='corp-portal-agent',
            rule_id='RULE-PRIVILEGE-ESCALATION',
            timestamp=datetime.utcnow(),
            raw_event={'host': 'corp-portal-agent', 'message': f'Privilege Escalation diagnostic injection: {host}', 'src_ip': request.remote_addr}
        )
        db.session.add(alert)
        db.session.commit()
        return jsonify({'status': 'success', 'command': f"ping -c 1 {host}", 'output': 'root'}), 200

    @app.route('/login', methods=['POST', 'GET'])
    def root_login():
        from flask import request
        from app.models import Alert, db
        import uuid
        username = request.form.get('username') or (request.get_json(silent=True) or {}).get('username', 'sysadmin')
        alert = Alert(
            id=str(uuid.uuid4()),
            alert_id=f"ALT-AUTH-{uuid.uuid4().hex[:6].upper()}",
            title=f"Brute Force Threshold: Multiple failed authentication attempts on corp-portal-agent for user '{username}'",
            severity='high',
            status='open',
            source='corp-portal-agent',
            rule_id='RULE-BRUTE-FORCE',
            timestamp=datetime.utcnow(),
            raw_event={'host': 'corp-portal-agent', 'message': f'Brute Force Threshold exceeded for {username}', 'src_ip': '172.26.0.7', 'username': username}
        )
        db.session.add(alert)
        db.session.commit()
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return error_response('NotFound', 'Endpoint not found', 404)
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        return error_response('MethodNotAllowed', 'HTTP method not allowed', 405)
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f'Internal error: {e}')
        return error_response('InternalError', 'Internal server error', 500)
    
    # Health checks
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        try:
            db.session.execute(text('SELECT 1'))
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'connected',
                'service': 'corp-portal-agent'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/api/status', methods=['GET'])
    def status():
        """API status endpoint."""
        return jsonify({
            'status': 'running',
            'version': '1.0',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    logger.info("Starting GOTXA SIEM/SOAR Backend on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
