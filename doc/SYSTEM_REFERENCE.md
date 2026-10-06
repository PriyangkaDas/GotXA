# GOTXA System Reference

This document describes the current source tree and the API surface loaded by the production backend. It reflects the Compose deployment in `docker-compose.yml`.

## Runtime architecture

| Component | Source / image definition | Responsibility | Port |
|---|---|---|---:|
| API gateway | `webservers/api-gateway/nginx.conf` | Routes browser traffic to frontend services and `/api/` to the backend. | 80 |
| Backend | `backend/main.py`, `backend/wsgi.py`, `backend/Dockerfile` | Flask REST API, PostgreSQL persistence, API health check. | 5000 |
| Celery worker | `backend/celery_worker.py`, `backend/Dockerfile.celery` | Executes report-generation tasks from Redis. | internal |
| PostgreSQL | `docker-compose.yml` | Persistent relational database. | 5432 |
| Redis | `docker-compose.yml` | Celery broker and result backend. | internal 6379 |
| SIEM frontend | `webservers/siem-soar-frontend/` | Serves the SIEM/SOAR UI. | internal 80 |
| Corporate frontend | `webservers/corp-portal-frontend/` | Serves the corporate UI. | internal 80 |
| SCADA frontend | `webservers/scada-frontend/` | Serves the SCADA UI. | internal 80 |
| Real-log collector (optional) | `log_collector.py`, `Dockerfile.collector` | Tails mounted real log files and sends authenticated batches to the backend. Enable with the `production-logging` profile. | internal 5006 |

`443` is currently mapped by Compose but not configured with an Nginx TLS listener or certificate. Do not use it until TLS configuration is added.

## Deployment and configuration files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Defines the runtime services, networks, persistent volumes, health checks, and optional collector profile. |
| `.env.example` | Example deployment settings. Set a high-entropy `COLLECTOR_INGEST_TOKEN` in an uncommitted `.env` file before enabling the collector. |
| `backend/requirements.txt` | Backend, Celery, SQLAlchemy, and report dependencies. |
| `backend/Dockerfile` | Backend image and Python health check. |
| `backend/Dockerfile.celery` | Worker image. Starts `celery_worker.celery`, not the task module. |
| `Dockerfile.collector` | Collector image; exposes 5006 only. |
| `webservers/*/Dockerfile` | Images for the three frontend Nginx services and gateway. |
| `webservers/*/nginx.conf` | Frontend routing and backend API proxy rules. |
| `frontend/vite.config.js` | Local development server configuration (5173) and proxy target. |

## Backend files and functions

| File | Main functions / responsibility |
|---|---|
| `backend/main.py` | `create_app()` configures Flask, database, Celery context, error handlers, and registers every API blueprint. |
| `backend/wsgi.py` | Gunicorn entry point; creates `app`. |
| `backend/app/models.py` | SQLAlchemy models: users, teams, alerts, incidents, tasks, evidence, reports, log sources, threat feeds, JIT sessions, devices, and immutable security events. |
| `backend/app/auth.py` | `authenticate`, `require_permission`, access checks, and consistent success/error response helpers. Production deployments must replace legacy header authentication with OIDC/SAML/JWT validation. |
| `backend/app/audit.py` | Records auditable security and configuration operations. |
| `backend/app/api_v1.py` | Core dashboard, alert, incident-list, capability, audit-event, and raw-stream read APIs. |
| `backend/app/api_v1_actions.py` | Alert and incident mutation APIs: assignments, suppression, lifecycle changes, and links. |
| `backend/app/api_v1_extended.py` | Task, log-source, threat-feed, JIT-access, and settings APIs. Superseded duplicate route registrations were removed. |
| `backend/app/api_v1_consolidated.py` | Current consolidated dashboard and incident endpoints; report requests, SCADA proxy endpoints, and legacy endpoint compatibility. Local demo login now returns `410 Gone`. |
| `backend/app/api_v1_reports.py` | Report lookup, download, and status APIs. |
| `backend/app/api_v1_db.py` | Administrative database-table inspection and controlled query APIs. |
| `backend/app/api_corporate.py` | Corporate portal authentication/session and dashboard APIs. |
| `backend/app/api_ingestion.py` | Authenticated real-event ingestion, automatic device inventory, device classification, and trust-state APIs. |
| `backend/app/celery_app.py` | `make_celery()` creates a Celery instance bound to the Flask application context. |
| `backend/app/tasks.py` | Asynchronous report-generation task definitions. |
| `backend/app/pdf_generator.py` | Creates report PDFs. |
| `backend/celery_worker.py` | Exports `celery`; used by the worker command. |

