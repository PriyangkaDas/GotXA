# GotXA IST (Indian Standard Time) Configuration

## Overview
All GotXA servers are configured to use **IST (Indian Standard Time)** as the standard timezone.

**IST Details:**
- Timezone: Asia/Kolkata
- UTC Offset: +05:30
- Daylight Saving: None (IST is year-round)
- SIEM_TZ_OFFSET_MINUTES: 330 minutes = 5.5 hours ahead of UTC

---

## System-Wide Configuration

### 1. Docker Compose Configuration

All services in `docker-compose.yml` use IST:

```yaml
environment:
  - TZ=Asia/Kolkata
  - SIEM_TZ_OFFSET_MINUTES=330
```

**Services configured with IST:**
- ✅ Backend API (`siem-postgres`)
- ✅ PostgreSQL Database
- ✅ Redis Cache
- ✅ Celery Worker
- ✅ API Gateway
- ✅ All Frontend Services (SIEM, Corp Portal, SCADA)
- ✅ Log Collector
- ✅ SCADA Gateway

### 2. Environment Variables (.env)

```
TZ=Asia/Kolkata
SIEM_TZ_OFFSET_MINUTES=330
```

### 3. Backend Application Configuration

**File:** `backend/main.py`

```python
os.environ.setdefault('TZ', 'Asia/Kolkata')
os.environ.setdefault('SIEM_TZ_OFFSET_MINUTES', '330')
```

---

## Time Display Formats

### Timestamp Formats Used

All API responses use IST with three timestamp formats:

1. **Standard Format** (Database/ISO)
   ```
   2026-09-09 21:22:00
   ```

2. **Human Readable Format**
   ```
   Sep 09, 2026, 09:22:00 PM
   ```

3. **Time Display Only**
   ```
   09:22:00 PM
   ```

### Example API Response

```json
{
  "data": {
    "id": "alert-123",
    "title": "Security Alert",
    "timestamp": "2026-09-09 21:22:00",
    "formatted_time": "Sep 09, 2026, 09:22:00 PM",
    "time_display": "09:22:00 PM",
    "created_at": "2026-09-09 21:22:00"
  }
}
```

---

## API Timezone Support

### 1. Timezone Override Header

Clients can override the server timezone using:

```
X-Timezone-Offset: <minutes>
```

Example: For UTC, send `X-Timezone-Offset: 0`

### 2. Timezone Detection in API

**File:** `backend/app/api_v1.py`

```python
def _get_tz_offset():
    """Determine timezone offset in minutes. Defaults to +330 (IST)."""
    if has_request_context():
        try:
            header_val = request.headers.get('X-Timezone-Offset')
            if header_val is not None:
                return -int(header_val)
        except Exception:
            pass
    try:
        return int(os.getenv('SIEM_TZ_OFFSET_MINUTES', '330'))
    except Exception:
        return 330
```

### 3. Timezone Conversion

All timestamps are converted to IST (or client-specified timezone) in responses:

```python
def _to_local(dt):
    """Convert UTC datetime to local timezone."""
    offset_mins = _get_tz_offset()
    if dt.tzinfo is not None:
        return dt.astimezone(timezone(timedelta(minutes=offset_mins)))
    return dt + timedelta(minutes=offset_mins)
```

---

## Database Timezone

### PostgreSQL Configuration

**File:** `docker-compose.yml`

```yaml
siem-postgres:
  environment:
    POSTGRES_TIMEZONE: 'Asia/Kolkata'
  command:
    - "-c"
    - "timezone='Asia/Kolkata'"
```

### Timestamp Storage

All timestamps stored in PostgreSQL are in **UTC** (for consistency), but displayed in **IST** when retrieved via API.

Example:
- **Stored in DB:** 2026-09-09 15:52:00 UTC
- **Displayed in API:** 2026-09-09 21:22:00 IST (UTC +5:30)

---

## Application-Level Configuration

### Backend Settings

**File:** `backend/main.py`

```python
import os
from datetime import timezone, timedelta

# Set IST as system timezone
os.environ['TZ'] = 'Asia/Kolkata'
os.environ['SIEM_TZ_OFFSET_MINUTES'] = '330'

# Timezone object for IST
IST = timezone(timedelta(hours=5, minutes=30))
```

### SIEM Log Ingestion

All log timestamps are normalized to IST:

```python
# Example from SystemTelemetryDaemon
event_time = datetime.now(tz=IST)  # Current time in IST
alert_timestamp = event_time.strftime('%Y-%m-%d %H:%M:%S')
```

---

## Frontend Timezone Display

### Web Dashboard

All frontend dashboards (SIEM, Corporate Portal, SCADA) display times in **IST**:

```javascript
// React component timestamp formatting
const formatTimeIST = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

// Example output: "09 Sep 2026, 21:22:00"
```

---

## Audit & Logging

### Audit Event Timestamps

All audit events use IST timestamps:

```json
{
  "audit_event": {
    "id": "audit-001",
    "action": "alert_acknowledged",
    "timestamp": "2026-09-09 21:22:00",
    "timezone": "IST (Asia/Kolkata)",
    "offset": "+05:30"
  }
}
```

### Log File Timestamps

SystemTelemetryDaemon and all loggers use IST:

```
[2026-09-09 21:22:00 +0530] INFO - SystemTelemetryDaemon started
[2026-09-09 21:22:05 +0530] ALERT - CRITICAL alert detected
```

---

## Report Generation

### PDF Report Timestamps

All generated reports (compliance, incident) include IST timestamps:

