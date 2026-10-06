# GotXA — Testing & Integration Guide

This guide details the automated test suites, manual security simulation scripts, and frontend integration standards for the GotXA platform.

---

## 1. Automated Security & SOAR Threat Testing

GotXA provides a closed-loop security validation pipeline (Attack → Real Logging → Ingestion → Detection Rule → Alert Generation → SOAR Playbook Containment).

```
 ┌────────────────┐      SQLi / RCE / Brute force      ┌─────────────────┐
 │ Attack Script  ├───────────────────────────────────>│ Vulnerable App  │
 └────────────────┘                                    └────────┬────────┘
                                                                │ logs
                                                                ▼
 ┌────────────────┐         Automated Action           ┌─────────────────┐
 │  SOAR Engine   │<───────────────────────────────────┤  Log Collector  │
 └──────┬─────────┘                                    └─────────────────┘
        │ iptables Block / Docker Isolate / Reboot
        ▼
 ┌────────────────┐
 │ Attacker Block │
 └────────────────┘
```

### 1.1 End-to-End SOAR Test Runner (`test_soar.py`)
Automates the full threat-to-remediation verification loop:
```bash
python test_soar.py
```
**Scenarios Tested**:
1. **Brute Force Attack** $\rightarrow$ Triggers `ip_block` (`iptables` drop rule).
2. **Brute Force Threshold** $\rightarrow$ Triggers `credential_lock` (account lock in database).
3. **Remote Code Execution** $\rightarrow$ Triggers `container_isolate` (`docker network disconnect`).
4. **Critical Server Crash** $\rightarrow$ Triggers `service_restart` (reboots the service container).
5. **Network Anomaly** $\rightarrow$ Triggers combined `ip_block` and `rate_limit` playbooks.

---

## 2. SCADA Telemetry & Dynamic Discovery Verification

### 2.1 SCADA & Parallel Collector Unit Test
Verifies dynamic machine registration, non-blocking SIEM telemetry queueing, dynamic folder file discovery, and structured log parsing:

```bash
python -c "
import tempfile, json, os
from pathlib import Path
from scada_gateway import poller, siem_publisher
from log_collector import ParallelLogCollector

# 1. Verify Dynamic Machine Registration
poller.register_machine('refinery-3', {
    'name': 'Refinery 3', 'host': 'ot-plc-refinery-3', 'port': 5007,
    'registers': {'column_pressure': {'addr': 10, 'qty': 1, 'scale': 0.1, 'unit': 'bar'}}
})
assert 'refinery-3' in poller.machines
print('[+] SCADA Dynamic Machine Registered Successfully')

# 2. Test Parallel SIEM Publisher
siem_publisher.publish_change('refinery-3', 'column_pressure', 85.4, '2026-09-01T01:00:00')
assert siem_publisher.queue.qsize() >= 1
print('[+] SIEM Publisher enqueued event asynchronously')
"
```

---

## 3. Manual Penetration Testing & Exploit Scripts

Individual penetration testing scripts simulate targeted network threats:

### 3.1 SQL Injection Attack (SQLi)
```bash
python pentesting_scripts/attack_sqli.py
```
*   **Target**: `POST http://localhost:5001/login`
*   **Payload**: `{"username": "' OR 1=1 --", "password": "any"}`
*   **Expected Telemetry**: `SQL_EXECUTED` log with query and client IP.

### 3.2 Authentication Brute Force
```bash
python pentesting_scripts/attack_bruteforce.py
```
*   **Target**: `POST http://localhost:5001/login`
*   **Expected Telemetry**: Burst of `AUTH_FAILURE` events triggering `RULE-BRUTE-FORCE`.

### 3.3 Remote Code Execution (RCE)
```bash
python pentesting_scripts/attack_rce.py
```
*   **Target**: `POST http://localhost:5001/diagnostic` with command injection (`127.0.0.1; whoami`).
*   **Expected Telemetry**: `COMMAND_EXECUTED` log with stdout and return code.

---

## 4. React Frontend Integration Guide

React frontends are served through Nginx. Use standard Axios clients configured with authentication headers:

### 4.1 Axios API Client Setup
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost/api', // Router gateway URL path
  headers: {
    'Content-Type': 'application/json',
    'X-User-ID': 'admin' // Demo mode authentication header
  }
});

export default api;
```

### 4.2 Polling Live SCADA Telemetry
```javascript
import React, { useState, useEffect } from 'react';
import api from './api';

export function ScadaMonitor() {
  const [data, setData] = useState({});

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        const res = await api.get('/modbus');
        setData(res.data);
      } catch (err) {
        console.error('Failed to poll Modbus telemetry:', err);
      }
    };
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h3>Refinery 1 Temp: {data.refinery_1?.temperature ?? '--'} °C</h3>
      <h3>Refinery 2 Flow: {data.refinery_2?.flow_rate ?? '--'} L/min</h3>
    </div>
  );
}
```

### 4.3 Streaming Raw Security Logs
```javascript
import React, { useState, useEffect } from 'react';
import api from './api';

export function RawLogStream() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await api.get('/raw-stream?limit=50');
        setLogs(res.data.items || []);
      } catch (err) {
        console.error('Failed to stream raw logs:', err);
      }
    };
    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      {logs.map(log => (
        <div key={log.id} className={`log-row ${log.level.toLowerCase()}`}>
          <span>[{log.timestamp}]</span> <strong>{log.host}</strong>: {log.message}
        </div>
      ))}
    </div>
  );
}
```
