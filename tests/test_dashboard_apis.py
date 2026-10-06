#!/usr/bin/env python3
"""
Diagnostic test script to scan frontend dashboard bundles for API endpoints
and verify whether the backend endpoints exist, accept requests, and return valid data.
"""

import os
import re
import sys
import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

# Set up backend paths
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / 'backend'
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / 'app'))

# Mock pdf generator if not installed in local environment
if 'app.pdf_generator' not in sys.modules:
    try:
        import app.pdf_generator
    except ImportError:
        sys.modules['app.pdf_generator'] = MagicMock()

from flask import Flask
from app.models import db, User, Alert, Incident, LogSource, Device, PlaybookExecution, Setting, ThreatIntelligenceFeed
from app import (
    api_v1,
    api_v1_actions,
    api_v1_extended,
    api_v1_consolidated,
    api_v1_reports,
    api_v1_db,
    api_corporate,
    api_ingestion,
)

def create_test_app():
    """Create Flask test application with in-memory SQLite database and seed data."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    # Register all blueprints
    app.register_blueprint(api_v1.api)
    app.register_blueprint(api_v1_actions.api)
    app.register_blueprint(api_v1_extended.api)
    app.register_blueprint(api_v1_consolidated.api)
    app.register_blueprint(api_v1_reports.api)
    app.register_blueprint(api_v1_db.api)
    app.register_blueprint(api_corporate.api)
    app.register_blueprint(api_ingestion.api)

    with app.app_context():
        db.create_all()
        # Seed test admin user
        admin = User(
            id='user-admin-uuid',
            username='admin',
            email='admin@gotxa.local',
            password_hash='dummy_hash',
            role='admin',
            is_active=True
        )
        db.session.add(admin)

        # Seed sample Alert
        alert = Alert(
            id='alert-uuid-1',
            alert_id='AL-2401',
            title='Sample Brute Force Attempt',
            severity='high',
            status='open',
            source='corp-portal-agent',
            rule_id='RULE-AUTH-FAILED',
            timestamp=datetime.utcnow()
        )
        db.session.add(alert)

        # Seed sample Incident
        incident = Incident(
            id='incident-uuid-1',
            incident_id='INC-2026-001',
            title='Sample Multi-Stage Incident',
            severity='high',
            status='investigating',
            detected_at=datetime.utcnow()
        )
        db.session.add(incident)

        # Seed sample Device
        device = Device(
            id='device-uuid-1',
            hostname='dev-01',
            device_type='workstation',
            trust_state='untrusted'
        )
        db.session.add(device)

        # Seed sample PlaybookExecution
        execution = PlaybookExecution(
            id='exec-uuid-1',
            playbook_id='containment.block_ip',
            execution_id='EXEC-TEST01',
            status='completed',
            mode='simulated'
        )
        db.session.add(execution)

        # Seed sample Threat Feed
        feed = ThreatIntelligenceFeed(
            id='feed-uuid-1',
            feed_id='feed-01',
            name='Emerging Threats',
            status='active'
        )
        db.session.add(feed)

        db.session.commit()

    return app

def extract_endpoints_from_dist():
    """Extract all API endpoint patterns from the dist bundles in frontend/."""
    frontend_dir = REPO_ROOT / 'frontend'
    endpoint_map = {}
    pattern = re.compile(r'["\'](/(?:api|v1)[a-zA-Z0-9_\-/\?=&]+)["\']')

    for js_path in frontend_dir.glob('**/dist/**/*.js'):
        dashboard_name = js_path.relative_to(frontend_dir).parts[0]
        try:
            with open(js_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                matches = pattern.findall(content)
                for m in matches:
                    clean_path = m.split('?')[0]
                    if any(clean_path.startswith(prefix) for prefix in ['/api', '/v1']):
                        endpoint_map.setdefault(dashboard_name, set()).add(clean_path)
        except Exception as e:
            print(f"Error reading {js_path}: {e}")

    return endpoint_map

def run_diagnostics():
    print("=" * 70)
    print("GOTXA DASHBOARD API VERIFICATION DIAGNOSTIC")
    print("=" * 70)

    # 1. Extract endpoints from frontend
    endpoint_map = extract_endpoints_from_dist()
    all_dashboard_endpoints = set()
    for d_name, eps in endpoint_map.items():
        print(f"\n[Dashboard: {d_name}] Found {len(eps)} API endpoints in dist bundle:")
        for ep in sorted(eps):
            print(f"  - {ep}")
            all_dashboard_endpoints.add(ep)

    # 2. Setup Flask app & client
    app = create_test_app()
    client = app.test_client()
    headers = {
        'X-User-ID': 'admin',
        'Authorization': 'Bearer test-token'
    }

    # 3. Test each endpoint with multiple candidate methods
    print("\n" + "=" * 70)
    print("TESTING ENDPOINT RESPONSES FROM BACKEND")
    print("=" * 70)

    results = []

    for ep in sorted(all_dashboard_endpoints):
        test_path = ep
        # Map known dashboard mock IDs to seeded database entities
        test_path = test_path.replace('AL-2401', 'alert-uuid-1')
        test_path = test_path.replace('INC-2026-001', 'incident-uuid-1')
        test_path = test_path.replace('INC-081', 'incident-uuid-1')
        test_path = test_path.replace('dev-01', 'device-uuid-1')
        test_path = test_path.replace('sys-01', 'sys-01')
        test_path = test_path.replace('task-01', 'task-01')
        test_path = test_path.replace('feed-01', 'feed-01')
        test_path = test_path.replace('rule-01', 'rule-01')
        test_path = test_path.replace('rule-246', 'rule-246')
        test_path = re.sub(r'\{[^\}]+\}', 'test-id', test_path)
        test_path = re.sub(r':([a-zA-Z_]+)', 'test-id', test_path)

        # Decide preferred methods to try
        methods_to_try = ['GET']
        if any(term in ep for term in ['/trust', '/status', '/systems/', '/tasks/']) and not ep.endswith('/status'):
            methods_to_try = ['PATCH', 'PUT', 'GET', 'POST']
        elif any(term in ep for term in ['status', 'update']):
            methods_to_try = ['PUT', 'POST', 'GET']
        elif any(term in ep for term in ['assign', 'suppress', 'execute', 'revoke', 'approve', 'batch', 'test', 'login', 'logout', 'sync', 'generate', 'query', 'control']):
            methods_to_try = ['POST', 'GET']

        best_resp = None
        best_method = 'GET'
        status_code = 404

        for m in methods_to_try:
            if m == 'GET':
                resp = client.get(test_path, headers=headers)
            elif m == 'POST':
                resp = client.post(test_path, headers=headers, json={'reason': 'test', 'status': 'open', 'operations': []})
            elif m == 'PUT':
                resp = client.put(test_path, headers=headers, json={'status': 'investigating', 'reason': 'test'})
            elif m == 'PATCH':
                resp = client.patch(test_path, headers=headers, json={'trust_state': 'trusted', 'status': 'online'})
            
            if resp.status_code != 405:
                best_resp = resp
                best_method = m
                status_code = resp.status_code
                if status_code in (200, 201):
                    break

        if best_resp is None:
            best_resp = client.get(test_path, headers=headers)
            status_code = best_resp.status_code
            best_method = 'GET'

        data = None
        has_valid_data = False
        error_detail = ""

        try:
            data = best_resp.get_json(silent=True)
            if data is not None and isinstance(data, (dict, list)):
                if status_code in (200, 201):
                    if isinstance(data, dict):
                        if any(k in data for k in ['data', 'items', 'alerts', 'status', 'sessions', 'actions', 'executions']):
                            has_valid_data = True
                    elif isinstance(data, list):
                        has_valid_data = True
            else:
                error_detail = f"Non-JSON response (len {len(best_resp.data)})"
        except Exception as err:
            error_detail = str(err)

        results.append({
            'endpoint': ep,
            'test_path': test_path,
            'method': best_method,
            'status': status_code,
            'valid_json': data is not None,
            'has_valid_data': has_valid_data,
            'data_preview': str(data)[:100] if data else error_detail
        })

    # Summary Table
    print(f"\n{'STATUS':<8} {'METHOD':<6} {'ENDPOINT':<40} {'HAS DATA?':<10} {'PREVIEW'}")
    print("-" * 90)
    
    missing_404 = []
    broken_500 = []
    working_ok = []

    for r in results:
        status_str = str(r['status'])
        data_str = "YES" if r['has_valid_data'] else "NO"
        if r['status'] == 404:
            missing_404.append(r)
        elif r['status'] >= 500:
            broken_500.append(r)
        elif r['status'] in (200, 201):
            working_ok.append(r)

        print(f"{status_str:<8} {r['method']:<6} {r['endpoint']:<40} {data_str:<10} {r['data_preview'][:35]}")

    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Total Unique Endpoints in Dashboards: {len(results)}")
    print(f"Working & Returning Valid Data:       {len(working_ok)}")
    print(f"Missing / 404 Not Found:             {len(missing_404)}")
    print(f"Internal Errors (500):               {len(broken_500)}")

    if missing_404:
        print("\n[!] 404 NOT FOUND ENDPOINTS (DASHBOARDS WILL BREAK):")
        for m in missing_404:
            print(f"  - {m['method']} {m['endpoint']}")

    if broken_500:
        print("\n[!] 500 SERVER ERROR ENDPOINTS:")
        for b in broken_500:
            print(f"  - {b['method']} {b['endpoint']}: {b['data_preview']}")

    return results

if __name__ == '__main__':
    run_diagnostics()