```
Report Generated: September 09, 2026 at 09:22 PM (IST)
Time Period: Sep 01, 2026 - Sep 09, 2026 (IST)
```

### Report Metadata

```json
{
  "report": {
    "id": "rpt-001",
    "title": "Monthly Incident Report",
    "generated_at": "2026-09-09 21:22:00",
    "timezone": "IST",
    "period_start": "2026-09-01 00:00:00",
    "period_end": "2026-09-30 23:59:59"
  }
}
```

---

## Celery Background Tasks

### Task Timestamps

Celery tasks use IST for scheduling and execution tracking:

```python
from celery import Celery
from datetime import datetime, timezone, timedelta

app = Celery('gotxa')

# Configure IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

@app.task
def generate_report():
    """Generate report with IST timestamp."""
    task_time = datetime.now(tz=IST)
    print(f"Report generation started at {task_time}")
```

---

## SCADA/OT Event Timestamps

### Industrial Control Events

All OT/SCADA events include IST timestamps:

```json
{
  "event": {
    "type": "PLC_PARAMETER_OVERRIDE",
    "timestamp": "2026-09-09 21:22:00",
    "timezone": "IST",
    "machine_id": "refinery-1",
    "parameter": "temperature_setpoint",
    "new_value": 120,
    "previous_value": 75
  }
}
```

---

## API Examples with IST

### Example 1: Get Alert with IST Timestamp

```bash
curl -H "X-User-ID: admin" \
  http://localhost:5000/api/alerts/alert-123
```

Response:
```json
{
  "data": {
    "id": "alert-123",
    "title": "Critical Security Event",
    "timestamp": "2026-09-09 21:22:00",
    "formatted_time": "Sep 09, 2026, 09:22:00 PM",
    "time_display": "09:22:00 PM",
    "detected_at": "2026-09-09 21:22:00"
  }
}
```

### Example 2: List Incidents with IST

```bash
curl -H "X-User-ID: admin" \
  http://localhost:5000/api/incidents?page=1
```

Response:
```json
{
  "data": [
    {
      "id": "inc-001",
      "title": "Potential Breach",
      "created_at": "2026-09-09 21:15:00",
      "detected_at": "2026-09-09 21:10:00"
    }
  ]
}
```

### Example 3: Create Incident with IST Logging

```bash
curl -X POST -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{"title":"New Incident","severity":"high"}' \
  http://localhost:5000/api/incidents
```

Audit log entry (IST):
```
[2026-09-09 21:22:00 +0530] AUDIT - User: admin | Action: create_incident | Resource: inc-002
```

---

## Timezone Verification

### Check System Timezone

```bash
# Inside container
docker exec backend date

# Output: Mon Sep  9 21:22:00 IST 2026
```

### Check PostgreSQL Timezone

```bash
# Query database
docker exec Database psql -U siem_user -d siem_db \
  -c "SELECT NOW() AT TIME ZONE 'Asia/Kolkata' as current_ist;"

# Output: 2026-09-09 21:22:00+05:30
```

### Check API Timezone

```bash
curl -H "X-User-ID: admin" \
  http://localhost:5000/api/overview/metrics | jq '.timestamp'

# Output: "2026-09-09 21:22:00"
```

---

## Configuration Summary

| Component | Timezone | Offset | Status |
|-----------|----------|--------|--------|
| Docker Compose | Asia/Kolkata | UTC+5:30 | ✅ Configured |
| Backend API | Asia/Kolkata | UTC+5:30 | ✅ Configured |
| PostgreSQL | Asia/Kolkata | UTC+5:30 | ✅ Configured |
| Redis | Asia/Kolkata | UTC+5:30 | ✅ Configured |
| Celery Worker | Asia/Kolkata | UTC+5:30 | ✅ Configured |
| Frontend (React) | Asia/Kolkata | UTC+5:30 | ✅ Configured |
| API Gateway | Asia/Kolkata | UTC+5:30 | ✅ Configured |
| Log Collector | Asia/Kolkata | UTC+5:30 | ✅ Configured |
| SCADA Gateway | Asia/Kolkata | UTC+5:30 | ✅ Configured |

---

## Troubleshooting

### Timestamp Mismatch

If you see timestamps that don't match IST:

1. **Check environment variable:**
   ```bash
   docker exec backend printenv TZ
   # Should output: Asia/Kolkata
   ```

2. **Check offset value:**
   ```bash
   docker exec backend printenv SIEM_TZ_OFFSET_MINUTES
   # Should output: 330
   ```

3. **Restart containers:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Client Timezone Override

To display times in a different timezone from client-side:

```bash
# Request with UTC timezone
curl -H "X-User-ID: admin" \
  -H "X-Timezone-Offset: 0" \
  http://localhost:5000/api/alerts
```

---

## Best Practices

1. **Always store UTC in database** - Store times in UTC, convert to IST on display
2. **Use IST for audit logs** - All security/compliance logs in IST
3. **Consistent format** - Use `YYYY-MM-DD HH:MM:SS` format throughout
4. **Document timezones** - Include timezone in reports and exports
5. **Handle DST carefully** - IST has no daylight saving, so no conversion needed

---

## References

- **IANA Timezone:** Asia/Kolkata
- **Timezone Database:** IANA TZDATA
- **UTC Offset:** +05:30 (fixed, no DST)
- **City:** Kolkata (Calcutta), India
- **Region:** All of India

---

**Last Updated:** September 9, 2026  
**Standard:** IST (Asia/Kolkata) - UTC+05:30  
**Status:** ✅ All servers configured for IST
