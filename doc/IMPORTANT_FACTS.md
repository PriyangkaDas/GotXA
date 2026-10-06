# GotXA — Important Facts & Quick Reference Guide

This document is an executive quick-reference cheat sheet for developers, security analysts, and administrators working with the GotXA platform.

---

## 1. System Ports & Services Map

| Service / Container Name | Internal Port | External Port | Access / Route Protocol | Description |
| :--- | :--- | :--- | :--- | :--- |
| **api-gateway** | `80`, `443` | `80`, `443` | `http://localhost/` | Single entry point reverse proxy (Nginx). |
| **siem-soar-frontend** | `80` | None | Proxied to `/` | SIEM & SOAR React dashboard. |
| **corp-portal-frontend** | `80` | None | Proxied to `/corp` | Corporate login & corporate admin dashboard. |
| **scada-frontend** | `80` | None | Proxied to `/scada` | SCADA Industrial HMI dashboard. |
| **gotxa-backend** | `5000` | `5000` | `http://localhost:5000/api` | Primary Flask REST API. Also proxied to `/api/`. |
| **celery-worker** | None | None | Internal | Celery background worker (PDF report generation). |
| **siem-postgres** | `5432` | `5432` | `localhost:5432` | PostgreSQL relational database. |
| **redis-cache** | `6379` | None | Internal | Redis cache and Celery broker. |
| **corp-portal-agent** | `5001` | `5001` | `http://localhost:5001/` | Vulnerable corporate site (simulates attacks). |
| **ot-scada-gateway** | `5002` | `5002` | `http://localhost:5002/api` | Modbus SCADA polling REST gateway. |
| **ot-plc-refinery-1** | `5003` | `5003` | Modbus TCP (`5003`) | PLC 1 simulation (temperature & pressure). |
| **ot-plc-refinery-2** | `5004` | `5004` | Modbus TCP (`5004`) | PLC 2 simulation (flow rate mixer). |
| **log-collector** | `5006` | `5006` | `http://localhost:5006/` | Parallel multi-threaded real log collector. |

---

## 2. Default Credentials & Authentication

### 2.1 Demo Header Authentication (RBAC)
When testing REST endpoints, pass the **`X-User-ID`** header to establish role identity:
*   **`admin`** role: `X-User-ID: admin` (Full permissions)
*   **`soc_manager`** role: `X-User-ID: soc_manager` (Incident triage + execution, requires escalation approvals for containment)
*   **`analyst`** role: `X-User-ID: analyst` (Read-only alerts/incidents, cannot run playbooks)

### 2.2 Relational Database Connection (PostgreSQL)
*   **Host**: `localhost` (external) or `siem-postgres` (Docker internal)
*   **Port**: `5432`
*   **Database Name**: `siem_db`
*   **Database User**: `siem_user`
*   **Database Password**: Set `POSTGRES_PASSWORD` in the uncommitted root `.env` file.
*   **ORM URI**: Set `DATABASE_URL` in the uncommitted root `.env` file.

### 2.3 Collector Ingestion Token
*   **Environment Variable**: `COLLECTOR_INGEST_TOKEN`
*   **Header**: `X-Collector-Token: <token>`

---

## 3. Core Environment Variables

| Variable | Default Value | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `.env` value | PostgreSQL connection string. |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Redis broker URI for Celery. |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Redis backend URI for Celery results. |
| `COLLECTOR_INGEST_TOKEN` | *High entropy secret* | Auth token for `/api/ingest/events`. |
| `SOAR_REAL_MODE` | `true` in Compose | `false` records simulated playbooks; `true` applies real backend-container `iptables` IP blocks. Requires the backend `NET_ADMIN` capability. |
| `REPORTS_DIR` | `/app/reports` | Directory where Celery writes PDF reports. |
| `SIEM_INGRESS_URL` | `http://backend:5000/api/ingest/events` | Ingestion target for collector and SCADA gateway. |
| `LOGS_BASE_DIR` | `/logs` | Base directory scanned for machine log discovery. |

---

## 4. Key Directory Structure

```
GotXA/
├── Additional Doc/     # Strategic planning, SaaS pricing guide, and multi-tenant technical implementation
├── backend/            # Flask REST API, PostgreSQL ORM models, Celery tasks, PDF engine
├── doc/                # Complete technical architecture, API specs, and runbooks
├── For Avirup/         # Specialized guides (MITRE mapping, compliance, incident runbooks, glossary)
├── frontend/           # React SPAs (SIEM SOC Dashboard, Corp Portal, SCADA HMI)
├── New_Machine/        # Adversary simulation node and attack automation (SQLi, RCE, Brute force)
├── webservers/         # Nginx reverse proxy configs for API Gateway and frontends
├── log_collector.py    # Parallel multi-threaded real log collector
├── modbus_plc_server.py# Instrumented Modbus TCP PLC industrial simulation
├── scada_gateway.py    # Async Modbus poller & parallel SIEM publisher
└── test_soar.py        # Threat testing and automated SOAR verification framework
```

---

## 5. Security Alerts & Playbook Actions Mapping

| Ingested Alert Rule | Severity | Playbook Name | Active Mitigation Action |
| :--- | :--- | :--- | :--- |
| **Brute Force Attempt** | HIGH | `brute_force_ip_block` | **IP Block**: Bans attacker's IP on port 80 via `iptables`. |
| **Brute Force Threshold Exceeded** | HIGH | `brute_force_ip_block`<br>`brute_force_credential_lock` | **Dual Action**: Bans attacker IP + locks username in database. |
| **Critical System Error** | HIGH | `critical_error_restart` | **Service Restart**: Automatically reboots the crashed container. |
| **Network Anomaly Detected** | HIGH | `network_anomaly_block`<br>`network_anomaly_rate_limit` | **Dual Action**: Bans malicious IP + applies traffic rate-limiting. |
| **Privilege Escalation** | HIGH | `privilege_escalation_isolate` | **Isolate**: Uses Docker socket to disconnect container from corporate network. |
| **RULE-NEW-DEVICE-DISCOVERY**| MEDIUM| `asset_quarantine` | **Quarantine**: Flags new asset as untrusted until admin review. |
