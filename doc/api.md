## Complete API Reference & Catalog

**Last Updated:** 2026-09-25  
**Total Endpoints:** 106  
**Status:** ACTIVE - All endpoints documented  
**Critical Issues:** 9 duplicates found (see rules.md)  

---

## 📊 QUICK STATISTICS

| Metric | Count |
|---|---|
| Total Endpoints | 106 |
| API Files | 8 |
| Blueprints | 3 |
| GET Endpoints | 55 |
| POST Endpoints | 40 |
| PUT Endpoints | 5 |
| PATCH Endpoints | 4 |
| DELETE Endpoints | 2 |
| Duplicate Endpoints | 9 ⚠️ |

---

## 📍 BLUEPRINT OVERVIEW

### /api (Main API) - 83 endpoints
Primary endpoints for alerts, incidents, SOAR, database, etc.

### /api/corporate (Corporate Portal) - 17 endpoints  
Corporate portal authentication, sessions, and management.

### /api/db (Database Operations) - 6 endpoints
Direct database query and table management.

---

## 🎯 ENDPOINT CATALOG BY RESOURCE

### ALERTS (13 endpoints)
```
GET  /api/alerts
  Purpose: List all alerts with pagination and filtering
  Input: page, limit, status, severity, source
  Output: [{ id, alert_id, title, severity, status, created_at, ... }]
  File: api_v1.py
  Primary: ✅ YES

GET  /api/alerts/<alert_id>
  Purpose: Get single alert with full details
  Input: alert_id (path)
  Output: { id, alert_id, title, severity, description, raw_event, ... }
  File: api_v1.py, api_v1_consolidated.py (DUPLICATE ⚠️)
  Primary: api_v1.py

POST /api/alerts/assign
  Purpose: Bulk assign alerts to analyst
  Input: { alert_ids: [...], assignee_id: "..." }
  Output: { assigned: number, failed: number }
  File: api_v1_actions.py
  Primary: ✅ YES

POST /api/alerts/batch-operations
  Purpose: Apply multiple alert actions in a single request
  Input: { "operations": [{ "type": "assign|suppress|status", ... }] }
  Output: { processed, results }
  File: api_v1_consolidated.py
  Primary: ✅ CONSOLIDATION

POST /api/alerts/<alert_id>/suppress
  Purpose: Suppress alert for specified duration
  Input: { duration_minutes: 60, reason: "..." }
  Output: { suppressed_until: timestamp }
  File: api_v1_actions.py, api_v1_consolidated.py (DUPLICATE ⚠️)
  Primary: api_v1_actions.py

PUT  /api/alerts/<alert_id>/status
  Purpose: Update alert status in workflow
  Input: { status: "open|acknowledged|resolved", reason: "..." }
  Output: { id, status, updated_at }
  File: api_v1_actions.py
  Primary: ✅ YES

POST /api/alerts/bulk-assign
  Purpose: Consolidated bulk assignment endpoint
  Input: { alert_ids: [...], assignee_id: "..." }
  Output: { assigned: number, failed: number }
  File: api_v1_consolidated.py
  Primary: ✅ CONSOLIDATION
  Note: Overlaps with POST /api/alerts/assign (CONSOLIDATE ⚠️)
```

