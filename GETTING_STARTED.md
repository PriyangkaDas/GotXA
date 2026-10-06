# GotXA Getting Started Guide

GotXA is a Docker Compose cyber range that combines a Flask SIEM/SOAR API, PostgreSQL, Redis, Celery report workers, three web dashboards, optional log collection, and an optional SCADA gateway.

This guide covers:

- Running the complete stack from the repository
- Using the Docker images published to Docker Hub
- Configuring secrets and persistent data
- Verifying health and troubleshooting common startup problems
- Enabling the optional logging and SCADA services

## 1. Choose a Deployment Method

There are two supported ways to start GotXA.

### Repository build

Use this for development, demonstrations, and when you need the current source code:

```powershell
docker compose up -d --build
```

The current `docker-compose.yml` uses `build:` for the application services. It therefore builds images from the local repository; it does not automatically pull your Docker Hub images.

### Docker Hub deployment

You have published at least these images:

```text
alchemistx22/gotxa:backend
alchemistx22/gotxa:scada-frontend
alchemistx22/gotxa:corp-frontend
```

Those images can be pulled on another machine, but they do not deploy the whole platform by themselves. PostgreSQL, Redis, Celery, the API gateway, and the other frontend services still need to be started and connected on the same Docker network.

The existing Compose file must also be changed or overridden to use registry images instead of `build:` directives. Do not assume that a backend image alone contains PostgreSQL, Redis, the gateway, or the frontend assets.

## 2. Prerequisites

Install the following on the host that will run GotXA:

- Docker Desktop 24 or newer on Windows/macOS, or Docker Engine with the Compose plugin on Linux
- At least 8 GB of RAM allocated to Docker for a comfortable demonstration environment
- At least 10 GB of free disk space for images, build cache, and PostgreSQL data
- Git, if cloning the repository

Confirm the installation:

```powershell
docker --version
docker compose version
docker info
```

On Windows, start Docker Desktop and make sure it is using Linux containers before running Compose.

## 3. Get the Repository

```powershell
git clone https://github.com/Gibberlin/GotXA.git
Set-Location GotXA
```

If the repository is already present:

```powershell
Set-Location C:\path\to\GotXA
git pull
```

The Compose file expects to be run from the repository root because its build contexts and volume paths are relative to that directory.

## 4. Frontend Build Prerequisite

The three frontend Dockerfiles copy prebuilt files from these directories:

```text
frontend/siem_dashboard/dist/
frontend/corp_portal/dist/
frontend/scada_dashboard/dist/
```

Make sure those directories contain the frontend build output before using `docker compose up --build`. If the directories are missing, the frontend image builds will fail at the `COPY .../dist/` step.

If the frontend projects contain their own package manifests, build them with the project’s package manager before building the containers. A typical workflow is:

```powershell
Set-Location frontend\siem_dashboard
npm install
npm run build

Set-Location ..\corp_portal
npm install
npm run build

Set-Location ..\scada_dashboard
npm install
npm run build

Set-Location ..\..
```

Use the scripts and package manager declared by each frontend project. Do not run these commands if the `dist` directories are already supplied by the repository or by a release artifact.

## 5. Configure Environment Variables

Create a `.env` file in the repository root. Docker Compose reads it automatically.

Example:

```dotenv
TZ=Asia/Kolkata
POSTGRES_PASSWORD=replace-with-a-strong-db-password
DATABASE_URL=postgresql://siem_user:replace-with-a-strong-db-password@siem-postgres:5432/siem_db
COLLECTOR_INGEST_TOKEN=replace-with-a-long-random-token
```

`COLLECTOR_INGEST_TOKEN` protects log ingestion from the collector and SCADA gateway. Use the same value for services that submit events. Generate a strong value rather than using the example text.

The Compose file supplies only non-sensitive service defaults. Set the database password, matching `DATABASE_URL`, and collector token before starting the stack:

| Setting | Current value | Purpose |
| --- | --- | --- |
| PostgreSQL database | `siem_db` | Application database |
| PostgreSQL user | `siem_user` | Application database user |
| PostgreSQL password | `.env:POSTGRES_PASSWORD` | Required deployment secret |
| PostgreSQL internal host | `siem-postgres` | Docker network hostname |
| Redis internal host | `redis` | Celery broker and result backend |
| Backend port | `5000` | Flask API |
| Reports directory | `/app/reports` | Generated report storage |
| SOAR enforcement | `false` in Compose | Keeps demo actions labeled `Simulated Containment` |

