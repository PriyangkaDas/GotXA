# GotXA — Container Stack & Technology Justification

This document provides a comprehensive overview of the containerized services in the GotXA platform, outlines the technical rationale for our architectural choices, and discusses future roadmap scopes.

---

## 🐋 1. Containerized Stack Overview

GotXA is orchestrated using a multi-container **Docker Compose** structure. The services communicate over an isolated bridge network (`gotxa-net`, subnet `172.26.0.0/16`).

```
                                      [ API Gateway: Port 80 / 443 ]
                                                    │
             ┌──────────────────────────────────────┼──────────────────────────────────────┐
             ▼                                      ▼                                      ▼
     [siem-soar-frontend]                 [corp-portal-frontend]                    [scada-frontend]
     (Internal Port 80)                     (Internal Port 80)                     (Internal Port 80)
             │                                      │                                      │
             └──────────────────────────────────────┼──────────────────────────────────────┘
                                                    ▼
                                      [ gotxa-backend: Port 5000 ]
                                                    │
                 ┌──────────────────────────────────┼──────────────────────────────────┐
                 ▼                                  ▼                                  ▼
          [siem-postgres]                    [celery-worker]                  [gotxa-log-collector]
          (Port 5432)                          (Background)                       (Port 5006)
                 │                                  │                                  │
                 └──────────────────┬───────────────┘                                  │
                                    ▼                                                  ▼
                             [redis: Port 6379]                                [ot-scada-gateway]
                                                                                  (Port 5002)
```

### Services Directory

| Container Name | Service Role | Docker Context / Image | Storage Volume Mounts | Health Checks |
| :--- | :--- | :--- | :--- | :--- |
| **`api-gateway`** | Ingress Nginx Reverse Proxy | `webservers/api-gateway/` | `nginx.conf`, static mappings | `wget --spider http://127.0.0.1/health` |
| **`siem-soar-frontend`**| SOC & Incident Dashboard UI | `webservers/siem-soar-frontend/` | `siem-frontend-data` (`/app/frontend`) | `wget --spider http://127.0.0.1/health` |
| **`corp-portal-frontend`**| Corporate Portal UI | `webservers/corp-portal-frontend/` | `corp-frontend-data` (`/app/frontend`) | `wget --spider http://127.0.0.1/health` |
| **`scada-frontend`** | Industrial HMI Gauges UI | `webservers/scada-frontend/` | `scada-frontend-data` (`/app/frontend`) | `wget --spider http://127.0.0.1/health` |
| **`gotxa-backend`** | REST API Core & Auth Engine | `backend/` (Gunicorn 4 workers) | `./backend:/app`, `reports-data:/app/reports` | `python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"` |
| **`celery-worker`** | Async Report Generation Engine | `backend/Dockerfile.celery` | `./backend:/app`, `reports-data:/app/reports` | Dependent on Postgres & Redis health |
| **`siem-postgres`** | Relational Database (ACID) | `postgres:15-alpine` | `siem-db-data:/var/lib/postgresql/data` | `pg_isready -U siem_user -d siem_db` |
| **`redis-cache`** | Broker & Telemetry Cache | `redis:7-alpine` | In-memory | `redis-cli ping` |
| **`gotxa-log-collector`** *(Profile: production-logging)* | Multi-source Log Ingestion Service | `Dockerfile.collector` | `./logs:/logs:ro` | Ingestion HTTP validation (`5006`) |
| **`ot-scada-gateway`** *(Profile: scada)* | Modbus PLC & OT Gateway Bridge | `Dockerfile.scada` | Host network / virtual PLC link | Modbus loopback / Ingress telemetry (`5002`) |
| **`New_Machine`** | Kali Linux Penetration Testing Node | `kalilinux/kali-rolling` (`New_Machine/`) | `./New_Machine:/workspace` | Process state & interactive shell |

---

## 🛠️ 2. Architectural Technology Justification

We chose our core technology stack based on resource efficiency, developer familiarity, and realistic industrial design mapping.