### INCIDENTS (18 endpoints)
```
GET  /api/incidents
  Purpose: List all incidents with pagination
  Input: page, limit, status, severity
  Output: [{ id, incident_id, title, status, created_at, ... }]
  Files: api_v1.py, api_v1_actions.py, api_v1_consolidated.py (MULTIPLE ⚠️)
  Primary: api_v1_actions.py

GET  /api/incidents/<incident_id>
  Purpose: Get single incident with full investigation details
  Input: incident_id (path)
  Output: { id, incident_id, title, status, description, tasks: [...], ... }
  Files: api_v1.py, api_v1_consolidated.py (DUPLICATE ⚠️)
  Primary: api_v1_consolidated.py

GET  /api/incidents/summary
  Purpose: Get incidents summary statistics
  Input: date_range, severity_filter
  Output: { total_open, total_investigating, by_severity: {...} }
  Files: api_v1_extended.py, api_v1_consolidated.py (DUPLICATE ⚠️)
  Primary: api_v1_consolidated.py

POST /api/incidents
  Purpose: Create new incident
  Input: { title, description, severity, incident_type }
  Output: { id, incident_id, created_at }
  Files: api_v1_actions.py, api_v1_consolidated.py (DUPLICATE ⚠️)
  Primary: api_v1_actions.py

PUT  /api/incidents/<incident_id>/status
  Purpose: Update incident status (lifecycle management)
  Input: { status: "open|investigating|contained|resolved|closed" }
  Output: { id, status, updated_at }
  File: api_v1_actions.py
  Primary: ✅ YES

POST /api/incidents/<incident_id>/assign
  Purpose: Assign incident to analyst
  Input: { assigned_to: user_id }
  Output: { assigned_to, assigned_at }
  File: api_v1_actions.py
  Primary: ✅ YES

POST /api/incidents/<incident_id>/link-alert
  Purpose: Link alert to incident
  Input: { alert_id: "..." }
  Output: { incident_id, alert_id, linked_at }
  File: api_v1_actions.py
  Primary: ✅ YES

POST /api/incidents/<incident_id>/batch-update
  Purpose: Create tasks, link alerts, and update status in one request
  Input: { "updates": [{ "type": "create-task|link-alert|update-status", ... }] }
  Output: { incident_id, processed, results }
  File: api_v1_consolidated.py
  Primary: ✅ CONSOLIDATION

GET  /api/incidents/<incident_id>/tasks
  Purpose: Get tasks assigned to incident
  Input: incident_id (path), page, limit
  Output: [{ id, title, status, assigned_to, created_at, ... }]
  File: api_v1_extended.py
  Primary: ✅ YES

POST /api/incidents/<incident_id>/tasks
  Purpose: Create new task for incident
  Input: { title, description, assigned_to }
  Output: { id, task_id, created_at }
  File: api_v1_extended.py
  Primary: ✅ YES
```

### SOAR AUTOMATION (4 endpoints)
```
GET  /api/v1/soar/actions
  Purpose: List all available automation actions (playbooks)
  Input: None
  Output: { data: [{ id, name, description }], total: 50 }
  File: api_v1_actions.py
  Primary: ✅ YES

POST /api/v1/soar/execute
  Purpose: Execute SOAR playbook manually
  Input: { playbook_id: "...", incident_id: "...", inputs: {...} }
  Output: { job_id, execution_id, status: "started" }
  File: api_v1_actions.py
  Primary: ✅ YES

GET  /api/v1/soar/history
  Purpose: View past automation executions
  Input: page, limit, status, playbook_id
  Output: [{ execution_id, playbook_id, status, outputs, completed_at, ... }]
  File: api_v1_actions.py
  Primary: ✅ YES

GET  /api/v1/soar/executions
  Purpose: List playbook execution records (same as history)
  Input: page, limit, playbook_id, status
  Output: [{ execution_id, playbook_id, status, outputs, ... }]
  File: api_v1_actions.py
  Primary: ✅ YES
  Note: Same as GET /api/v1/soar/history (CONSOLIDATE ⚠️)
```

### ACCESS CONTROL & JIT (8 endpoints)
```
GET  /api/access/jit-sessions
  Purpose: List just-in-time elevation sessions
  Input: page, limit, status
  Output: [{ id, session_id, user_id, status, expires_at, ... }]
  Files: api_v1_extended.py, api_v1_consolidated.py (DUPLICATE ⚠️)
  Primary: api_v1_extended.py

POST /api/access/jit-sessions
  Purpose: Create new JIT elevation request
  Input: { reason, requested_access_level, duration_minutes }
  Output: { session_id, status: "pending", expires_at }
  Files: api_v1_extended.py, api_v1_consolidated.py (DUPLICATE ⚠️)
  Primary: api_v1_extended.py

POST /api/access/jit-sessions/<session_id>/approve
  Purpose: Approve temporary JIT elevation
  Input: session_id (path)
  Output: { session_id, status: "approved", active_until }
  File: api_v1_extended.py
  Primary: ✅ YES

POST /api/access/jit-sessions/<session_id>/revoke
  Purpose: Revoke JIT elevation early
  Input: session_id (path)
  Output: { session_id, status: "revoked", revoked_at }
  File: api_v1_extended.py
  Primary: ✅ YES

POST /api/access/jit-sessions/batch-action
  Purpose: Approve or revoke multiple JIT sessions in one request
  Input: { "actions": [{ "session_id": "...", "action": "approve|revoke" }] }
  Output: { processed, results }
  File: api_v1_consolidated.py
  Primary: ✅ CONSOLIDATION

GET  /api/access/review
  Purpose: Get access review queue
  Input: page, limit, type
  Output: [{ id, user_id, action, status, expires_at, ... }]
  File: api_v1_consolidated.py
  Primary: ✅ YES
```