## Data tables

| Table / model | Purpose | Important fields |
|---|---|---|
| `users`, `teams` | User identity and team membership. | role, is_active, team_id |
| `alerts`, `incidents`, `tasks`, `evidence` | SIEM case-management workflow. | severity, status, owner, timestamps |
| `audit_events` | Immutable operational audit trail. | actor, action, resource, correlation ID |
| `reports` | Queued and completed reports. | status, type, file path, requested by |
| `log_sources` | Health/metrics of configured sources. | ingestion rate, parse errors, last event |
| `threat_intelligence_feeds`, `jit_sessions`, `system_metrics` | Threat-feed, privileged-access, and KPI state. | status and timestamps |
| `devices` | Observed device inventory. | hostname, IP, MAC, device type, manufacturer, model, OS, serial number, trust state, first/last seen |
| `security_events` | Immutable events received from approved collectors. | device, source, severity, occurred/received timestamps, raw event |

New devices are always created as **`untrusted`**. An authorized administrator may change the state to `trusted` or `blocked`. Device type is taken from event metadata when supplied; otherwise the system conservatively infers PLC, SCADA, database server, web server, workstation, or `unknown` from the hostname.

## Real-log ingestion

`log_collector.py` polls these mounted paths for real `app.log` files:

- `/logs/corp-portal`
- `/logs/corp-database`
- `/logs/corp-workstation`
- `/logs/ot-scada`
- `/logs/ot-plc-1`
- `/logs/ot-plc-2`

It sends batches to `http://backend:5000/api/ingest/events` with `X-Collector-Token`. Every event must include a real ISO-8601 `timestamp` and non-empty `message`; optional `device` metadata accepts `hostname`, `ip_address`, `mac_address`, `device_type`, `manufacturer`, `model`, `os_version`, `serial_number`, and `metadata`.

Synthetic generators `agent.py` and `log_generator.sh` were removed. The collector does not fabricate events.

## API reference

### Public and operational endpoints

| Method | Path | Function |
|---|---|---|
| GET | `/health` | Backend and database health. |
| GET | `/api/status` | API version and liveness. |
| POST | `/api/ingest/events` | Ingest up to 500 real events; requires collector token. |
| POST | `/api/login` | Disabled legacy local login; returns `410`. |
| GET | `/api/modbus`, `/api/modbus/refinery-1`, `/api/modbus/refinery-2` | Proxy live SCADA gateway telemetry; returns `503` if the real gateway is unavailable. |

### SIEM/SOAR APIs

| Method | Paths | Function |
|---|---|---|
| GET | `/api/overview`, `/api/overview/metrics`, `/api/dashboard-data`, `/api/dashboard-metrics`, `/api/recent-activity`, `/api/raw-stream` | Dashboard metrics, activity, and raw event stream. |
| GET | `/api/alerts`, `/api/alerts/{alert_id}` | Alert list and detail. |
| PUT / POST | `/api/alerts/{alert_id}/status`, `/api/alerts/{alert_id}/suppress`, `/api/alerts/bulk-assign` | Alert status, suppression, and assignment. |
| GET / POST | `/api/incidents`, `/api/incidents/{incident_id}`, `/api/incidents/summary` | Incident list, detail, creation, and summary. |
| PUT / POST | `/api/incidents/{incident_id}/status`, `/assign`, `/link-alert`, `/tasks` | Incident lifecycle, assignment, alert link, and task operations. |
| GET | `/api/capabilities`, `/api/audit-events`, `/api/assets/export` | Permissions, audit events, and asset export. |
| POST / GET | `/api/v1/soar/execute`, `/api/v1/soar/actions`, `/api/v1/soar/history`, `/api/playbooks/{playbook_id}/executions`, `/api/containment-requests` | SOAR execution and containment workflows. |
| GET / POST | `/api/reports`, `/api/reports/{report_id}`, `/api/reports/{report_id}/status`, `/api/reports/{report_id}/download` | Report request, lookup, status, and download. |

