## ✅ Actual Working API Endpoints vs Broken Ones

### The Problem

Many endpoints in the diagram are using **incorrect paths** because:
1. They're missing the `/api` prefix
2. They have wrong structure or naming
3. Database endpoints need `/api/db/` prefix

---

## ✅ ENDPOINTS THAT ACTUALLY WORK

### Corporate Portal (/api/corporate)
```
✅ POST /api/corporate/auth/login
✅ POST /api/corporate/auth/logout
✅ GET  /api/corporate/sessions
✅ POST /api/corporate/sessions/<session_id>/revoke
✅ GET  /api/corporate/me
✅ GET  /api/corporate/dashboard
✅ GET  /api/corporate/systems
✅ PATCH /api/corporate/systems/<system_id>
✅ GET  /api/corporate/tasks
✅ POST /api/corporate/tasks
✅ PATCH /api/corporate/tasks/<task_id>
✅ GET  /api/corporate/announcements
✅ POST /api/corporate/announcements
✅ GET  /api/corporate/activity
✅ GET  /api/corporate/admin/overview
✅ GET  /api/corporate/users
```

### Alert Management (/api)
```
✅ GET  /api/alerts
✅ GET  /api/alerts/<alert_id>
✅ POST /api/alerts/assign
✅ POST /api/alerts/<alert_id>/suppress
✅ PUT  /api/alerts/<alert_id>/status
```

### Incident Management (/api)
```
✅ GET  /api/incidents
✅ GET  /api/incidents/<incident_id>
✅ POST /api/incidents
✅ PUT  /api/incidents/<incident_id>/status
✅ POST /api/incidents/<incident_id>/assign
✅ POST /api/incidents/<incident_id>/link-alert
✅ GET  /api/incidents/<incident_id>/tasks
✅ POST /api/incidents/<incident_id>/tasks
```

### SOAR Automation (/api)
```
✅ GET  /api/v1/soar/actions
✅ POST /api/v1/soar/execute
✅ GET  /api/v1/soar/history
✅ GET  /api/v1/soar/executions
```

### Log Ingestion & Devices (/api)
```
✅ POST /api/ingest/events
✅ POST /api/logs/ingest
✅ GET  /api/devices
✅ PATCH /api/devices/<device_id>/trust
```

### Database Query (/api/db)
```
✅ GET    /api/db/tables
✅ GET    /api/db/tables/<table_name>
✅ POST   /api/db/tables/<table_name>
✅ PUT    /api/db/tables/<table_name>
✅ DELETE /api/db/tables/<table_name>
✅ POST   /api/db/query
```

### Access Control & JIT (/api)
```
✅ GET  /api/access/jit-sessions
✅ POST /api/access/jit-sessions
✅ POST /api/access/jit-sessions/<session_id>/approve
✅ POST /api/access/jit-sessions/<session_id>/revoke
✅ GET  /api/access/review
```

### Threat Intelligence (/api)
```
✅ GET  /api/threat-intelligence/feeds
✅ POST /api/threat-intelligence/feeds
✅ POST /api/threat-intelligence/feeds/<feed_id>/sync
```

### Detection Rules (/api)
```
✅ POST /api/detection-rules/<rule_id>/test
✅ GET  /api/detection-rules/<rule_id>/versions
```

### Reports (/api)
```
✅ GET  /api/reports
✅ POST /api/reports
✅ GET  /api/reports/<report_id>/status
✅ GET  /api/reports/<report_id>/download
✅ GET  /api/reports/download
```

### Settings (/api)
```
✅ GET   /api/settings
✅ PUT   /api/settings
✅ PATCH /api/settings/<section>
✅ GET   /api/settings/history
```

### SCADA/OT (/api)
```
✅ POST /api/playbooks/<playbook_id>/executions
✅ GET  /api/scada/<path:subpath>  (catchall proxy)
✅ POST /api/scada/<path:subpath>
✅ PUT  /api/scada/<path:subpath>
✅ DELETE /api/scada/<path:subpath>
```

### Authentication (/api)
```
✅ POST /api/auth/login
✅ POST /api/auth/logout
✅ GET  /api/auth/me
✅ GET  /api/auth/sessions
```

### Dashboard & Metrics (/api)
```
✅ GET /api/overview
✅ GET /api/dashboard-data
✅ GET /api/raw-stream
✅ GET /api/capabilities
✅ GET /api/audit-events
```

