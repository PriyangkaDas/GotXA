# Project Rules & Operational Governance

> **🚨 CRITICAL DIRECTIVE FOR ALL AI AGENTS & DEVELOPERS:**  
> **DO NOT MODIFY, EDIT, REFACTOR, RENAME, OR DELETE ANY FILE IN THIS REPOSITORY WITHOUT EXPLICIT, UNAMBIGUOUS USER CONSENT.**  
> **READ-ONLY INSPECTION AND DIAGNOSTICS ARE THE DEFAULT OPERATIONAL MODE AT ALL TIMES.**

---

## 🛡️ PART 1: ZERO UNWANTED EDITS POLICY (MANDATORY)

### 1. Default Operational Mode: Strict Read-Only
- **No Unprompted Modifications:** Under no circumstances should any AI assistant, automated agent, or developer modify, rewrite, refactor, reorganize, or format any file in this repository unless the user has explicitly requested changes to that specific file and scope.
- **Diagnostics ≠ Edits:** Requests to "check", "inspect", "debug", "investigate", "explain", "review", or "find" must be handled strictly as read-only operations. Do not apply "fixes" without explicit authorization.
- **No Speculative Changes:** Never anticipate future requirements by adding unsolicited boilerplate, moving code around, changing project structures, or cleaning up working code.
- **Maintain Existing State:** If code works, is in progress, or contains temporary comments/breakpoints, leave it intact. Never assume code is "messy" and needs reformatting.

### 2. Protocol for Requesting & Making Changes
Whenever a modification is proposed or requested:
1. **Explain the Purpose:** State clearly what needs to be changed and why.
2. **Present the Diff / Scope:** Detail the exact files, functions, or lines that will be touched.
3. **Wait for Explicit Approval:** Receive explicit confirmation (e.g., "Yes, proceed with the edit") before touching or creating any file.
4. **Minimal Atomic Edits:** Make only the minimal surgical changes necessary. Do not modify adjacent or unrelated code.
5. **Preserve Documentation & Comments:** Never delete or alter existing comments, docstrings, or developer notes.

### 3. High-Security & Mission-Critical Files (Strict Lockdown)
The following files and directories are mission-critical. They must never be edited, deleted, or overwritten without explicit user approval:
- **SCADA & ICS Control Systems:**
  - `scada_gateway.py`
  - `modbus_plc_server.py`
  - `Dockerfile.scada`
  - `New_Machine/`
- **Configuration & Secrets:**
  - `.env`, `.env.example`, any credentials, tokens, or network configuration files.
- **Infrastructure & Containerization:**
  - `docker-compose.yml`
  - `Dockerfile.collector`
  - `Dockerfile.scada`
- **Data Ingestion & Collectors:**
  - `log_collector.py`
  - Ingestion endpoints and service logs.
- **Backend Core & Database:**
  - `backend/app/models.py`, `backend/app/db.py`, and database migration files.

### 4. Prohibited Destructive Actions
- **Destructive Git Commands:** `git reset --hard`, `git clean -fd`, `git checkout -- .`, or force pushing are strictly forbidden.
- **File Deletions / Purges:** Never delete or truncate files without explicit instructions.
- **Silent Deprecations:** Never remove API routes, functions, or database fields without formal deprecation and verification.
- **Dependency Mutability:** Never run global `pip install` or overwrite `requirements.txt` unless explicitly asked.

---

## 📐 PART 2: API ARCHITECTURE RULES & STANDARDS

**Last Updated:** 2026-09-25  
**Status:** ACTIVE - Prevents further degradation  
**Owner:** Backend Team  

---

### 🚨 CRITICAL ISSUES FOUND

#### 1. Duplicate Endpoints (9 DUPLICATES FOUND)

These endpoints are defined in MULTIPLE files - this must stop:

| Endpoint | Files | Status | Action Required |
|---|---|---|---|
| `GET /api/access/jit-sessions` | api_v1_consolidated.py, api_v1_extended.py | ❌ DUPLICATE | Remove from api_v1_extended.py |
| `GET /api/data-sources/metrics` | api_v1_consolidated.py, api_v1_extended.py | ❌ DUPLICATE | Remove from api_v1_extended.py |
| `GET /api/incidents/<id>` | api_v1_consolidated.py, api_v1.py | ❌ DUPLICATE | Remove from api_v1.py |
| `GET /api/incidents/summary` | api_v1_consolidated.py, api_v1_extended.py | ❌ DUPLICATE | Remove from api_v1_extended.py |
| `GET /api/threat-intelligence/feeds` | api_v1_consolidated.py, api_v1_extended.py | ❌ DUPLICATE | Remove from api_v1_extended.py |
| `POST /api/access/jit-sessions` | api_v1_consolidated.py, api_v1_extended.py | ❌ DUPLICATE | Remove from api_v1_extended.py |
| `POST /api/alerts/<id>/suppress` | api_v1_actions.py, api_v1_consolidated.py | ❌ DUPLICATE | Remove from api_v1_consolidated.py |
| `POST /api/incidents` | api_v1_actions.py, api_v1_consolidated.py | ❌ DUPLICATE | Remove from api_v1_consolidated.py |
| `POST /api/reports` | api_v1_consolidated.py, api_v1_reports.py | ❌ DUPLICATE | Remove from api_v1_consolidated.py |

