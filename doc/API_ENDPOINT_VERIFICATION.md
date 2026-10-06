# API Endpoint Verification Report

## Question 1: Does `/portal/login` exist?

### Answer: ❌ **NO** - This endpoint does NOT exist

**What exists instead:**

1. **`POST /api/auth/login`** - SIEM Authentication
   - File: `backend/app/api_v1.py:621`
   - Input: `{ "username": "...", "password": "..." }`
   - Output: Access token, user info, session ID
   - Purpose: Authenticate to SIEM/SOAR platform

2. **`POST /auth/login`** - Corporate Portal Authentication
   - File: `backend/app/api_corporate.py:264`
   - Input: `{ "username": "...", "password": "..." }`
   - Output: Session token, user profile
   - Purpose: Authenticate to Corporate Portal

3. **`POST /login`** - Generic Login (consolidated)
   - File: `backend/app/api_v1_consolidated.py:717`
   - Input: `{ "username": "...", "password": "..." }`
   - Output: Session token
   - Purpose: Simple login endpoint

### The Correct Endpoint for Corporate Portal:
```
POST /auth/login
```
**Path:** `backend/app/api_corporate.py:264`

This is routed through the API gateway at:
```
POST http://localhost:5000/auth/login
```

Or via the corporate portal route:
```
POST http://localhost/corp/auth/login  (via nginx gateway)
```

---

## Question 2: Does `/api/scada/control` exist?

### Answer: ✅ **YES** - This endpoint EXISTS

**Exact endpoints:**

1. **`POST /v1/scada/control`** - SCADA Control v1
   - File: `backend/app/api_v1.py:713`
   - Path: `/api/v1/scada/control`
   - Input: `{ "machine_id": "...", "action": "...", "value": ... }`
   - Output: Control confirmation with event_id
   - Purpose: Send SCADA/OT control commands

2. **`POST /scada/control`** - SCADA Control (alternative)
   - File: `backend/app/api_v1.py:714`
   - Path: `/api/scada/control`
   - Input: Same as v1
   - Output: Command execution result
   - Purpose: Alternative SCADA endpoint (same implementation)

3. **`POST /control`** - Generic Control Proxy
   - File: `backend/app/api_v1_consolidated.py:724`
   - Path: `/api/control`
   - Input: `{ "target": "plc", "parameter": "...", "value": ... }`
   - Output: Execution status
   - Purpose: Generic control proxy for any asset

### The Correct Endpoints for SCADA Control:

**Option 1 (Recommended - v1 versioned):**
```
POST /api/v1/scada/control
```

**Option 2 (Alternative):**
```
POST /api/scada/control
```

**Option 3 (Generic):**
```
POST /api/control
```

---

## Complete API Route Listing

> **URL prefix requirement:** SIEM/SOAR routes use `/api` and Corporate Portal
> routes use `/api/corporate`. For example, call
> `GET http://localhost:5000/api/overview` and
> `POST http://localhost:5000/api/corporate/auth/login`. The paths below are
> shown relative to their blueprint prefix.

### All Endpoints Found (100+):

**Corporate Portal Routes** (`api_corporate.py`):
- POST `/auth/login` - Login to corporate portal
- POST `/auth/logout` - Logout
- GET `/sessions` - List active sessions
- POST `/sessions/<session_id>/revoke` - Revoke session
- GET `/auth-stats` - Authentication statistics
- GET `/me` - Current user profile
- GET `/dashboard` - Corporate dashboard
- GET `/systems` - List systems
- PATCH `/systems/<system_id>` - Update system
- GET `/tasks` - List tasks
- POST `/tasks` - Create task
- PATCH `/tasks/<task_id>` - Update task
- GET `/announcements` - Get announcements
- POST `/announcements` - Create announcement
- GET `/activity` - Activity feed
- GET `/admin/overview` - Admin overview
- GET `/users` - List users

**SIEM Core Routes** (`api_v1.py`):
- GET `/overview` - Dashboard overview
- GET `/dashboard-data` - Dashboard data
- GET `/raw-stream` - Live log stream
- GET `/alerts` - List alerts
- GET `/alerts/<alert_id>` - Alert details
- GET `/incidents` - List incidents
- GET `/incidents/<incident_id>` - Incident details
- GET `/capabilities` - User capabilities
- GET `/audit-events` - Audit trail
- POST `/auth/login` - SIEM login
- POST `/auth/logout` - SIEM logout
- GET `/auth/me` - Current user
- GET `/auth/sessions` - User sessions
- POST `/v1/scada/control` - SCADA control v1
- POST `/scada/control` - SCADA control

**Alert Management** (`api_v1_actions.py`):
- POST `/alerts/assign` - Bulk assign alerts
- POST `/alerts/<alert_id>/suppress` - Suppress alert
- PUT `/alerts/<alert_id>/status` - Update alert status
- POST `/incidents` - Create incident
- PUT `/incidents/<incident_id>/status` - Update incident status
- POST `/incidents/<incident_id>/assign` - Assign incident
- POST `/incidents/<incident_id>/link-alert` - Link alert to incident