### Device, source, and administration APIs

| Method | Paths | Function |
|---|---|---|
| GET / PATCH | `/api/devices`, `/api/devices/{device_id}/trust` | Device inventory and trust-state administration. |
| GET / POST | `/api/data-sources/metrics`, `/api/data-sources` | Source metrics and source registration. |
| GET / POST | `/api/threat-intelligence/feeds`, `/api/threat-intelligence/feeds/{feed_id}/sync` | Feed inventory and synchronization. |
| GET / POST | `/api/access/jit-sessions`, `/api/access/jit-sessions/{session_id}/approve`, `/revoke`, `/api/access/review` | Just-in-time access request, approval, revocation, and review. |
| GET / PUT / PATCH | `/api/settings`, `/api/settings/{section}`, `/api/settings/history` | Settings, updates, and change history. |
| GET / POST / PUT / DELETE | `/api/db/tables`, `/api/db/tables/{table_name}`, `/api/db/query` | Restricted database administration. |
| POST / GET | `/api/detection-rules/{rule_id}/test`, `/api/detection-rules/{rule_id}/versions` | Detection-rule test and version lookup. |

### Corporate portal APIs

| Method | Path | Function |
|---|---|---|
| POST | `/api/corporate/auth/login`, `/api/corporate/auth/logout` | Corporate session authentication. |
| GET | `/api/corporate/me`, `/dashboard`, `/systems`, `/tasks`, `/announcements`, `/activity`, `/admin/overview` | Corporate user and dashboard data. |
| PATCH | `/api/corporate/tasks/{task_id}` | Update a corporate task. |

## Supporting and legacy source files

| File/group | Status and purpose |
|---|---|
| `scada_gateway.py`, `modbus_plc_server.py`, `Dockerfile.scada`, `Dockerfile.agent` | Standalone SCADA/PLC integration code. It is not part of the current production Compose profile; connect it only to real PLC endpoints. |
| `vulnerable_app.py`, `Dockerfile.vulnerable`, `pentesting_scripts/` | Deliberately vulnerable training/lab material; do not deploy in production. |
| `app/`, `siem_server.py`, `nginx.conf`, `Dockerfile.siem`, `Dockerfile.frontend` | Earlier standalone SIEM implementation retained for reference; not loaded by the Compose backend. |
| `filebeat.yml`, `logstash.conf` | LEGACY/unused historical references; current pipeline is `log_collector.py` -> `POST /api/ingest/events`. |
| `doc/` | Comprehensive platform documentation: `API_SPECIFICATION.md`, `ARCHITECTURE.md`, `CODE_SNIPPETS.md`, `IMPORTANT_FACTS.md`, `TESTING_AND_INTEGRATION.md`, `vision_corp.md`, `vision_scada.md`, `SYSTEM_REFERENCE.md`. |
| `Additional Doc/` | SaaS commercialization and transition resources: `GotXA_SaaS_Strategy.md`, `GotXA_SaaS_Pricing_Guide.md`, `GotXA_SaaS_Technical_Implementation.md`. |
| `frontend/` | React/Vite development source for dashboards and corporate/SCADA pages. |
| `test_endpoints.sh`, `test_soar.py`, `test_service_logs.py` | Integration and training test scripts. |

## Production checklist

1. Populate `.env` with unique secrets, especially `COLLECTOR_INGEST_TOKEN`.
2. Mount real, access-controlled application/device logs at `./logs` and start the collector profile.
3. Configure OIDC/SAML/JWT validation in `backend/app/auth.py`; do not rely on the legacy user-ID header.
4. Install a trusted TLS certificate and add an Nginx `listen 443 ssl` server block before exposing HTTPS.
5. Configure the SCADA gateway with actual PLC addresses or register dynamic machines via `POST /api/scada/machines/register`.
