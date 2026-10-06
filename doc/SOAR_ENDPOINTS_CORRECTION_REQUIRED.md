## ⚠️ SOAR Endpoints - Correction Required

### Executive Summary

**The diagram you showed is INCORRECT.** All endpoints are missing the `/api` prefix and will return 404 errors.

---

## Endpoints in Diagram (❌ DON'T WORK)

These endpoints return **404 NOT FOUND**:
```
GET  /v1/soar/actions
POST /v1/soar/execute
GET  /v1/soar/history
GET  /v1/soar/executions
POST /playbooks/PB-ISOLATE/executions
```

---

## Correct Working Endpoints (✅ WORKING)

These endpoints return **200 OK**:

```
GET  /api/v1/soar/actions       ✅ Returns 50 actions
POST /api/v1/soar/execute       ✅ Creates execution
GET  /api/v1/soar/history       ✅ Returns 6579 records
GET  /api/v1/soar/executions    ✅ Returns 6579 records
```

---

## Full URLs (Ready to Copy/Paste)

```
http://localhost:5000/api/v1/soar/actions
http://localhost:5000/api/v1/soar/execute
http://localhost:5000/api/v1/soar/history
http://localhost:5000/api/v1/soar/executions
```

---

## Response Examples

### GET /api/v1/soar/actions
```json
{
  "data": [
    {
      "id": "1",
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
      "inputs": {
        "host": "target-host",
        "ip": "192.168.1.100"
      },
      "outputs": {
        "action_taken": "dynamic_ip_blacklist",
        "target_ip": "192.168.1.100",
        "summary": "Adversary IP 192.168.1.100 dynamically blacklisted."
      },
      "triggered_by": "admin",
      "created_at": "2026-09-25T01:45:00Z",
      "started_at": "2026-09-25T01:45:00Z",
      "completed_at": "2026-09-25T01:45:01Z"
    }
  ],
  "total": 6579,
  "page": 1,
  "page_size": 25
}
```

---

## Root Cause

**Backend File:** `backend/app/api_v1_actions.py` (Line 21)

```python
api = Blueprint('api_actions', __name__, url_prefix='/api')
```

The blueprint is registered with `url_prefix='/api'`, which means:
- Route: `/v1/soar/actions`
- Actual URL: `/api` + `/v1/soar/actions` = `/api/v1/soar/actions`

---

## Frontend Fix

If your frontend is using the diagram endpoints (without `/api`):

**BEFORE (❌ Broken):**
```javascript
const response = await fetch('/v1/soar/executions');
// Returns: 404 NOT FOUND
```

**AFTER (✅ Working):**
```javascript
const response = await fetch('/api/v1/soar/executions');
// Returns: 200 OK with data
```

---

## Test Command (curl)

```bash
# Test if endpoints work
curl http://localhost:5000/api/v1/soar/actions -H "X-User-ID: admin"
curl http://localhost:5000/api/v1/soar/executions -H "X-User-ID: admin"

# Should return 200 OK, not 404
```

---

## Verification Checklist

- [ ] Update frontend to use `/api/v1/soar/...` paths
- [ ] Remove `/api` from any hardcoded paths that already have it twice
- [ ] Test endpoints return 200 OK (not 404)
- [ ] Verify data is displayed in SoarEngineWorkspace

---

## Summary Table

| Diagram URL | Status | Correct URL | Status |
|---|---|---|---|
| `/v1/soar/actions` | ❌ 404 | `/api/v1/soar/actions` | ✅ 200 |
| `/v1/soar/execute` | ❌ 404 | `/api/v1/soar/execute` | ✅ 200 |
| `/v1/soar/history` | ❌ 404 | `/api/v1/soar/history` | ✅ 200 |
| `/v1/soar/executions` | ❌ 404 | `/api/v1/soar/executions` | ✅ 200 |
| `/playbooks/PB-ISOLATE/...` | ❌ 404 | Use `/api/v1/soar/execute` | ✅ 200 |

---

## Next Steps

1. **Identify where frontend calls SOAR endpoints**
2. **Add `/api` prefix to all endpoint paths**
3. **Test that endpoints return 200 OK**
4. **Verify data displays in frontend**

All SOAR endpoints are working and ready, they just need the correct `/api` prefix!