### THREAT INTELLIGENCE (5 endpoints)
```
GET  /api/threat-intelligence/feeds
  Purpose: List threat intelligence feeds
  Input: page, limit
  Output: [{ id, feed_id, name, source, last_sync, ... }]
  Files: api_v1_extended.py, api_v1_consolidated.py (DUPLICATE ⚠️)
  Primary: api_v1_extended.py

POST /api/threat-intelligence/feeds
  Purpose: Add new threat feed
  Input: { name, source_url, sync_interval_hours }
  Output: { feed_id, created_at }
  File: api_v1_extended.py
  Primary: ✅ YES

POST /api/threat-intelligence/feeds/<feed_id>/sync
  Purpose: Manually trigger threat feed synchronization
  Input: feed_id (path)
  Output: { feed_id, sync_status: "started", records_updated: number }
  File: api_v1_extended.py
  Primary: ✅ YES
```

### DATABASE OPERATIONS (6 endpoints - /api/db)
```
GET  /api/db/tables
  Purpose: Discover database schema tables
  Input: None
  Output: [{ name, columns: [...], row_count }]
  File: api_v1_db.py
  Primary: ✅ YES

GET  /api/db/tables/<table_name>
  Purpose: Query table contents with filters
  Input: page, limit, filter, sort
  Output: [{ rows }]
  File: api_v1_db.py
  Primary: ✅ YES

POST /api/db/tables/<table_name>
  Purpose: Insert new database table row
  Input: { column: value, ... }
  Output: { id, inserted_id }
  File: api_v1_db.py
  Primary: ✅ YES

PUT  /api/db/tables/<table_name>
  Purpose: Update table record
  Input: { id: "...", column: new_value, ... }
  Output: { rows_affected: 1 }
  File: api_v1_db.py
  Primary: ✅ YES

DELETE /api/db/tables/<table_name>
  Purpose: Delete table record
  Input: { id: "..." }
  Output: { rows_deleted: 1 }
  File: api_v1_db.py
  Primary: ✅ YES

POST /api/db/query
  Purpose: Execute custom SQL query (admin only)
  Input: { sql: "SELECT...", params: [...] }
  Output: { rows: [...], count: number }
  File: api_v1_db.py
  Primary: ✅ YES
```

### LOG INGESTION & DEVICES (4 endpoints)
```
POST /api/ingest/events
  Purpose: Ingest security events from sources
  Input: [{ source, event_type, data, timestamp }]
  Output: { ingested: number, errors: number }
  File: api_ingestion.py
  Primary: ✅ YES

POST /api/logs/ingest
  Purpose: Ingest raw logs (same as /ingest/events)
  Input: [{ message, source, timestamp }]
  Output: { ingested: number }
  File: api_ingestion.py
  Primary: ✅ YES

GET  /api/devices
  Purpose: List all telemetry collection devices
  Input: page, limit, trust_status
  Output: [{ device_id, name, status, last_seen, ... }]
  File: api_ingestion.py
  Primary: ✅ YES

PATCH /api/devices/<device_id>/trust
  Purpose: Trust or quarantine telemetry device
  Input: { trusted: true }
  Output: { device_id, trust_status }
  File: api_ingestion.py
  Primary: ✅ YES
```

### REPORTS (5 endpoints)
```
GET  /api/reports
  Purpose: List generated reports
  Input: page, limit, status
  Output: [{ id, report_id, title, status, created_at, ... }]
  File: api_v1_reports.py
  Primary: ✅ YES

POST /api/reports
  Purpose: Generate new report
  Input: { title, report_type: "incident|alert|security", date_range }
  Output: { report_id, status: "generating" }
  Files: api_v1_consolidated.py, api_v1_reports.py (DUPLICATE ⚠️)
  Primary: api_v1_reports.py

GET  /api/reports/<report_id>/status
  Purpose: Check report generation progress
  Input: report_id (path)
  Output: { report_id, status, progress: 0-100, created_at }
  File: api_v1_reports.py
  Primary: ✅ YES

GET  /api/reports/<report_id>/download
  Purpose: Download generated report
  Input: report_id (path)
  Output: PDF/CSV file
  File: api_v1_reports.py
  Primary: ✅ YES

GET  /api/reports/download
  Purpose: Download report by ID (alternative)
  Input: report_id (query param)
  Output: PDF/CSV file
  File: api_v1_reports.py
  Primary: ✅ YES
```

