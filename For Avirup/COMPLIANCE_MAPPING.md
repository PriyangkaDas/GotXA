# GotXA — Security Compliance Mapping Report

This report maps the security features of the GotXA platform (Role-Based Access Control, Immutable Audit Logging, SOAR Playbooks) to the regulatory requirements specified in **NIST SP 800-53 (Security and Privacy Controls)**, **NIST SP 800-61 (Incident Handling)**, and **ISO/IEC 27001 (Information Security Management)**.

---

## 📋 Security Controls Mapping Matrix

| GotXA Platform Feature | NIST SP 800-53 Control | ISO 27001 Control | Compliance Requirement Met |
| :--- | :--- | :--- | :--- |
| **Role-Based Access Control (RBAC)** | **AC-2**: Account Management / **AC-3**: Access Enforcement | **A.9.2**: User registration / **A.9.4**: System access control | Enforces separation of duties. Restricts analyst and manager privileges based on job role template authorization. |
| **Immutable Audit Logging** | **AU-2**: Event Logging / **AU-10**: Non-repudiation | **A.12.4**: Logging and monitoring | Captures complete mutation histories (before/after states, client IPs, correlation IDs) in write-once tables. |
| **SOAR Containment Playbooks** | **IR-4**: Incident Handling / **IR-5**: Incident Monitoring | **A.16.1**: Incident management | Coordinates automated threat mitigation steps (network isolation, IP blocks) instantly upon threat detection. |
| **Dynamic Setting Approvals** | **CM-3**: Configuration Change Control | **A.12.1**: Operational procedures | Demands multi-approver authorization tickets and roll-back plans before high-risk changes are committed. |
| **JIT Privileged Access** | **AC-6**: Least Privilege | **A.9.4.4**: Privilege management | Limits administrative exposure by provisioning temporary, time-bound access keys that expire automatically. |

---

## 🔍 In-Depth Control Analysis

### 1. NIST SP 800-53: Access Control (AC) & Configuration Management (CM)
*   **Enforcement**: The backend checks permissions on every request through the `@require_permission` decorator, enforcing least-privilege operations.
*   **Change Control**: All configuration updates undergo setting validations (`CM-3`). High-risk changes are stored as `applied` or `pending` status inside the `SettingChange` schema, verifying that managers validate operational changes.

### 2. ISO/IEC 27001: Operational Logging & Security Monitoring (A.12.4)
*   **Enforcement**: The `AuditLogger` captures client details (`User-Agent`, IP address) and UUID correlation IDs to trace lateral movement attempts across microservices.
*   **Tamper Protection**: Database user accounts (`gotxa_api_user`) lack permissions to perform `UPDATE` or `DELETE` on the `audit_events` tables, establishing write-once compliance properties.

### 3. NIST SP 800-61: Incident Containment & Recovery Guidance (IR-4)
*   **Enforcement**: The SOAR playbook execution logic acts as an automated incident containment helper. 
*   **Containment Isolation**: By separating compromised containers from internal bridges, the playbook prevents lateral movement into production and OT database zones, complying with containment guidelines.