---

### 📋 CONSOLIDATION PLAN

#### Phase 1: Remove Duplicates (IMMEDIATE)
These must be deleted to reduce load:

**api_v1_extended.py - REMOVE THESE:**
- Line ~25: `GET /api/incidents/summary`
- Line ~58: `GET /api/incidents/<incident_id>/tasks`
- Line ~86: `POST /api/incidents/<incident_id>/tasks`
- Line ~124: `GET /api/data-sources/metrics`
- Line ~183: `GET /api/threat-intelligence/feeds`
- Line ~211: `POST /api/threat-intelligence/feeds`
- Line ~240: `POST /api/threat-intelligence/feeds/<feed_id>/sync`
- Line ~269: `GET /api/access/jit-sessions`
- Line ~302: `POST /api/access/jit-sessions`
- Line ~334: `POST /api/access/jit-sessions/<session_id>/approve`
- Line ~362: `POST /api/access/jit-sessions/<session_id>/revoke`

**api_v1.py - REMOVE THESE:**
- Line ~532: `GET /api/incidents/<incident_id>` (keep only in api_v1_consolidated.py)

**api_v1_consolidated.py - REMOVE THESE:**
- Line ~286: `POST /api/alerts/<alert_id>/suppress` (keep only in api_v1_actions.py)
- Line ~177: `POST /api/incidents` (keep only in api_v1_actions.py)
- Line ~651: `POST /api/reports` (keep only in api_v1_reports.py)

**api_v1_actions.py - KEEP THESE (primary):**
- `POST /api/alerts/assign`
- `POST /api/alerts/<alert_id>/suppress` ← PRIMARY
- `PUT /api/alerts/<alert_id>/status`
- `POST /api/incidents` ← PRIMARY
- `PUT /api/incidents/<incident_id>/status`
- `POST /api/incidents/<incident_id>/assign`
- `POST /api/incidents/<incident_id>/link-alert`

**api_v1_reports.py - KEEP THIS (primary):**
- `POST /api/reports` ← PRIMARY

---

#### Phase 2: Implement Batch Endpoints (OPTIMIZATION)

Replace 3-5 separate calls with 1 consolidated endpoint:

##### 2A. Alert Operations Consolidation
```
NEW ENDPOINT: POST /api/alerts/batch-operations

Replace these 3 separate calls:
  ❌ POST /api/alerts/assign
  ❌ POST /api/alerts/<id>/suppress
  ❌ PUT  /api/alerts/<id>/status

With ONE call:
  ✅ POST /api/alerts/batch-operations
  {
    "operations": [
      { "type": "assign", "alert_ids": [...], "assignee_id": "..." },
      { "type": "suppress", "alert_ids": [...], "duration_minutes": 60 },
      { "type": "status", "alert_ids": [...], "status": "acknowledged" }
    ]
  }

BENEFIT: 66% fewer requests, 66% less connection pool load
```

##### 2B. Incident Operations Consolidation
```
NEW ENDPOINT: POST /api/incidents/<id>/batch-update

Replace these 3 separate calls:
  ❌ POST /api/incidents/<id>/tasks
  ❌ POST /api/incidents/<id>/link-alert
  ❌ PUT  /api/incidents/<id>/status

With ONE call:
  ✅ POST /api/incidents/<id>/batch-update
  {
    "updates": [
      { "type": "create-task", "title": "...", "assigned_to": "..." },
      { "type": "link-alert", "alert_id": "..." },
      { "type": "update-status", "status": "investigating" }
    ]
  }

BENEFIT: 66% fewer requests, 66% less connection pool load
```

