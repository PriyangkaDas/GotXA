# GotXA — Production Hardening & Recommendations Guide

This guide details the security configurations needed to move the GotXA platform from an isolated cyber-range simulation to a hardened, production-grade deployment.

---

## 🔒 Security Roadmap

```
 ┌───────────────────┐     Enforce HTTPS/TLS      ┌───────────────────┐
 │   Nginx Gateway   ├───────────────────────────>│   Client Browser  │
 └─────────┬─────────┘                            └───────────────────┘
           │
           │  JWT Validation (Drop X-User-ID)
           ▼
 ┌───────────────────┐     Least-Privilege DB     ┌───────────────────┐
 │    Backend API    ├───────────────────────────>│    PostgreSQL     │
 └───────────────────┘                            └───────────────────┘
```

---

## 🛡️ 1. API Authentication & Token Management

### The Problem
The current backend uses the `X-User-ID` header in demo mode, which trusts client-side user assertions and auto-provisions administrative privileges.

### Hardening Recommendations
1.  **Enforce JWT Authentication**: Replace header-based authentication with cryptographically signed JSON Web Tokens (JWT) containing short expiration windows (e.g., 15 minutes).
2.  **Secret Management**: Load the JWT signature key from secure environment stores (e.g., AWS Secrets Manager or HashiCorp Vault) instead of code constants.
3.  **Role Verification**: Enforce verification of claims within JWT tokens on the backend before handling any API requests.

---

## 🐋 2. Docker Container Security & Socket Isolation

### The Problem
The SOAR engine connects directly to the host container daemon using the Unix socket file (`/var/run/docker.sock`). If an adversary compromises the backend API, they can issue arbitrary container execution commands and gain root access to the host.

### Hardening Recommendations
1.  **Drop Direct Socket Mounts**: Remove the `/var/run/docker.sock` volume mount from the backend compose configuration.
2.  **Deploy an API Proxy Daemon**: Set up a read-only Docker socket proxy container (e.g., `tecnativa/docker-socket-proxy`) that sits between the API and the socket, allowing only specific routes (like `restart` or `disconnect`) and blocking administrative commands.
3.  **User Namespace Mapping**: Run container processes as non-root system users (configured via the `USER` flag in the Dockerfile).

---

## 🗄️ 3. Relational Database Least Privilege

### The Problem
The backend connects to PostgreSQL using the database owner credentials (`siem_user`), giving it full schema modification (`DROP TABLE`, `ALTER SCHEMA`) permissions.

### Hardening Recommendations
1.  **Differentiate User Accounts**: Create separate database roles:
    *   **`gotxa_api_user`**: Restricted to Data Manipulation Language (DML) queries (`SELECT`, `INSERT`, `UPDATE`) on specific tables.
    *   **`gotxa_migration_user`**: Privileged role used exclusively during deployment schema migrations.
2.  **Network Access Lists**: Configure `pg_hba.conf` in the database container to accept connections exclusively from the backend subnet range, blocking direct external access.

---

## 🌐 4. Nginx Reverse Proxy & HTTP Gateways

### The Problem
The outer reverse-proxy listens on port 80 (HTTP), sending authentication tokens and settings parameters across the network in cleartext.

### Hardening Recommendations
1.  **Enforce TLS/HTTPS**: Enable HTTPS using TLS 1.3 on port 443 with automated certificates (e.g., Let's Encrypt / Certbot).
2.  **Redirect HTTP Traffic**: Configure a global server redirect in `nginx.conf` routing port 80 traffic to port 443.
3.  **Security Headers**: Inject HTTP security headers inside gateway responses:
    ```nginx
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self';" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    ```
