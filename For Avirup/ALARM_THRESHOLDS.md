# GotXA — Refinery Process Alarm Thresholds

This document defines the operational baseline parameters, status ranges, and automated incident response triggers for the operational technology (OT) refinery simulation.

---

## 🎛️ PLC Operational Parameter Reference

The refinery simulation models two separate process units using holding registers mapped via Modbus TCP.

```
 [PLC-1: Refinery Heater (Port 5003)]           [PLC-2: Mixer Tank (Port 5004)]
   Reg 40001: Crude Oil Temperature               Reg 40003: Chemical Flow Rate
   Reg 40002: Pressure Control Valve              Reg 40004: Mixer Speed (Future)
```

| Parameter Name | Target Register | Baseline Value | Safe Operating Range | Warning Range | Emergency Shutdown (ESD) Limit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Heater Temperature** | `40001` | **`180.0°C`** | `170.0°C` - `190.0°C` | `160.0°C` - `169.9°C` / `190.1°C` - `200.0°C` | **`<160.0°C`** (Cool-down crash) or **`>200.0°C`** (Overheating risk) |
| **Valve Pressure** | `40002` | **`50.0 PSI`** | `45.0` - `55.0 PSI` | `40.0` - `44.9 PSI` / `55.1` - `60.0 PSI` | **`<40.0 PSI`** (Line collapse) or **`>60.0 PSI`** (Overpressure burst) |
| **Mixer Flow Rate** | `40003` | **`50.0 L/min`**| `40.0` - `60.0 L/min` | `30.0` - `39.9 L/min` / `60.1` - `70.0 L/min` | **`<30.0 L/min`** (Starvation block) or **`>70.0 L/min`** (Overflow overflow) |

*   *Note: Modbus holding registers store integer values (unsigned 16-bit). Telemetry calculations scale values by `10` (e.g., a register reading of `1850` correlates to `185.0` in HMI representations).*

---

## 🟢 Operational Telemetry Bands

The SCADA gateway parses PLC parameters and translates them into HMI visual indicator bands:

### 1. Safe Status Band (Green)
*   **Definition**: Values fall within nominal limits representing standard, stable operation.
*   **HMI Dashboard Action**: SVGs render as steady green. No security alerts.

### 2. Warning Status Band (Orange)
*   **Definition**: Values indicate process deviations caused by wear-and-tear or telemetry noise anomalies.
*   **HMI Dashboard Action**: SVGs flash yellow/orange.
*   **SIEM Correlation**: Ingested as a `LOW` priority warning event, triggering the **`warning_monitor_escalation`** playbook to increase telemetry polling resolution.

### 3. Critical Status Band / Emergency Shutdown (Red)
*   **Definition**: Parameters exceed physical safety design boundaries, indicating telemetry sensor faults, line blockages, or malicious register alteration.
*   **HMI Dashboard Action**: SVGs flash red with system sirens.
*   **SIEM Correlation**: Ingested as a `HIGH` priority alert.
*   **SOAR Action**: Fires the **`critical_error_restart`** or **`service_availability_restart`** playbooks to reboot PLC systems and purge memory, bringing registers back to safe initial defaults.

---

## 🛠️ Modbus Registry Verification
You can query PLC registers from your terminal using standard python Modbus commands:
```python
from pymodbus.client import ModbusTcpClient

# Query PLC-1 heater temperature
client = ModbusTcpClient('localhost', port=5003)
client.connect()
result = client.read_holding_registers(0, 1) # Reads register 40001 (idx 0)
print(f"Current temperature: {result.registers[0] / 10.0}°C")
client.close()
```