For an internet-facing deployment, replace the demo database password and review the application authentication and secret handling before exposing port 80 or 443.

### SOAR enforcement scope

With `SOAR_REAL_MODE=true`, the `containment.block_ip` playbook may install an `iptables` DROP rule in the backend container. Keep `SOAR_REAL_MODE=false` for demonstrations; those actions are explicitly labeled `Simulated Containment`. PLC actions remain simulated/emulated.

## 6. Start the Core Stack

From the repository root:

```powershell
docker compose up -d --build
```

This starts:

- `redis`
- `siem-postgres`
- `backend`
- `celery-worker`
- `siem-soar-frontend`
- `corp-portal-frontend`
- `scada-frontend`
- `api-gateway`

The first build can take several minutes. Follow startup logs with:

```powershell
docker compose logs -f
```

The command returns when the logs are attached; press `Ctrl+C` to stop viewing logs. It does not stop the containers.

## 7. Enable Optional Services

The log collector and SCADA gateway are disabled unless their Compose profiles are selected.

Start the core stack plus the log collector:

```powershell
docker compose --profile production-logging up -d --build
```

Start the core stack plus the SCADA gateway:

```powershell
docker compose --profile scada up -d --build
```

Enable both optional services:

```powershell
docker compose --profile production-logging --profile scada up -d --build
```

The collector reads host log files from `./logs`, mounted read-only at `/logs`. The SCADA gateway sends events to the backend and expects PLC hosts named `ot-plc-refinery-1` and `ot-plc-refinery-2` unless overridden with environment variables. Those PLC services are not defined in the current root Compose file, so start or add the PLC services before expecting live Modbus polling.

## 8. Verify the Deployment

List services and their state:

```powershell
docker compose ps
```

Check the gateway:

```powershell
curl.exe http://localhost/health
curl.exe http://localhost/status
```

Check the backend directly:

```powershell
curl.exe http://localhost:5000/health
```

Expected health responses should indicate that the gateway or backend is healthy. If a service is still starting, wait for its health check and inspect its logs.

Check individual logs:

```powershell
docker compose logs --tail=100 backend
docker compose logs --tail=100 celery-worker
docker compose logs --tail=100 api-gateway
docker compose logs --tail=100 siem-postgres
```

## 9. Open the Application

With the gateway running, open:

| Component | URL |
| --- | --- |
| SIEM/SOAR dashboard | http://localhost/ |
| Corporate portal | http://localhost/corp/ |
| SCADA dashboard | http://localhost/scada/ |
| API through gateway | http://localhost/api/ |
| Backend directly | http://localhost:5000/ |
| PostgreSQL from the host | `localhost:5432` |

The frontend services are internal to the Compose network. Port 80 is exposed by `api-gateway`, which routes requests to the correct frontend and backend service.

## 10. Default Development Authentication

For API testing, the project supports demo role identity through the `X-User-ID` header:

```powershell
curl.exe -H "X-User-ID: admin" http://localhost/api/health
```

Common demo identities documented by the project are `admin`, `soc_manager`, and `analyst`. Treat these as demonstration identities, not production authentication.

## 11. Docker Hub Images

To pull an image from Docker Hub:

```powershell
docker login
docker pull alchemistx22/gotxa:backend
docker pull alchemistx22/gotxa:scada-frontend
docker pull alchemistx22/gotxa:corp-frontend
```

To see locally available images:

```powershell
docker image ls
```

To publish another locally built service, tag it with the exact Docker Hub repository and tag, then push it:

```powershell
docker tag gotxa-api-gateway:latest alchemistx22/gotxa:api-gateway
docker push alchemistx22/gotxa:api-gateway
```

Repeat this for every service that you want to deploy from Docker Hub. The repository tag is only a label; it does not combine multiple service images into one application image.

### Important: using registry images with Compose

The current Compose file uses `build:` for GotXA services. Pulling an image does not cause Compose to use it. A registry-based deployment needs a Compose override or a revised Compose file whose services use `image:`, for example:

```yaml
services:
  backend:
    image: alchemistx22/gotxa:backend
    build: null
```

