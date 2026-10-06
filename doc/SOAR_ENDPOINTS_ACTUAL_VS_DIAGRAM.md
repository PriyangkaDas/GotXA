## ✅ SOAR Endpoints - ACTUAL vs DIAGRAM

### Issue Found

The diagram shows endpoints **WITHOUT** the `/api` prefix, but they **DON'T WORK**.

### Endpoint Status

| Endpoint (From Diagram) | Status | Actual Endpoint | Status |
|---|---|---|---|
| `GET /v1/soar/actions` | ❌ 404 | `GET /api/v1/soar/actions` | ✅ 200 OK |
| `POST /v1/soar/execute` | ❌ 404 | `POST /api/v1/soar/execute` | ✅ 200 OK |
| `GET /v1/soar/history` | ❌ 404 | `GET /api/v1/soar/history` | ✅ 200 OK |
| `GET /v1/soar/executions` | ❌ 404 | `GET /api/v1/soar/executions` | ✅ 200 OK |
| `POST /playbooks/PB-ISOLATE/executions` | ❌ 404 | N/A - Not in backend | ❌ Doesn't exist |

---

## Working Endpoints (Correct Paths)

### 1. GET /api/v1/soar/actions
- **Status:** ✅ 200 OK
- **Returns:** 50 available SOAR actions (playbooks)
- **Response:** `{ "data": [...], "total": 50 }`

### 2. POST /api/v1/soar/execute
- **Status:** ✅ 200 OK
- **Input:** `{ "playbook_id": "...", "incident_id": "...", "inputs": {...} }`
- **Returns:** Execution confirmation

### 3. GET /api/v1/soar/history
- **Status:** ✅ 200 OK
- **Returns:** Past execution records (paginated)
- **Total Records:** 6,579 in database
- **Fields:** execution_id, playbook_id, status, outputs, timestamps

### 4. GET /api/v1/soar/executions
- **Status:** ✅ 200 OK
- **Returns:** Current/past execution records (same as history)
- **Total Records:** 6,579
- **Sample:** `EXEC-B6E6E408 - containment.block_ip (completed)`

### 5. POST /playbooks/PB-ISOLATE/executions
- **Status:** ❌ 404 NOT FOUND
- **Note:** This endpoint doesn't exist in backend
- **Alternative:** Use `/api/v1/soar/execute` instead

---

## Why the /api Prefix?

In `backend/app/api_v1_actions.py`:
```python
api = Blueprint('api_actions', __name__, url_prefix='/api')

@api.route('/v1/soar/actions', methods=['GET'])  # Route definition
def get_soar_actions():
    ...
```

The blueprint has `url_prefix='/api'`, so:
- Route defined as: `/v1/soar/actions`
- Actual endpoint: `/api/v1/soar/actions`

---

## Frontend Fix Required

The frontend (SoarEngineWorkspace.jsx or equivalent) must use:

```javascript
// ❌ WRONG - These return 404
const actions = await fetch('/v1/soar/actions');
const executions = await fetch('/v1/soar/executions');
const history = await fetch('/v1/soar/history');

// ✅ CORRECT - These work
const actions = await fetch('/api/v1/soar/actions');
const executions = await fetch('/api/v1/soar/executions');
const history = await fetch('/api/v1/soar/history');
```

---

## API Configuration Check

### Backend Routes (CONFIRMED)
```
File: backend/app/api_v1_actions.py

@api.route('/v1/soar/actions', methods=['GET'])      ✓ Line 356
@api.route('/v1/soar/execute', methods=['POST'])     ✓ Line 558
@api.route('/v1/soar/history', methods=['GET'])      ✓ Line 645
@api.route('/v1/soar/executions', methods=['GET'])   ✓ Line 646

Blueprint: url_prefix='/api'                         ✓ Line 21
```

### Actual Working URLs
```
http://localhost:5000/api/v1/soar/actions       ✓ 200 OK
http://localhost:5000/api/v1/soar/execute       ✓ 200 OK
http://localhost:5000/api/v1/soar/history       ✓ 200 OK
http://localhost:5000/api/v1/soar/executions    ✓ 200 OK
```

---

## Response Structure

### GET /api/v1/soar/actions
```json
{
  "data": [
    {
      "id": "action-1",
      "name": "block_ip",
      "description": "Block Malicious IP"
    },
    ...
  ],
  "total": 50
}
```

### GET /api/v1/soar/executions
```json
{
  "items": [
    {
      "execution_id": "EXEC-B6E6E408",
      "playbook_id": "containment.block_ip",
      "status": "completed",
      "mode": "automated",
      "inputs": {...},
      "outputs": {...},
      "triggered_by": "admin",
      "created_at": "timestamp",
      "started_at": "timestamp",
      "completed_at": "timestamp"
    }
  ],
  "total": 6579,
  "page": 1,
  "page_size": 25
}
```

---

## Summary

| Item | Status |
|---|---|
| Diagram endpoints (no /api prefix) | ❌ DON'T WORK - 404 errors |
| Correct endpoints (with /api prefix) | ✅ WORKING - 200 OK |
| GET /api/v1/soar/actions | ✅ Working (50 actions) |
| POST /api/v1/soar/execute | ✅ Working |
| GET /api/v1/soar/history | ✅ Working (6579 records) |
| GET /api/v1/soar/executions | ✅ Working (6579 records) |
| POST /playbooks/PB-ISOLATE/... | ❌ Doesn't exist |

**Action Required:** Update frontend to use `/api/v1/soar/...` paths instead of `/v1/soar/...`