### A. Python Flask (REST API Backend)
*   **Why**: Flask is a lightweight micro-framework. It allows us to build REST APIs rapidly without the overhead of heavy opinionated engines (like Django), which is ideal for deploying in resource-constrained environments like edge gateways.
*   **Authentication & Session Management**: Built-in stateful session tokens (`UserSession`, `gotxa_sess_...`), bearer authentication, session expiration tracking, and comprehensive audit trail logging (`AuditLogger`).
*   **Alternative Considered**: FastAPI. While FastAPI provides automatic typing, Flask’s integration with standard SQLAlchemy ORM is mature and robust for orchestrating dynamic state models.

### B. React + Vite (Frontend Dashboards)
*   **Why**: GotXA requires real-time dashboard updates (e.g., log streams, SCADA gauges). React's virtual DOM allows for efficient rendering of telemetry values without page refreshes. Vite provides fast local hot-reload builds, streamlining development.
*   **Alternative Considered**: Angular or plain Vanilla JavaScript. Angular is too heavy for simple dashboard UIs, and Vanilla JS becomes difficult to maintain when handling complex states (like tracking pending SOAR execution status).

### C. PostgreSQL (Database Layer)
*   **Why**: Security audit logs and relational incidents must be immutable and possess transaction integrity (ACID compliance). PostgreSQL allows us to enforce relational constraints, run complex nested queries, and create performant indices on high-query alert fields.
*   **Alternative Considered**: MongoDB. NoSQL databases lack relational constraints, making alert-to-incident linkages, RBAC sessions, and audit logs prone to consistency issues.

### D. Redis & Celery (Async Task Processing)
*   **Why**: Rendering PDF compliance reports requires significant CPU time. By offloading these tasks to Celery workers with a Redis message broker, the API gateway can respond immediately with a `202 Accepted` status, preventing the UI from freezing.

### E. Nginx (API Gateway & Asset Server)
*   **Why**: Nginx acts as a unified reverse-proxy entry point. It simplifies client-side routing, handles CORS constraints, and allows us to configure security headers and rate limits in a single, centralized location.

---

## 🔮 3. Future Scope & Roadmap

GotXA is designed to be modular. We plan to expand the platform in the following areas:

### A. Deep Threat Detection (Suricata IDS Integration)
*   **Upgrade**: Deploy a Suricata container inside the bridge network configured for packet mirroring.
*   **Outcome**: Allows the SIEM to detect network-level attacks (like port scans, DDoS, or command-and-control beacons) in addition to log-level threats.

### B. Distributed Logging Cluster (Elasticsearch/OpenSearch)
*   **Upgrade**: Replace or augment the PostgreSQL logging table with a dedicated Elasticsearch indexing cluster.
*   **Outcome**: Enables lightning-fast full-text searches and log aggregation across thousands of host machines, simulating a true enterprise SOC.

### C. Active Directory (AD) & Enterprise OAuth2 / SAML Integration
*   **Upgrade**: Connect the backend authentication middleware and `UserSession` engine to an enterprise Keycloak or OpenLDAP directory server.
*   **Outcome**: Enables seamless Single Sign-On (SSO) alongside internal RBAC session tokens.

### D. Machine Learning Anomaly Detection
*   **Upgrade**: Run a lightweight Python background service using Scikit-Learn or PyTorch to monitor Modbus registers.
*   **Outcome**: Automatically alerts on slow, subtle temperature/pressure anomalies that slip past standard static threshold rules (detecting slow-leak attacks).

### E. Multi-Tenant SaaS Transition
*   **Upgrade**: Implement tenant isolation layers, per-tenant database schemas/routing, usage metering, subscription enforcement, and billing webhooks.
*   **Outcome**: Enables GotXA to scale into a commercial multi-tenant cloud SIEM/SOAR platform.
*   **Reference**: Full commercial strategy, pricing calculations, and technical checklist are documented in [`Additional Doc/`](../Additional%20Doc/).

