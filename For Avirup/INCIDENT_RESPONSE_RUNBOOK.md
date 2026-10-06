# GotXA — Incident Response Runbook

This runbook defines the step-by-step operational procedures for SOC analysts responding to security incidents generated on the GotXA platform.

---

## 📞 Incident Response Workflow

The platform follows the standard **NIST SP 800-61** Incident Response Life Cycle:

```
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. Detection & Analysis                                     │
  │    - Alerts ingested on SIEM dashboard                      │
  │    - Analysts review severity, host name, and event logs    │
  └──────────────────────────────┬──────────────────────────────┘
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ 2. Containment, Eradication, & Recovery                     │
  │    - Automated SOAR playbooks execute initial block         │
  │    - Analysts request manual containment overrides          │
  └──────────────────────────────┬──────────────────────────────┘
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ 3. Post-Incident Activity                                   │
  │    - Merge related tickets into primary cases               │
  │    - Generate NIST PDF compliance reports                   │
  └─────────────────────────────────────────────────────────────┘
```

---

## 🚨 Threat Scenario Procedures

### Scenario A: Brute Force Attempt (Alert Rule: `Brute Force Attempt`)
An adversary is conducting authentication password spraying against corporate accounts.

#### 1. Analysis Phase
*   Check the alert assignee and details on the **SIEM Alerts** dashboard.
*   Identify the target user account and client IP address from the log payload message.
*   Query audit events to check if this IP has hit other endpoints (`GET /api/audit-events`).

#### 2. Containment Phase
*   The SOAR engine automatically fires the **`brute_force_ip_block`** playbook, adding an `iptables` drop rule for the attacking IP.
*   *Manual Action*: If the brute force threshold is breached and the username is compromised, invoke the **`brute_force_credential_lock`** playbook via the SOAR panel to lock the account in the database.

#### 3. Recovery Phase
*   Confirm the attacker's traffic is dropped (their dashboard log streams will cease).
*   Coordinate with the user to update passwords and unlock the credential record.

---

### Scenario B: Remote Code Execution (Alert Rule: `Privilege Escalation`)
An adversary has injected shell scripts into the corporate diagnostic panel, gaining local command access.

#### 1. Analysis Phase
*   Verify the compromised host container name (e.g., `corp-portal-agent`).
*   Review the command execution string in the alert details to identify the payload run by the attacker (e.g., executing `cat /etc/passwd`).

#### 2. Containment Phase
*   The SOAR engine triggers **`privilege_escalation_isolate`**, calling the Docker socket to disconnect the compromised container from the `corporate_net` bridge.
*   *Manual Action*: Verify that the container is isolated by running a ping command from the gateway container; the compromised host must be unreachable.

#### 3. Recovery & Eradication Phase
*   Deploy a patched version of the web container with command sanitization.
*   Run the container restart playbook (**`service_availability_restart`**) to rebuild the container environment from a clean image.

---

### Scenario C: SCADA Registry Manipulation (Alert Rule: `Critical System Error`)
An attacker pivot has accessed the OT Modbus network and modified PLC register limits, driving Refinery heaters above safe operational thresholds.

#### 1. Analysis Phase
*   Observe the SCADA dashboard gauges. Identify registers flashing red (e.g., Temperature > 200°C).
*   Inspect the SCADA Gateway polling logs to confirm the source IP writing to port 5003 or 5004.

#### 2. Containment Phase
*   The SOAR engine runs **`critical_error_restart`** or **`service_availability_restart`** to reboot the target PLC simulator.
*   The PLC baseline initial values are restored on reboot, cooling the system down.

#### 3. Recovery Phase
*   Block the lateral proxy IP at the corporate boundary gateway.
*   Generate the **Post-Incident Analysis report** via the Report Generation panel for compliance recordkeeping.
