# GotXA SIEM/SOAR Platform - Complete API Reference

## Overview
GotXA is a production-grade Security Information and Event Management (SIEM) and Security Orchestration, Automation and Response (SOAR) platform. This document provides a complete reference for all REST API endpoints.

**Base URL:** `http://localhost:5000`  
**API Path Prefix:** `/api`  
**Authentication:** Bearer token (via `X-User-ID` header or `Authorization: Bearer <token>`)

---

## Table of Contents
1. [Core SIEM Endpoints](#core-siem-endpoints)
2. [Alert Management](#alert-management)
3. [Incident Management](#incident-management)
4. [SOAR Automation](#soar-automation)
5. [Access Control & JIT](#access-control--jit)
6. [Settings & Configuration](#settings--configuration)
7. [Reports & Export](#reports--export)
8. [Authentication & Sessions](#authentication--sessions)
9. [Database Query](#database-query)
10. [SCADA/OT Control](#scadaot-control)
11. [Log Ingestion](#log-ingestion)
12. [Corporate Portal](#corporate-portal)

---

## CORE SIEM ENDPOINTS

All SIEM endpoints below are served under `/api`. For example, use
`http://localhost:5000/api/overview` or `http://localhost/api/overview` through
the gateway. Corporate Portal endpoints are served under `/api/corporate`.

### Overview & Dashboard

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/overview` | GET | None | KPIs, charts, alerts, source health | Get dashboard overview metrics and health status |
| `/overview/metrics` | GET | None | Active incidents, ingestion rate, critical alerts | Get consolidated SIEM metrics |
| `/dashboard-data` | GET | None | Total logs, alerts, critical alerts, hosts | Legacy dashboard endpoint (backward compatible) |
| `/dashboard-metrics` | GET | None | System health, performance metrics | Get system dashboard metrics |
| `/raw-stream` | GET | `limit`, `source`, `category` | Raw log events with IST timestamps | Stream live logs for real-time dashboard |
| `/data-sources/metrics` | GET | None | Source health, ingestion rates, status | Get data source connector health |
| `/recent-activity` | GET | None | Recent incidents, alerts, tasks | Get activity feed |

---

## ALERT MANAGEMENT

### List & Retrieve Alerts

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/alerts` | GET | `page`, `page_size`, `severity`, `status`, `assignee` | Paginated alert list with enriched forensics | List all alerts with filtering and IST timestamps |
| `/alerts/<alert_id>` | GET | `alert_id` (path param) | Alert details, forensic telemetry, related alerts | Get full alert investigation context |
| `/alerts/assign` | POST | `{ "alert_ids": [...], "assignee_id": "..." }` | Assignment confirmation | Bulk assign alerts to analyst |
| `/alerts/bulk-assign` | POST | `{ "alert_ids": [...], "assignee_id": "..." }` | Assignment confirmation | Consolidated bulk assign endpoint |
| `/alerts/<alert_id>/suppress` | POST | `{ "duration_minutes": 60, "reason": "..." }` | Suppression confirmation | Suppress alert for specified duration |
| `/alerts/<alert_id>/status` | PUT | `{ "status": "open\|acknowledged\|resolved" }` | Status update confirmation | Update alert status in workflow |

---

## INCIDENT MANAGEMENT

### Create & Manage Incidents

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/incidents` | GET | `page`, `page_size`, `status`, `priority` | Paginated incident list | List all incidents with filtering |
| `/incidents` | POST | `{ "title": "...", "severity": "...", "source_alert_ids": [...] }` | New incident with ID | Create incident from alerts |
| `/incidents/<incident_id>` | GET | `incident_id` (path param) | Full incident details, timeline, artifacts | Get incident investigation details |
| `/incidents/<incident_id>/status` | PUT | `{ "status": "open\|investigating\|contained\|resolved" }` | Status update confirmation | Update incident lifecycle status |
| `/incidents/<incident_id>/assign` | POST | `{ "owner_id": "...", "team_id": "..." }` | Assignment confirmation | Assign incident to team/analyst |
| `/incidents/<incident_id>/link-alert` | POST | `{ "alert_id": "..." }` | Link confirmation | Link additional alert to incident |
| `/incidents/<incident_id>/tasks` | GET | `page`, `limit` | List of tasks for incident | Get all tasks associated with incident |
| `/incidents/<incident_id>/tasks` | POST | `{ "title": "...", "description": "..." }` | New task created | Create task for incident |
| `/incidents/summary` | GET | None | Open tasks, overdue items, post-incident actions | Get incident workflow summary |

---

## SOAR AUTOMATION

### Playbook Execution & Task Management

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/v1/soar/actions` | GET | None | Available SOAR actions, playbook list | List all available automation actions |
| `/v1/soar/execute` | POST | `{ "playbook_id": "...", "incident_id": "...", "inputs": {...} }` | Execution confirmation, job_id | Execute SOAR playbook manually |
| `/v1/soar/history` | GET | `page`, `limit`, `status` | Playbook execution history | View past automation executions |
| `/v1/soar/executions` | GET | `page`, `limit`, `playbook_id` | Active/completed playbook runs | List playbook execution records |
| `/playbooks/<playbook_id>/executions` | POST | `{ "incident_id": "...", "inputs": {...} }` | Execution confirmation | Execute specific playbook |
| `/containment-requests` | POST | `{ "type": "network\|asset\|user", "target": "...", "reason": "..." }` | Containment job_id | Request automated containment action |

---

## ACCESS CONTROL & JIT

### Just-In-Time Privilege Management

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/access/jit-sessions` | GET | `page`, `limit`, `status` | JIT session list with expiry | List active JIT privilege sessions |
| `/access/jit-sessions` | POST | `{ "user_id": "...", "privilege_level": "...", "duration_minutes": 60 }` | Session approval + token | Request temporary elevated privileges |
| `/access/jit-sessions/<session_id>/approve` | POST | None | Approval confirmation | Approve JIT session request |
| `/access/jit-sessions/<session_id>/revoke` | POST | None | Revocation confirmation | Revoke JIT session immediately |
| `/access/review` | GET | None | Recent privilege requests, approvals | Review access request audit trail |

---

## SETTINGS & CONFIGURATION

### System Configuration

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/settings` | GET | `page`, `limit` | Current settings by section | Retrieve system configuration |
| `/settings` | PUT | `{ "section": "alerts", "key": "retention_days", "value": 90 }` | Update confirmation | Update system setting |
| `/settings/<section>` | PATCH | `{ "key1": "value1", "key2": "value2" }` | Bulk update confirmation | Update multiple settings in section |
| `/settings/history` | GET | `page`, `limit`, `section` | Settings change audit trail | View configuration change history (IST timestamps) |
| `/detection-rules/<rule_id>/test` | POST | `{ "test_data": {...} }` | Test result (pass/fail) | Test detection rule against data |
| `/detection-rules/<rule_id>/versions` | GET | `limit` | Rule version history | View rule evolution/changes |

---

## THREAT INTELLIGENCE

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/threat-intelligence/feeds` | GET | None | Active threat feeds, last update time | List threat intelligence sources |
| `/threat-intelligence/feeds` | POST | `{ "name": "...", "url": "...", "type": "..." }` | Feed created confirmation | Add new threat intelligence feed |
| `/threat-intelligence/feeds/<feed_id>/sync` | POST | None | Sync status | Manually sync threat feed |

---

## REPORTS & EXPORT

### Report Generation & Asset Export

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/reports` | GET | `page`, `limit` | List of generated reports | Get all reports with status |
| `/reports` | POST | `{ "type": "incident\|alert\|soar", "date_range": {...}, "format": "pdf" }` | Report job_id + status | Generate compliance/incident report (async) |
| `/reports/<report_id>` | GET | `report_id` (path param) | Report metadata + status | Check report generation status |
| `/reports/<report_id>/status` | GET | `report_id` (path param) | Generation status (pending/complete/failed) | Get report generation progress |
| `/reports/<report_id>/download` | GET | `report_id` (path param) | Binary PDF file with IST timestamps | Download generated report |
| `/reports/download` | GET | `report_id` (query) | Binary PDF file | Alternative download endpoint |
| `/assets/export` | GET | `format` (csv/json), `filter` | CSV/JSON asset inventory | Export asset inventory for backup |

---

## AUTHENTICATION & SESSIONS

### User Session Management

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/auth/login` | POST | `{ "username": "...", "password": "...", "role": "..." }` | Access token, user info, expiry | Authenticate to SIEM and get session token |
| `/auth/logout` | POST | Authorization header | Logout confirmation | Revoke session token |
| `/auth/me` | GET | Authorization header | Current user info, session metadata, IST timezone | Get authenticated user profile |
| `/auth/sessions` | GET | Authorization header | List of active sessions | View all active user sessions |
| `/login` | POST | `{ "username": "...", "password": "..." }` | Session token | Generic/simple login endpoint |

---

## DATABASE QUERY

### Direct Table Access (Admin Only)

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/tables` | GET | None | List of available tables with columns | Discover database schema |
| `/tables/<table_name>` | GET | `page`, `limit`, `filter` | Table data with pagination | Query table contents |
| `/tables/<table_name>` | POST | JSON row data | Inserted row ID | Insert new record |
| `/tables/<table_name>` | PUT | `{ "id": "...", "column": "value" }` | Update confirmation | Update table record |
| `/tables/<table_name>` | DELETE | `{ "id": "..." }` | Deletion confirmation | Delete table record |
| `/query` | POST | `{ "sql": "SELECT ... FROM ...", "params": [...] }` | Query result set | Execute custom SQL query (admin only) |

---

## SCADA/OT CONTROL

### Industrial Control System Integration

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/v1/scada/control` | POST | `{ "machine_id": "r1_heater", "action": "SET_TEMP", "target_temperature": 75, "operator": "..." }` | Control confirmation, event_id | Send SCADA control command (audited) - **RECOMMENDED** |
| `/scada/control` | POST | `{ "machine_id": "...", "action": "...", "target_value": ... }` | Command execution result | Alternative SCADA endpoint |
| `/control` | POST | `{ "target": "plc", "parameter": "...", "value": ... }` | Execution status | Generic control proxy for any asset |
| `/modbus` | GET | `device_id`, `registers` | Modbus register values | Read Modbus TCP registers |
| `/modbus/refinery-1` | GET | None | Refinery PLC1 telemetry, temperature, pressure | Get Refinery PLC1 real-time status |
| `/modbus/refinery-2` | GET | None | Refinery PLC2 telemetry, temperature, pressure | Get Refinery PLC2 real-time status |
| `/scada/<path:subpath>` | GET/POST/PUT/DELETE | Proxy request | Proxy response | Generic SCADA gateway for any OT endpoint |
| `/dashboard-metrics` | GET | None | SCADA system KPIs, health status | Get OT/SCADA metrics |

---

## LOG INGESTION

### Event & Log Collection

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/ingest/events` | POST | `{ "source": "...", "event": {...}, "timestamp": "..." }` | Event ID, IST timestamp | Ingest security events from collectors |
| `/logs/ingest` | POST | `{ "logs": [...], "source": "..." }` | Ingestion confirmation | Ingest logs from collectors (same as ingest/events) |
| `/devices` | GET | None | List of connected devices/sources | List all registered log sources |
| `/devices/<device_id>/trust` | PATCH | `{ "trusted": true\|false }` | Trust status updated | Mark device as trusted/untrusted |

---

## CORPORATE PORTAL

### Corporate Portal Management

Corporate Portal URLs use the `/api/corporate` prefix. For example, login is
`POST /api/corporate/auth/login`.

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/api/corporate/auth/login` | POST | `{ "username": "...", "password": "..." }` | Session token, user profile, IST time | Authenticate to Corporate Portal ✅ **USE THIS** (not /portal/login) |
| `/auth/logout` | POST | Authorization header | Logout confirmation | Logout from Corporate Portal |
| `/sessions` | GET | Authorization header | List of user sessions | List active sessions in Corporate Portal |
| `/sessions/<session_id>/revoke` | POST | None | Revocation confirmation | Revoke specific session |
| `/auth-stats` | GET | Authorization header | Authentication statistics | Get portal auth metrics |
| `/me` | GET | Authorization header | Current user profile | Get current user information |
| `/dashboard` | GET | Authorization header | Corporate dashboard metrics | Get Corporate Portal dashboard |
| `/systems` | GET | Authorization header | List of systems | Get all connected systems |
| `/systems/<system_id>` | PATCH | `{ "status": "...", "config": {...} }` | Update confirmation | Update system configuration |
| `/tasks` | GET | Authorization header | List of corporate tasks | Get all tasks (paginated) |
| `/tasks` | POST | `{ "title": "...", "description": "...", "assignee": "..." }` | Task created | Create new task |
| `/tasks/<task_id>` | PATCH | `{ "status": "...", "notes": "..." }` | Update confirmation | Update task status/notes |
| `/announcements` | GET | Authorization header | List announcements | Get corporate announcements |
| `/announcements` | POST | `{ "title": "...", "message": "..." }` | Announcement created | Create new announcement |
| `/activity` | GET | Authorization header | Activity feed with IST timestamps | Get recent activity log |
| `/admin/overview` | GET | Authorization header | Admin dashboard metrics | Get admin overview (admin only) |
| `/users` | GET | Authorization header | List of users | Get all users (admin only) |

---

## ADDITIONAL & UTILITY ENDPOINTS

### System Health & Capabilities

| Endpoint | Method | Input | Output | Use Case |
|----------|--------|-------|--------|----------|
| `/capabilities` | GET | Authorization header | Available actions for current role | Check role-based permissions |
| `/audit-events` | GET | `page`, `limit`, `action`, `resource_type` | Audit trail records with IST timestamps | View system audit log |
| `/saved-views` | GET | Authorization header | User's saved dashboard views | List saved dashboard configurations |
| `/saved-views` | POST | `{ "name": "...", "filters": {...} }` | View saved confirmation | Save custom dashboard view |
| `/health` | GET | None | `{"status": "healthy"}` | System health check |

---

## Response Format

### Success Response
```json
{
  "data": {
    "id": "...",
    "status": "open",
    "timestamp": "2026-09-09 21:22:00",
    "formatted_time": "Sep 09, 2026, 09:22:00 PM"
  },
  "timestamp": "2026-09-09 21:22:00 IST"
}
```

### Error Response
```json
{
  "error": {
    "code": "NotFound",
    "message": "Alert not found",
    "details": {}
  },
  "timestamp": "2026-09-09 21:22:00 IST"
}
```

### List Response (Paginated)
```json
{
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 25,
  "pages": 4,
  "timestamp": "2026-09-09 21:22:00 IST"
}
```

---

## Authentication Headers

All endpoints require authentication via one of:

1. **Bearer Token (Recommended):**
```bash
Authorization: Bearer <token>
```

2. **User ID Header:**
```bash
X-User-ID: admin
```

3. **Session Cookie:**
```
Cookie: session_id=<token>
```

---

## Common Query Parameters

| Parameter | Type | Example | Description |
|-----------|------|---------|-------------|
| `page` | int | `1` | Page number (1-indexed) |
| `page_size` | int | `25` | Records per page (max 100) |
| `limit` | int | `50` | Alias for page_size |
| `sort` | string | `-created_at` | Sort field (- for descending) |
| `filter` | string | `status=open` | Filter condition |
| `status` | string | `open\|investigating\|resolved` | Filter by status |
| `severity` | string | `critical\|high\|medium\|low\|info` | Filter by severity |
| `assignee` | string | `user_id` | Filter by assignee |

---

## Timezone Configuration

**All timestamps are in IST (Indian Standard Time) - UTC+05:30**

- **Timezone:** Asia/Kolkata
- **UTC Offset:** +05:30 (fixed, no daylight saving)
- **Example:** `2026-09-09 21:22:00` = IST

**Three timestamp formats in responses:**
1. **Standard:** `2026-09-09 21:22:00` (ISO format with IST)
2. **Readable:** `Sep 09, 2026, 09:22:00 PM` (12-hour with IST)
3. **Time Only:** `09:22:00 PM` (12-hour format)

See [IST_TIMEZONE_CONFIGURATION.md](IST_TIMEZONE_CONFIGURATION.md) for detailed timezone setup.

---

## Example Usage

### Get Dashboard Metrics
```bash
curl -H "X-User-ID: admin" http://localhost:5000/api/overview/metrics
```

### List Alerts
```bash
curl -H "X-User-ID: admin" \
  "http://localhost:5000/api/alerts?page=1&page_size=25&severity=critical"
```

### Create Incident
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"title":"Security Incident","severity":"high","source_alert_ids":["alert-1"]}' \
  http://localhost:5000/api/incidents
```

### Execute SOAR Playbook
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"playbook_id":"pb-001","incident_id":"inc-123","inputs":{}}' \
  http://localhost:5000/api/v1/soar/execute
```

### Send SCADA Control Command ✅ RECOMMENDED
```bash
curl -X POST -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"machine_id":"r1_heater","action":"SET_TEMP","target_temperature":75,"operator":"admin"}' \
  http://localhost:5000/api/v1/scada/control
```

### Corporate Portal Login ✅ USE THIS
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}' \
  http://localhost:5000/auth/login
```

### Update Alert Status
```bash
curl -X PUT -H "X-User-ID: admin" -H "Content-Type: application/json" \
  -d '{"status":"acknowledged"}' \
  http://localhost:5000/api/alerts/alert-123/status
```

---

## Role-Based Access Control

### Admin
- Full access to all endpoints
- Can modify settings, rules, and configurations
- Can execute any SOAR action
- Can access admin-only endpoints

### SOC Manager
- Access to alerts and incidents
- Can assign incidents to teams
- Can execute approved SOAR playbooks
- Can view audit logs

### Analyst
- Can view assigned alerts and incidents
- Can create tasks
- Can execute SOAR tasks
- Cannot modify settings or system configuration

### Read-Only
- Can view all data
- Cannot create or modify anything
- Cannot execute any actions

---

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| NotFound | 404 | Resource not found |
| Forbidden | 403 | Access denied |
| Unauthorized | 401 | Authentication required |
| BadRequest | 400 | Invalid request format |
| InternalError | 500 | Server error |
| Conflict | 409 | Resource conflict |
| RateLimited | 429 | Too many requests |

---

## Performance & Limits

- **Max page size:** 100 records
- **Max query timeout:** 30 seconds
- **Rate limit:** 1000 requests/minute per user
- **Response timeout:** 60 seconds
- **Concurrent connections:** 100 per user
- **Max request body:** 10 MB

---

## Important Notes

### ⚠️ Deprecated Endpoints
- ❌ `POST /portal/login` - **DOES NOT EXIST**
  - ✅ Use `POST /auth/login` instead (Corporate Portal)
  - ✅ Use `POST /api/auth/login` instead (SIEM/SOAR)

### ✅ Verified Endpoints
- ✅ `POST /api/v1/scada/control` - **EXISTS AND WORKING** (Recommended)
- ✅ `POST /api/scada/control` - **EXISTS AND WORKING** (Alternative)
- ✅ `POST /api/control` - **EXISTS AND WORKING** (Generic)

---

## WebHooks & Events

Endpoints automatically trigger:
- Alert creation → SOAR correlation checks
- Incident creation → Playbook execution triggers
- Status changes → Audit logging with IST timestamps
- SCADA commands → Security event generation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-09-10 | Updated with verified endpoints, IST timezone, correct corporate portal login |
| 1.1 | 2026-09-09 | Added SCADA/OT endpoints, JIT access, fixed endpoint paths |
| 1.0 | 2026-09-09 | Initial release (60+ endpoints) |

---

## Support & Documentation

- **API Status:** http://localhost:5000/health
- **Schema Discovery:** http://localhost:5000/api/tables
- **Live Dashboards:**
  - SIEM Dashboard: http://localhost/
  - Corporate Portal: http://localhost/corp
  - SCADA Dashboard: http://localhost/scada
- **Complete Endpoint List:** See [API_ENDPOINT_VERIFICATION.md](API_ENDPOINT_VERIFICATION.md)
- **IST Configuration:** See [IST_TIMEZONE_CONFIGURATION.md](IST_TIMEZONE_CONFIGURATION.md)

---

**Last Updated:** September 10, 2026  
**Platform:** GotXA SIEM/SOAR v2.0  
**Status:** Production Ready ✅  
**Timezone:** IST (Asia/Kolkata - UTC+05:30)  
**Total Endpoints:** 100+ verified and documented