### SETTINGS & DETECTION RULES (5 endpoints)
```
GET  /api/settings
  Purpose: Get all system settings
  Input: None
  Output: { general: {...}, security: {...}, notifications: {...} }
  File: api_v1_actions.py
  Primary: ✅ YES

PUT  /api/settings
  Purpose: Update system settings
  Input: { section: {...} }
  Output: { updated_at, changes: number }
  File: api_v1_actions.py
  Primary: ✅ YES

PATCH /api/settings/<section>
  Purpose: Update specific settings section
  Input: { key: value, ... }
  Output: { section, updated_at }
  File: api_v1_consolidated.py
  Primary: ✅ YES

GET  /api/settings/history
  Purpose: View settings change history
  Input: page, limit, section
  Output: [{ changed_by, change, timestamp, ... }]
  File: api_v1_consolidated.py
  Primary: ✅ YES

POST /api/detection-rules/<rule_id>/test
  Purpose: Test detection rule against data
  Input: { test_data: {...} }
  Output: { matches: number, result: true|false }
  File: api_v1_consolidated.py
  Primary: ✅ YES

GET  /api/detection-rules/<rule_id>/versions
  Purpose: View rule evolution/changes
  Input: rule_id (path), limit
  Output: [{ version, changed_by, changes, created_at, ... }]
  File: api_v1_consolidated.py
  Primary: ✅ YES
```

### CORPORATE PORTAL (17 endpoints - /api/corporate)
```
POST /api/corporate/auth/login
  Purpose: Corporate portal authentication
  Input: { username, password, mfa_token }
  Output: { session_id, token, expires_at }
  File: api_corporate.py
  Primary: ✅ YES

POST /api/corporate/auth/logout
  Purpose: Logout from corporate portal
  Input: None
  Output: { logged_out: true }
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/sessions
  Purpose: List active corporate sessions
  Input: page, limit
  Output: [{ session_id, user, login_time, last_activity, ... }]
  File: api_corporate.py
  Primary: ✅ YES

POST /api/corporate/sessions/<session_id>/revoke
  Purpose: Revoke active corporate session
  Input: session_id (path)
  Output: { session_id, status: "revoked" }
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/me
  Purpose: Get current user profile
  Input: None
  Output: { id, name, email, role, permissions: [...] }
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/dashboard
  Purpose: Get corporate dashboard metrics
  Input: None
  Output: { total_users, total_incidents, recent_activities: [...] }
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/systems
  Purpose: List corporate systems
  Input: page, limit
  Output: [{ id, name, status, health_score, ... }]
  File: api_corporate.py
  Primary: ✅ YES

PATCH /api/corporate/systems/<system_id>
  Purpose: Update system configuration
  Input: { field: value, ... }
  Output: { system_id, updated_at }
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/tasks
  Purpose: Get corporate tasks
  Input: page, limit, status
  Output: [{ task_id, title, status, assigned_to, ... }]
  File: api_corporate.py
  Primary: ✅ YES

POST /api/corporate/tasks
  Purpose: Create new corporate task
  Input: { title, description, assigned_to }
  Output: { task_id, created_at }
  File: api_corporate.py
  Primary: ✅ YES

PATCH /api/corporate/tasks/<task_id>
  Purpose: Update corporate task
  Input: { status, assigned_to, ... }
  Output: { task_id, updated_at }
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/announcements
  Purpose: Get corporate announcements
  Input: page, limit
  Output: [{ id, title, content, created_at, ... }]
  File: api_corporate.py
  Primary: ✅ YES

POST /api/corporate/announcements
  Purpose: Create announcement
  Input: { title, content, visibility }
  Output: { id, created_at }
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/activity
  Purpose: Get activity log
  Input: page, limit, user_id, action
  Output: [{ user, action, resource, timestamp, ... }]
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/admin/overview
  Purpose: Admin system overview
  Input: None
  Output: { total_users, total_systems, alerts, incidents, ... }
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/users
  Purpose: List corporate users
  Input: page, limit, role
  Output: [{ id, name, email, role, status, ... }]
  File: api_corporate.py
  Primary: ✅ YES

GET  /api/corporate/auth-stats
  Purpose: Get authentication statistics
  Input: time_range
  Output: { total_logins, failed_attempts, mfa_usage, ... }
  File: api_corporate.py
  Primary: ✅ YES
```

### SCADA/OT CONTROL (3 endpoints)
```
POST /api/playbooks/<playbook_id>/executions
  Purpose: Execute specific playbook
  Input: { incident_id: "...", inputs: {...} }
  Output: { execution_id, status: "running" }
  File: api_v1_consolidated.py
  Primary: ✅ YES

GET  /api/scada/<path:subpath>
  Purpose: Generic SCADA gateway proxy (catchall)
  Input: Any SCADA-related path
  Output: Proxied response from SCADA system
  File: api_v1_consolidated.py
  Primary: ✅ YES (CATCHALL)

POST /api/scada/<path:subpath>
  Purpose: Generic SCADA control endpoint (catchall)
  Input: Any SCADA-related POST request
  Output: Proxied response from SCADA system
  File: api_v1_consolidated.py
  Primary: ✅ YES (CATCHALL)
```

