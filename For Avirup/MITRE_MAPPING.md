# GotXA — MITRE ATT&CK Matrix Mapping

This report maps the threat simulation vectors of the GotXA platform to the industry-standard **MITRE ATT&CK Enterprise Matrix** and **MITRE ATT&CK for Industrial Control Systems (ICS)**.

---

## 🗺️ Mapping Overview

The attack simulation models an adversary starting from public corporate systems and pivoting laterally into the sensitive Industrial Control System (OT) network to manipulate refinery processes.

```
 [IT Corporate Portal]          [Corporate workstation]          [Modbus OT Network]
   SQLi / Portal RCE                 Pivot Workstation            PLC register manipulation
 (MITRE T1190 / T1203)             (MITRE T1090 / T1021)            (MITRE T0836 / T0855)
```

| Attack Vector | Zone | MITRE Tactic | MITRE Technique | Description | Automated SOAR Mitigation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Portal SQL Injection** | Corporate | Initial Access / Privilege Escalation | **T1190**: Exploit Public-Facing Application | Attacker uses SQL bypass payloads to gain administrative corporate portal access. | None. Ingested as critical telemetry log. |
| **Login Password Spraying** | Corporate | Credential Access | **T1110**: Brute Force | Attacker fires repeated logins to guess credentials. | **`brute_force_ip_block`**: Injects an `iptables` drop rule for the attacker IP. |
| **Diagnostics Endpoint RCE** | Corporate | Execution | **T1203**: Exploitation for Client Execution | Attacker executes operating system commands via diagnostic forms. | **`privilege_escalation_isolate`**: Disconnects the vulnerable container from Nginx corp net. |
| **OT Gateway Pivot** | IT/OT Bridge | Lateral Movement | **T1090**: Proxy / **T1021**: Remote Services | Attacker routes command shell queries through the corporate host to query SCADA. | **`network_anomaly_block`**: Blocks lateral IP addresses and rate-limits connections. |
| **Modbus PLC Alteration** | Operational Technology | Impair Process Control | **T0836**: Modify Parameter / **T0855**: Unauthorized Command | Attacker directly issues Modbus commands to heater/mixer registers. | **`service_availability_restart`**: Reboots the PLC simulation server to baseline. |

---

## 🔍 Detailed Attack Vector Analysis

### 1. Exploit Public-Facing Application (T1190)
*   **Context**: The employee portal (`vulnerable_app.py`) accepts database parameters without validation.
*   **Attack Action**: The adversary passes `' OR 1=1 --` into the login query, tricking SQLAlchemy into returning the administrative user record.
*   **Defense Correlation**: The SIEM rule matches SQL syntax patterns (`UNION`, `SELECT`, `OR 1=1`) in raw web server access logs and generates a high-severity alert.

### 2. Brute Force Login Attempts (T1110)
*   **Context**: The portal login does not throttle authentication failure requests.
*   **Attack Action**: Attacker sends multiple login requests within seconds.
*   **Defense Correlation**: The SIEM engine detects more than 10 login failures from a single IP within a 30-second window, triggering the **`brute_force_ip_block`** playbook to ban the source IP.

### 3. Remote Code Execution via OS Command Injection (T1203)
*   **Context**: The diagnostics panel pipes parameter inputs directly to OS system shells (`subprocess.popen`).
*   **Attack Action**: Attacker appends command separators (`;`, `&&`, `|`) to execute malicious host commands.
*   **Defense Correlation**: The SIEM rule matches shell syntax (`/etc/passwd`, `whoami`, `bin/sh`) inside the logs, triggering the **`container_isolate`** playbook.

### 4. Lateral Movement & Proxy Routing (T1090)
*   **Context**: The compromised IT web server possesses routing capabilities into the isolated OT network range.
*   **Attack Action**: Attacker pivots by using the corporate host as a proxy hop to access the SCADA Gateway.
*   **Defense Correlation**: The SIEM alerts on connection routing patterns originating outside the whitelisted subnet range.

### 5. Modification of Process Parameter Registers (T0836)
*   **Context**: The simulated Modbus TCP servers lack authentication.
*   **Attack Action**: Attacker sends write command packets directly to Modbus ports (`5003`, `5004`) to push heater registers above emergency limits.
*   **Defense Correlation**: The SCADA polling daemon alerts on high register telemetry, and the SOAR playbook restarts the PLC container to restore the baseline process state.
