# SCADA HMI Dashboard — Architecture, Vision & API Handoff

## 1. Product Intent & Architecture

The SCADA Dashboard is an industrial Human-Machine Interface (HMI) for real-time visualization and supervisory control over refinery machinery. It features holographic process diagrams, live telemetry meters, alarm notification rails, and audited actuator control panels.

All process state changes, threshold breaches, and operator commands are forwarded in parallel to the SIEM.

---

## 2. Interactive Operator Experience

1. **Refinery Overview**: Shows interactive representations of Refinery 1 (Heater & Pressure Vessel) and Refinery 2 (Chemical Flow Mixer), plus any dynamically discovered PLCs.
2. **Telemetry Streaming**: Subscribes to live Modbus telemetry polled at 2-second intervals (`GET /api/modbus`).
3. **Machine Detail & Controls**: Selecting a machine opens a drawer with real-time gauges, trend charts, active safety alarms, and setpoint controls.
4. **Audited Commands**: Operators propose setpoint changes or emergency stops; the gateway validates operating bounds and logs structured audit records.

---

## 3. Component Hierarchy

| Area | Components | Description |
| :--- | :--- | :--- |
| **App Shell** | `ScadaLayout`, `ConnectionBanner`, `AlarmRail`, `LastUpdated` | Persistent frame, alarm banner, connection indicators. |
| **HMI Scene** | `HologramScene`, `MachineNode`, `TelemetryLabel`, `FlowLine` | Layered SVG process diagram with animated flow paths. |
| **Detail Drawer** | `MachineDetailDrawer`, `MachineHealth`, `TrendChart`, `ControlAuditList` | Deep telemetry insights, historical charts, audit history. |
| **Controls** | `ControlKnob`, `SetpointInput`, `ToggleControl`, `EmergencyStop` | Validated actuator controls and interlocks. |

---

## 4. REST API Contract

### 4.1 Live Telemetry APIs
| Method | Endpoint | Purpose | Key Fields |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/modbus` | Poll all machinery states | `refinery_1`, `refinery_2`, `dynamic_machines` |
| `GET` | `/api/modbus/refinery-1` | Refinery 1 heater telemetry | `temperature`, `pressure`, `status`, `last_update` |
| `GET` | `/api/modbus/refinery-2` | Refinery 2 flow telemetry | `flow_rate`, `status`, `last_update` |
| `GET` | `/health` | Gateway & PLC connectivity status | `status`, `service`, `plc_1`, `plc_2` |

### 4.2 Dynamic Discovery & Industrial Control APIs
| Method | Endpoint | Purpose | Key Fields |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/scada/machines` | All machines & allowable limits | `id`, `name`, `registers`, `controls`, `status` |
| `POST` | `/api/scada/machines/register` | Dynamically register new PLC | `id`, `name`, `host`, `port`, `registers`, `controls` |
| `POST` | `/api/scada/machines/{id}/commands` | Submit actuator command | `command`, `value`, `reason` $\rightarrow$ `status`, `command_id` |
| `GET` | `/api/scada/commands/{command_id}` | Poll command execution result | `status`, `applied_at`, `rejection_reason` |
| `GET` | `/api/scada/alarms` | Active & historical safety alarms | `id`, `machine_id`, `severity`, `message`, `status` |
| `POST` | `/api/scada/alarms/{id}/acknowledge` | Acknowledge alarm | `note` $\rightarrow$ updated alarm record |
| `GET` | `/api/scada/audit` | Machine control audit trail | `command`, `actor`, `requested_at`, `status`, `value` |