The image must contain the configuration expected by the Compose service, and every required service must be available on the same `gotxa-net` network. Do not remove the health checks, environment variables, volumes, or service dependencies when creating the override.

## 12. Persistent Data and Volumes

Compose creates named volumes for data that should survive container recreation:

| Volume | Contents |
| --- | --- |
| `siem-db-data` | PostgreSQL database |
| `reports-data` | Generated reports |
| `siem-frontend-data` | SIEM frontend mount |
| `corp-frontend-data` | Corporate frontend mount |
| `scada-frontend-data` | SCADA frontend mount |

List volumes:

```powershell
docker volume ls
```

Stopping or recreating containers normally preserves named volumes:

```powershell
docker compose down
docker compose up -d
```

To intentionally delete the database and other named volume data:

```powershell
docker compose down -v
```

Use `down -v` only when resetting the environment. Back up important PostgreSQL data first.

## 13. Useful Operations

Restart one service:

```powershell
docker compose restart backend
```

Rebuild one service:

```powershell
docker compose up -d --build backend
```

Open a shell in the backend container:

```powershell
docker compose exec backend sh
```

Inspect the final Compose configuration:

```powershell
docker compose config
```

Stop the stack without deleting volumes:

```powershell
docker compose down
```

## 14. Troubleshooting

### `tag does not exist`

The local image does not have the tag being pushed. Find the source image and tag it:

```powershell
docker image ls
docker tag gotxa-backend:latest alchemistx22/gotxa:backend
docker push alchemistx22/gotxa:backend
```

### Frontend build fails at `COPY .../dist/`

Build the corresponding frontend first, or obtain the prebuilt `dist` artifact. The frontend Dockerfiles do not run the JavaScript build themselves.

### Backend is unhealthy

Inspect the backend and its dependencies:

```powershell
docker compose logs backend
docker compose logs siem-postgres
docker compose logs redis
```

The backend waits for healthy PostgreSQL and Redis services. Database startup on the first run can take longer than expected.

### Port 80 or 5000 is already in use

Find the process using the port, stop it, or change the host-side port mapping in a Compose override. The value before the colon is the host port; the value after it is the container port.

### Containers start but the browser shows gateway errors

Check all service states and gateway logs:

```powershell
docker compose ps
docker compose logs api-gateway
```

The gateway routes to service names such as `backend`, `scada-frontend`, and `corp-portal-frontend`. These names must remain resolvable on the shared `gotxa-net` network.

### Data disappeared

Check whether `docker compose down -v` was used. That command deletes the named volumes, including `siem-db-data`.

## 15. Security Checklist Before Sharing the Deployment

- Replace the demo PostgreSQL password.
- Set a strong `COLLECTOR_INGEST_TOKEN`.
- Do not expose PostgreSQL port 5432 to the public internet.
- Put TLS termination and access control in front of port 80/443.
- Review the demo authentication identities and disable them for production.
- Keep attack simulation containers isolated and run them only in an authorized lab.
- Back up the `siem-db-data` and `reports-data` volumes.
- Review SOAR actions before enabling any real containment mode.

## 16. Recommended First-Run Sequence

```powershell
Set-Location C:\path\to\GotXA
docker info
docker compose config
docker compose up -d --build
docker compose ps
curl.exe http://localhost/health
curl.exe http://localhost:5000/health
```

After the core stack is healthy, enable the optional profiles as needed and watch the logs while exercising the dashboards.

## 17. Further Documentation

- [`README.md`](README.md) - platform overview and quick reference
- [`doc/IMPORTANT_FACTS.md`](doc/IMPORTANT_FACTS.md) - ports, credentials, and environment variables
- [`doc/ARCHITECTURE.md`](doc/ARCHITECTURE.md) - architecture and service behavior
- [`doc/API_SPECIFICATION.md`](doc/API_SPECIFICATION.md) - API endpoints and payloads
- [`doc/TESTING_AND_INTEGRATION.md`](doc/TESTING_AND_INTEGRATION.md) - testing and frontend integration
- [`For Avirup/CONTAINERS_OVERVIEW.md`](For%20Avirup/CONTAINERS_OVERVIEW.md) - container topology
- [`For Avirup/PENTESTING_GUIDE.md`](For%20Avirup/PENTESTING_GUIDE.md) - authorized attack simulation workflow
