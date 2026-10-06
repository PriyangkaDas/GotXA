# ⚔️ New_Machine — Penetration Testing & Adversary Simulation Node

`New_Machine` is an isolated security assessment and penetration testing container located within the GotXA internal Docker bridge network (`gotxa-net`).

---

## 🛠️ How to Execute Pentests from Host

You can run individual scripts or launch the interactive CLI console:

### 1. Interactive Menu Console
```bash
docker exec -it New_Machine python menu.py
```

### 2. Run All Attacks in Sequence
```bash
docker exec -it New_Machine bash run_all_attacks.sh
```

### 3. Run Specific Attack Vectors
* **Corporate Portal Brute Force**:
  ```bash
  docker exec -it New_Machine python attack_bruteforce.py
  ```
* **Corporate Portal SQL Injection**:
  ```bash
  docker exec -it New_Machine python attack_sqli.py
  ```
* **SCADA / Modbus Register Attack**:
  ```bash
  docker exec -it New_Machine python attack_modbus_ot.py
  ```
* **Internal Network & Port Scanner**:
  ```bash
  docker exec -it New_Machine python port_scanner.py
  ```

---

## 🎯 Target Endpoints in `gotxa-net`

| Target Host | Ports / Protocol | Target Description |
| :--- | :--- | :--- |
| `backend:5000` | HTTP / REST API | Core SIEM & Corporate API |
| `api-gateway:80` | HTTP / Nginx Proxy | Main Ingress Gateway |
| `corp-portal-frontend:80` | HTTP / Web | Corporate Workspace UI |
| `scada-frontend:80` | HTTP / Web | SCADA HMI Telemetry Portal |
| `ot-scada-gateway:5002` | HTTP / Modbus | OT Pipeline Telemetry Gateway |
| `siem-postgres:5432` | TCP / PostgreSQL | SIEM Relational Database |