##### 2C. JIT Access Consolidation
```
NEW ENDPOINT: POST /api/access/jit-sessions/batch-action

Replace these 2 separate calls:
  ❌ POST /api/access/jit-sessions/<id>/approve
  ❌ POST /api/access/jit-sessions/<id>/revoke

With ONE call:
  ✅ POST /api/access/jit-sessions/batch-action
  {
    "actions": [
      { "session_id": "...", "action": "approve" },
      { "session_id": "...", "action": "revoke" }
    ]
  }

BENEFIT: 50% fewer requests
```

##### 2D. Database Operations Consolidation
```
NEW ENDPOINT: POST /api/db/batch-operations

Replace these 5 separate calls:
  ❌ GET    /api/db/tables/<name>
  ❌ POST   /api/db/tables/<name>
  ❌ PUT    /api/db/tables/<name>
  ❌ DELETE /api/db/tables/<name>
  ❌ POST   /api/db/query

With ONE call:
  ✅ POST /api/db/batch-operations
  {
    "queries": [
      { "table": "users", "operation": "select", "filters": {...} },
      { "table": "events", "operation": "insert", "data": {...} },
      { "sql": "SELECT * FROM events WHERE..." }
    ]
  }

BENEFIT: 80% fewer requests, 80% less connection pool load
```

---

### 📐 ROUTING RULES (MUST FOLLOW)

#### Rule 1: Single Responsibility Per Blueprint
```
✅ ALLOWED:
  - api_v1_actions.py: Alert & Incident actions only
  - api_v1_extended.py: Extended features only
  - api_v1_consolidated.py: Consolidation endpoints only
  - api_v1.py: Read-only views only
  - api_v1_reports.py: Reports only
  - api_corporate.py: Corporate portal only
  - api_v1_db.py: Database operations only
  - api_ingestion.py: Log ingestion only

❌ NOT ALLOWED:
  - api_v1_extended.py + api_v1_consolidated.py doing same thing
  - api_v1_actions.py + api_v1_consolidated.py doing same thing
  - api_v1.py + api_v1_consolidated.py doing same thing
```

#### Rule 2: Primary File Ownership
```
Alert Management → api_v1_actions.py (PRIMARY)
Incident Management → api_v1_actions.py (PRIMARY)
Consolidation Operations → api_v1_consolidated.py (ONLY)
Extended Features → api_v1_extended.py (NEW FEATURES ONLY)
Reports → api_v1_reports.py (PRIMARY)
Database → api_v1_db.py (PRIMARY)
Ingestion → api_ingestion.py (PRIMARY)
```

#### Rule 3: No Endpoint Migration Without Deprecation
```
PROCESS:
  1. Add @deprecated() decorator to old endpoint
  2. Log a WARNING when endpoint is called
  3. Point client to new endpoint in response
  4. Keep for 2 versions
  5. Then remove

FORBIDDEN:
  ❌ Moving endpoint without warning
  ❌ Having same endpoint in 2 files
  ❌ Breaking client integrations silently
```

#### Rule 4: URL Prefix Consistency
```
✅ MUST USE:
  - /api/...           (All main endpoints)
  - /api/db/...        (Database operations)
  - /api/corporate/... (Corporate portal)

❌ NEVER USE:
  - /...               (Missing /api)
  - /tables/...        (Should be /api/db/tables/)
  - /devices/...       (Should be /api/devices/)
  - /query             (Should be /api/db/query)
```

#### Rule 5: Batch Operations Naming
```
✅ REQUIRED PATTERN:
  POST /api/<resource>/batch-operations
  POST /api/<resource>/<id>/batch-update
  POST /api/<resource>/batch-action

✅ PAYLOAD STRUCTURE:
  {
    "operations": [...]  // For POST .../batch-operations
    "updates": [...]     // For POST .../<id>/batch-update
    "actions": [...]     // For POST .../batch-action
  }
```

---

### 🔒 ENFORCEMENT RULES

#### MUST NOT HAPPEN:
```
1. ❌ Adding duplicate endpoints
   ✅ Check all api*.py files before adding new endpoint
   
2. ❌ Moving endpoints between files
   ✅ Keep endpoint in original file or properly deprecate
   
3. ❌ Creating similar endpoints with different paths
   ✅ Use consistent URL structure
   
4. ❌ Mixing concerns in one file
   ✅ Keep each file focused (single responsibility)
   
5. ❌ Ignoring connection pool exhaustion
   ✅ Use batch endpoints for related operations
   
6. ❌ Not updating documentation
   ✅ Document every endpoint before merging
```

