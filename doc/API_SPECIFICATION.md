# GotXA — Complete REST API Specification

This document provides the complete, authoritative specification for all REST API endpoints exposed across the GotXA Security Operations, SCADA Gateway, and IT/OT Monitoring Platform.

---

## 1. Global Platform Configurations & Authentication

### Base URLs
*   **Unified API Gateway**: `http://localhost/api` (or `http://<host>:80/api`)
*   **Backend Direct**: `http://localhost:5000/api`
*   **SCADA Gateway**: `http://localhost:5002/api`
*   **Log Collector Stream**: `http://localhost:5006/api`

### Authentication Mechanisms
1. **JWT Bearer Token (Production)**:
   ```http
   Authorization: Bearer <JWT_TOKEN>
   ```
2. **Role/User Identity Header (Platform Internal & Testing)**:
   ```http
   X-User-ID: admin
   X-Operator: analyst-1
   ```
3. **Collector & Telemetry Ingestion Token**:
   ```http
   X-Collector-Token: <COLLECTOR_INGEST_TOKEN>
   ```

---

## 2. Standard Response Schemas

### 2.1 Standard Success Envelope
```json
{
  "data": { ... },
  "message": "Success",
  "timestamp": "2026-09-01T01:30:00.000000"
}
```

### 2.2 Paginated List Envelope
```json
{
  "items": [ ... ],
  "total": 120,
  "page": 1,
  "page_size": 25,
  "pages": 5
}
```

### 2.3 Standard Error Envelope
```json
{
  "error": {
    "code": "BadRequest",
    "message": "Detailed error explanation",
    "details": { ... }
  }
}
```

---

## 3. Telemetry & Parallel Event Ingestion

### `POST /api/ingest/events`
High-throughput, asynchronous batch ingestion endpoint for SIEM collectors, agents, and gateways. Automatically performs dynamic asset discovery and classification.

*   **Auth**: Requires `X-Collector-Token`
*   **Request Body**:
    ```json
    {
      "events": [
        {
          "timestamp": "2026-09-01T01:00:00Z",
          "level": "INFO",
          "source": "ot-scada-gateway",
          "host": "ot-plc-refinery-1",
          "message": "PROCESS_TELEMETRY: Operational state: temperature = 185.2",
          "event_type": "PROCESS_TELEMETRY",
          "device": {
            "hostname": "ot-plc-refinery-1",
            "device_type": "plc",
            "ip_address": "172.26.0.10",
            "metadata": { "metric": "temperature", "value": 185.2 }
          }
        }
      ]
    }
    ```
*   **Response (202 Accepted)**:
    ```json
    {
      "queued": 1,
      "task_id": "8f3b2a1c-..."
    }
    ```

---

## 4. Device Inventory & Asset Discovery

### `GET /api/devices`
Retrieves all dynamically discovered and cataloged IT/OT devices.

*   **Auth**: Required
*   **Response (200 OK)**:
    ```json
    {
      "items": [
        {
          "id": "c1a2b3...",
          "hostname": "ot-plc-refinery-1",
          "device_type": "plc",
          "trust_state": "untrusted",
          "first_seen_at": "2026-09-01T00:15:00",
          "last_seen_at": "2026-09-01T01:30:00",
          "ip_address": "172.26.0.10"
        }
      ]
    }
    ```

### `PATCH /api/devices/{device_id}/trust`
Updates trust status (`trusted`, `untrusted`, `blocked`).

*   **Auth**: Required (Permission: `settings.write`)
*   **Request Body**:
    ```json
    {
      "trust_state": "trusted"
    }
    ```

---

## 5. SCADA Gateway & Industrial Controls

### `GET /api/modbus`
Returns live Modbus register states across all registered machines.

*   **Response (200 OK)**:
    ```json
    {
      "refinery_1": {
        "temperature": 185.2,
        "pressure": 52.1,
        "status": "online",
        "last_update": "2026-09-01T01:30:00"
      },
      "refinery_2": {
        "flow_rate": 54.8,
        "status": "online",
        "last_update": "2026-09-01T01:30:00"
      }
    }
    ```

### `GET /api/scada/machines`
Lists all machines, live status, configured register schemas, and allowed controls.

### `POST /api/scada/machines/register`
Dynamically registers a new PLC/machine at runtime and automatically initializes Modbus polling.

*   **Request Body**:
    ```json
    {
      "id": "refinery-3",
      "name": "Refinery 3 Distillation Unit",
      "host": "ot-plc-refinery-3",
      "port": 5005,
      "slave_id": 1,
      "poll_interval": 2,
      "registers": {
        "column_pressure": { "addr": 0, "qty": 1, "scale": 0.1, "unit": "bar", "threshold_high": 100 }
      },
      "controls": [
        { "command": "emergency_stop", "label": "Emergency Stop", "type": "action" }
      ]
    }
    ```

### `POST /api/scada/machines/{machine_id}/commands`
Validates, executes, audits, and forwards SCADA actuator commands.

*   **Request Body**:
    ```json
    {
      "command": "set_temperature",
      "value": 190.0,
      "reason": "Process optimization"
    }
    ```

### `GET /api/scada/alarms`
Lists active and historical threshold alarms.

### `POST /api/scada/alarms/{alarm_id}/acknowledge`
Acknowledges an active alarm with operator notes.

---

## 6. SIEM Security Operations & Log Streaming

### `GET /api/overview`
Retrieves SOC KPI metrics, critical alert counts, active incidents, and source health.

### `GET /api/raw-stream`
Cursor-based pagination of live security events and telemetry.

*   **Query Parameters**: `limit` (default: 50, max: 250), `cursor` (UUID pointer)

### `GET /api/alerts`
Lists security alerts with filtering by `severity`, `status`, `assignee`, `page`, `page_size`.

### `POST /api/alerts/{id}/suppress`
Suppresses matching future alert rules.

---

## 7. Incident Management & SOAR Workflows

### `POST /api/incidents`
Creates an incident ticket.

*   **Request Body**:
    ```json
    {
      "title": "SQL Injection on Corporate Portal",
      "severity": "high",
      "priority": "high",
      "description": "Attacker attempted authentication bypass using UNION SELECT."
    }
    ```

### `PATCH /api/incidents/{id}`
Updates incident state (`open` → `investigating` → `contained` → `resolved` → `closed`).

### `POST /api/playbooks/{playbook_id}/executions`
Triggers an automated SOAR playbook.

*   **Request Body**:
    ```json
    {
      "target": "172.26.0.15",
      "dry_run": false,
      "reason": "Host quarantine due to RCE detection"
    }
    ```

### `POST /api/playbook-executions/{execution_id}/approve`
Approves high-risk containment execution.

---

## 8. Reports & Background Processing

### `POST /api/reports`
Queues asynchronous PDF report generation via Celery.

*   **Request Body**:
    ```json
    {
      "type": "executive",
      "title": "Monthly SOC Operations & OT Security Summary"
    }
    ```

### `GET /api/reports/{id}/download`
Downloads the compiled PDF artifact.

---

## 9. Database & Operational Health

### `GET /health`
Returns database connection status and server health.

### `GET /api/status`
Returns API service version and timestamp.

### `GET /api/db/tables`
Lists database tables and row counts.