### DASHBOARD & METRICS (8 endpoints)
```
GET  /api/overview
  Purpose: Get SIEM overview metrics
  Input: None
  Output: { total_alerts, total_incidents, critical_count, ... }
  File: api_v1.py
  Primary: ✅ YES

GET  /api/dashboard-data
  Purpose: Get dashboard chart data
  Input: date_range, metric_type
  Output: { labels: [...], datasets: [...] }
  File: api_v1.py
  Primary: ✅ YES

GET  /api/raw-stream
  Purpose: Get real-time raw event stream (WebSocket ready)
  Input: None
  Output: [{ timestamp, event, ... }]
  File: api_v1.py
  Primary: ✅ YES

GET  /api/capabilities
  Purpose: Get system capabilities
  Input: None
  Output: { features: [...], limits: {...} }
  File: api_v1.py
  Primary: ✅ YES

GET  /api/audit-events
  Purpose: Get audit trail
  Input: page, limit, user_id, action
  Output: [{ user, action, resource, timestamp, ... }]
  File: api_v1.py
  Primary: ✅ YES

GET  /api/overview/metrics
  Purpose: Get overview metrics (same as /overview)
  Input: None
  Output: { total_alerts, total_incidents, ... }
  File: api_v1_consolidated.py
  Primary: ✅ YES (CONSOLIDATION)

GET  /api/data-sources/metrics
  Purpose: Get data source metrics
  Input: None
  Output: { ingestion_rate, record_count, sources: {...} }
  Files: api_v1_extended.py, api_v1_consolidated.py (DUPLICATE ⚠️)
  Primary: api_v1_consolidated.py
```

### AUTHENTICATION (4 endpoints)
```
POST /api/auth/login
  Purpose: SIEM authentication
  Input: { username, password }
  Output: { token, session_id, expires_at }
  File: api_v1.py
  Primary: ✅ YES

POST /api/auth/logout
  Purpose: SIEM logout
  Input: None
  Output: { logged_out: true }
  File: api_v1.py
  Primary: ✅ YES

GET  /api/auth/me
  Purpose: Get current user
  Input: None
  Output: { id, username, role, permissions: [...] }
  File: api_v1.py
  Primary: ✅ YES

GET  /api/auth/sessions
  Purpose: List user sessions
  Input: None
  Output: [{ session_id, created_at, last_activity, ... }]
  File: api_v1.py
  Primary: ✅ YES
```

---

## ⚠️ CRITICAL ISSUES SUMMARY

### Duplicate Endpoints (9 found)
See `rules.md` for complete details on consolidation.

### Functional Overlap (16 patterns)
Multiple files implementing same functionality.

### Recommended Consolidations
1. Batch alert operations (3 → 1 call)
2. Batch incident operations (3 → 1 call)
3. Batch access control (2 → 1 call)
4. Batch database operations (5 → 1 call)

---

## 📋 ENDPOINT USAGE GUIDE

### How to Find an Endpoint
1. **By Resource:** Find resource type above (ALERTS, INCIDENTS, etc.)
2. **By Operation:** GET (list/read), POST (create), PUT (update), PATCH (modify), DELETE (remove)
3. **By File:** Check which api_*.py file it's in

### How to Use an Endpoint
```
Method:  HTTP method (GET, POST, etc.)
Path:    Full path starting with /api
Input:   Query params or JSON body
Output:  Response format
File:    Which file implements it
Primary: Whether this is the canonical endpoint
```

### Example: Assign Alert to Analyst
```
Endpoint: POST /api/alerts/assign
Input: { "alert_ids": ["alert-123", "alert-456"], "assignee_id": "user-789" }
Output: { "assigned": 2, "failed": 0 }
```

---

## 🔗 Related Documents

- `rules.md` - API architecture rules and consolidation plan
- `ALL_API_ENDPOINTS_WORKING_PATHS.md` - Which endpoints actually work and which are broken

---

**Generated:** 2026-09-25  
**Verification:** All 106 endpoints cataloged and verified  
**Duplicates Found:** 9 (MUST BE FIXED - see rules.md)  
**Status:** READY FOR CONSOLIDATION