#### MUST HAPPEN BEFORE MERGE:
```
1. ✅ Verify endpoint doesn't exist elsewhere
   Command: grep -r "@api.route('/<path>'" backend/app/api*.py
   
2. ✅ Check for similar patterns
   Command: grep -r "/api/<resource>/" backend/app/api*.py
   
3. ✅ Verify URL prefix is correct
   Must start with /api/ or /api/db/ or /api/corporate/
   
4. ✅ Add to api.md documentation
   Include: Method, Path, Purpose, Input, Output
   
5. ✅ Update this rules.md if new rules needed
   
6. ✅ Test against all existing endpoints
   Ensure no conflicts or duplicates
```

---

### 📊 LOAD OPTIMIZATION METRICS

#### Before Consolidation:
```
Connection Pool Load: 100% (3-5x per operation)
Response Time: 150-300ms (cumulative)
HTTP Requests: 3-5 per user action
Auth Checks: 3-5 per user action
Database Connections: 3-5 per user action
```

#### After Consolidation:
```
Connection Pool Load: 20-30% (1x per operation)
Response Time: 50-100ms (parallel processing)
HTTP Requests: 1 per user action (66-80% reduction)
Auth Checks: 1 per user action (66-80% reduction)
Database Connections: 1 per user action (66-80% reduction)
```

---

### 🚨 CRITICAL INCIDENTS TO PREVENT

#### Incident: Connection Pool Exhaustion
```
CAUSED BY: Too many simultaneous requests
SYMPTOM: API returns 503 or timeout
PREVENTION: 
  1. Use batch endpoints for related operations
  2. Monitor connection pool size
  3. Set connection limits in gunicorn
  4. Remove duplicate endpoints
  5. Implement request queuing
```

#### Incident: Duplicate Endpoint Conflicts
```
CAUSED BY: Same endpoint in multiple files
SYMPTOM: Unpredictable behavior, 404 errors
PREVENTION:
  1. Follow "Primary File Ownership" rule
  2. Check before adding new endpoints
  3. Remove all duplicates
  4. Test endpoint routing
```

#### Incident: API Breaking Changes
```
CAUSED BY: Moving/removing endpoints without notice
SYMPTOM: Client applications crash
PREVENTION:
  1. Use deprecation decorator
  2. Keep endpoints for 2 versions
  3. Log warnings
  4. Update documentation
  5. Notify clients
```

---

### ✅ CHECKLIST FOR NEW ENDPOINTS

Before adding ANY new endpoint, answer YES to all:

```
□ Does this endpoint already exist elsewhere?
  (Check all api*.py files)

□ Is the URL path consistent with existing endpoints?
  (Starts with /api/ or /api/db/ or /api/corporate/)

□ Is this endpoint in the correct primary file?
  (Check Primary File Ownership rule)

□ Could this operation be batched with similar ones?
  (Consider batch endpoints for 3+ related operations)

□ Is this documented in api.md?
  (Including Method, Path, Purpose, Input, Output)

□ Have all duplicates been removed?
  (Check api_v1_consolidated.py doesn't repeat it)

□ Is this endpoint tested?
  (Verify it works without breaking others)

□ Is the connection pool impact acceptable?
  (Single request, minimal database connections)
```

---

### 📅 IMMEDIATE ACTION ITEMS

#### This Week:
- [ ] Remove 9 duplicate endpoints (see table above)
- [ ] Update api_v1_extended.py (remove duplicates)
- [ ] Update api_v1.py (remove duplicate /incidents/<id>)
- [ ] Update api_v1_consolidated.py (remove duplicates)
- [ ] Test all endpoints work correctly

#### Next Week:
- [ ] Implement POST /api/alerts/batch-operations
- [ ] Implement POST /api/incidents/<id>/batch-update
- [ ] Implement POST /api/access/jit-sessions/batch-action
- [ ] Implement POST /api/db/batch-operations
- [ ] Update frontend to use batch endpoints

#### Before Production:
- [ ] Remove old individual endpoints (after batch endpoint testing)
- [ ] Update all documentation
- [ ] Performance test (measure connection pool load)
- [ ] Load test (verify 50% improvement)
- [ ] Update monitoring/alerting

---

### 📞 Violations Report

If you find a violation of these rules:

1. **Create an issue** with:
   - Which rule is violated
   - Which file/endpoint
   - Why it matters

2. **Examples of violations:**
   - "Rule 1: GET /api/incidents/<id> exists in BOTH api_v1.py and api_v1_consolidated.py"
   - "Rule 3: POST /api/alerts/assign missing /api prefix in test"
   - "Rule 4: New endpoint POST /tables doesn't follow naming convention"

---

### 🔗 Related Documents

- `doc/api.md` - Complete API documentation and catalog
- `rules.md` - Operational and architectural governance