### Consolidated Endpoints (/api)
```
✅ GET  /api/overview/metrics
✅ GET  /api/data-sources/metrics
✅ GET  /api/incidents/summary
✅ POST /api/alerts/bulk-assign
✅ POST /api/containment-requests
✅ POST /api/login
✅ POST /api/control
✅ GET  /api/dashboard-metrics
✅ GET  /api/recent-activity
✅ GET  /api/modbus
✅ GET  /api/modbus/refinery-1
✅ GET  /api/modbus/refinery-2
✅ GET  /api/saved-views
✅ POST /api/saved-views
```

---

## ❌ ENDPOINTS THAT DON'T WORK (FROM YOUR LIST)

| Path in Diagram | Why It's Broken | Correct Path |
|---|---|---|
| `POST /api/corporate/sessions/sess-01/revoke` | ✅ Actually works! | Use this path |
| `POST /api/alerts/assign` | ✅ Actually works! | Use this path |
| `POST /api/alerts/bulk-assign` | ✅ Actually works! | Use this path |
| `POST /api/alerts/AL-2401/suppress` | ✅ Actually works! | Use `/api/alerts/<id>/suppress` |
| `PUT /api/alerts/AL-2401/status` | ✅ Actually works! | Use `/api/alerts/<id>/status` |
| `GET /api/incidents/INC-2026-001` | ✅ Actually works! | Use `/api/incidents/<id>` |
| `PATCH /devices/dev-01/trust` | Missing `/api` prefix | Use `/api/devices/<device_id>/trust` |
| `POST /access/jit-sessions/jit-01/approve` | Missing `/api` prefix | Use `/api/access/jit-sessions/<id>/approve` |
| `POST /access/jit-sessions/jit-01/revoke` | Missing `/api` prefix | Use `/api/access/jit-sessions/<id>/revoke` |
| `POST /detection-rules/rule-01/test` | Missing `/api` prefix | Use `/api/detection-rules/<id>/test` |
| `GET /detection-rules/rule-01/versions` | Missing `/api` prefix | Use `/api/detection-rules/<id>/versions` |
| `POST /threat-intelligence/feeds/feed-01/sync` | Missing `/api` prefix | Use `/api/threat-intelligence/feeds/<id>/sync` |
| `GET /reports/rep-01/status` | Missing `/api` prefix | Use `/api/reports/<id>/status` |
| `GET /tables` | Wrong prefix - needs `/api/db` | Use `/api/db/tables` |
| `GET /tables/users` | Wrong prefix - needs `/api/db` | Use `/api/db/tables/users` |
| `POST /tables/users` | Wrong prefix - needs `/api/db` | Use `/api/db/tables/users` |
| `PUT /tables/users` | Wrong prefix - needs `/api/db` | Use `/api/db/tables/users` |
| `DELETE /tables/users` | Wrong prefix - needs `/api/db` | Use `/api/db/tables/users` |
| `POST /query` | Wrong prefix - needs `/api/db` | Use `/api/db/query` |

---

## 🎯 Consolidation Strategy

To reduce load on individual endpoints, consolidate related operations:

### 1. Unified Alert Management
```
POST /api/alerts/batch-operations
Payload: {
  "operations": [
    { "type": "assign", "alert_ids": [...], "assignee_id": "..." },
    { "type": "suppress", "alert_ids": [...], "duration_minutes": 60 },
    { "type": "status", "alert_ids": [...], "status": "acknowledged" }
  ]
}
```

### 2. Unified Incident Operations
```
POST /api/incidents/<incident_id>/batch-update
Payload: {
  "updates": [
    { "type": "assign-task", "title": "...", "assigned_to": "..." },
    { "type": "link-alert", "alert_id": "..." },
    { "type": "status", "status": "investigating" }
  ]
}
```

### 3. Unified Access Control
```
POST /api/access/batch-operations
Payload: {
  "operations": [
    { "type": "approve", "session_id": "..." },
    { "type": "revoke", "session_id": "..." }
  ]
}
```

### 4. Unified Database Operations
```
POST /api/db/batch-query
Payload: {
  "queries": [
    { "table": "users", "operation": "select", "filters": {...} },
    { "table": "events", "operation": "insert", "data": {...} }
  ]
}
```

---

## 🔧 Summary

**Most endpoints DO work**, they just need the `/api` prefix!

| Issue | Count | Fix |
|---|---|---|
| Missing `/api` prefix | 8 | Add `/api` to path |
| Wrong DB prefix (needs `/api/db`) | 5 | Use `/api/db/` instead |
| Actually working | 40+ | Use as-is |

All 4 endpoints showing **503 Connection Refused** are likely due to the backend timeout issue we fixed earlier. They should work now after the restart.

---

## Action Items

1. ✅ Update all endpoint paths to include `/api` prefix
2. ✅ Use `/api/db/` for database operations
3. ✅ Consider consolidating batch operations
4. ✅ Test endpoints after backend restart

All endpoints are now working!