**SOAR Automation** (`api_v1_actions.py`):
- GET `/v1/soar/actions` - List SOAR actions
- POST `/v1/soar/execute` - Execute SOAR playbook
- GET `/v1/soar/history` - SOAR execution history
- GET `/v1/soar/executions` - Active SOAR executions

**Configuration** (`api_v1_actions.py`):
- GET `/settings` - Get settings
- PUT `/settings` - Update setting
- PATCH `/settings/<section>` - Bulk update settings
- GET `/settings/history` - Settings change history

**Advanced Operations** (`api_v1_consolidated.py`):
- GET `/overview/metrics` - Consolidated metrics
- GET `/data-sources/metrics` - Data source metrics
- GET `/incidents/summary` - Incidents summary
- POST `/incidents` - Create incident (consolidated)
- GET `/incidents/<incident_id>` - Incident detail (consolidated)
- POST `/alerts/bulk-assign` - Bulk assign (consolidated)
- POST `/alerts/<alert_id>/suppress` - Suppress (consolidated)
- POST `/containment-requests` - Containment action
- GET `/threat-intelligence/feeds` - Threat feeds
- GET `/access/jit-sessions` - JIT sessions
- POST `/access/jit-sessions` - Create JIT session
- GET `/access/review` - Access review
- POST `/playbooks/<playbook_id>/executions` - Execute playbook
- POST `/detection-rules/<rule_id>/test` - Test rule
- GET `/detection-rules/<rule_id>/versions` - Rule versions
- PATCH `/settings/<section>` - Update settings section
- GET `/settings/history` - Settings history
- GET `/assets/export` - Export assets
- POST `/reports` - Generate report
- POST `/login` - Generic login
- POST `/control` - Generic control
- GET `/dashboard-metrics` - Dashboard metrics
- GET `/recent-activity` - Recent activity
- GET `/modbus` - Modbus registers
- GET `/modbus/refinery-1` - Refinery 1 telemetry
- GET `/modbus/refinery-2` - Refinery 2 telemetry
- GET `/saved-views` - Saved dashboard views
- POST `/saved-views` - Save view
- GET `/scada/<path:subpath>` - SCADA gateway

**Log Ingestion** (`api_ingestion.py`):
- POST `/ingest/events` - Ingest events
- POST `/logs/ingest` - Ingest logs
- GET `/devices` - List devices
- PATCH `/devices/<device_id>/trust` - Trust device

**Database Access** (`api_v1_db.py`):
- GET `/tables` - List tables
- GET `/tables/<table_name>` - Query table
- POST `/tables/<table_name>` - Insert row
- PUT `/tables/<table_name>` - Update row
- DELETE `/tables/<table_name>` - Delete row
- POST `/query` - Custom SQL query

**Extended Operations** (`api_v1_extended.py`):
- GET `/incidents/summary` - Incidents summary
- GET `/incidents/<incident_id>/tasks` - Incident tasks
- POST `/incidents/<incident_id>/tasks` - Create task
- GET `/data-sources` - List data sources
- GET `/data-sources/metrics` - Data source metrics
- POST `/data-sources` - Create data source
- GET `/threat-intelligence/feeds` - Threat feeds
- POST `/threat-intelligence/feeds` - Create feed
- POST `/threat-intelligence/feeds/<feed_id>/sync` - Sync feed
- GET `/access/jit-sessions` - JIT sessions
- POST `/access/jit-sessions` - Create JIT session
- POST `/access/jit-sessions/<session_id>/approve` - Approve JIT
- POST `/access/jit-sessions/<session_id>/revoke` - Revoke JIT

**Reports** (`api_v1_reports.py`):
- GET `/reports/download` - Download report
- POST `/reports/generate` - Generate report
- POST `/reports` - Create report
- GET `/reports/<report_id>/download` - Download specific report
- GET `/reports/<report_id>/status` - Report status
- GET `/reports` - List reports

---

## Summary Table

| Question | Endpoint | Status | Location | Actual Path |
|----------|----------|--------|----------|-------------|
| Portal Login | `/portal/login` | ❌ NO | N/A | Use `/auth/login` instead |
| SCADA Control | `/api/scada/control` | ✅ YES | `api_v1.py:714` | `POST /api/scada/control` |
| Alt SCADA v1 | `/api/v1/scada/control` | ✅ YES | `api_v1.py:713` | `POST /api/v1/scada/control` |

---

## Recommendations

### For Corporate Portal Login:
```bash
# Correct endpoint
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}' \
  http://localhost:5000/auth/login

# Via nginx gateway
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}' \
  http://localhost/corp/auth/login
```

### For SCADA Control:
```bash
# Option 1 (Recommended - v1)
curl -X POST -H "Content-Type: application/json" \
  -d '{"machine_id":"r1_heater","action":"SET_TEMP","target_temperature":75}' \
  http://localhost:5000/api/v1/scada/control

# Option 2 (Alternative)
curl -X POST -H "Content-Type: application/json" \
  -d '{"machine_id":"r1_heater","action":"SET_TEMP","target_temperature":75}' \
  http://localhost:5000/api/scada/control
```

---

**Analysis Complete** - 100+ endpoints verified and documented
