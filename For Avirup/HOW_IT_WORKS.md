# GotXA — How It Works (Layman's Guide)

Welcome to GotXA! This guide explains how the system automatically detects and blocks cyber attacks, using simple language and everyday analogies.

---

## 🏢 The Security Analogy

Think of the GotXA platform as a **secure warehouse facility** containing both corporate offices and industrial refinery equipment.

```
  ┌─────────────────────────────────────────────────────────────┐
  │ 🏢 The Warehouse Facility (System Architecture)             │
  ├──────────────────┬──────────────────┬───────────────────────┤
  │ 📹 Security      │ 🚨 Central Alarm │ 🤖 Robotic Security    │
  │    Cameras       │    Station       │    Fences             │
  │ (Log Collectors) │  (SIEM Engine)   │ (SOAR Playbook Engine)│
  └──────────────────┴──────────────────┴───────────────────────┘
```

1.  **The Intruder (Attacker)**: A hacker attempting to break into the facility.
2.  **Security Cameras (Log Collectors)**: Cameras watching and recording everything that happens at the doors and gates.
3.  **Central Alarm Station (SIEM Engine)**: A guard watching the camera feeds who alerts the system when an intruder is detected.
4.  **Robotic Security Fences (SOAR Engine)**: Automated systems that lock doors, sound alarms, and isolate intruders immediately without waiting for human intervention.

---

## 🔄 The Attack & Defense Loop (Step-by-Step)

Here is how the automated security loop works when a hacker attacks the system:

```
  [1. Hacker Attacks] ──> [2. Access Logs Written] ──> [3. Ingestion & Analysis]
                                                                │
  [5. Attack Quarantined] <── [4. Auto-Playbook Fired] <────────┘
```

### Step 1: The Hacker Attacks
*   **Action**: A hacker runs an attack script (like a password-guessing bot) against the corporate portal login form.
*   **Analogy**: The intruder tries to shake and force open the warehouse back door.

### Step 2: The Camera Records the Event (Logs)
*   **Action**: The corporate web server records the failed logins and writes them as entries in a text file.
*   **Analogy**: The security camera records footage of the intruder shaking the door handle.

### Step 3: The Alarm Station Ingests the Footage (SIEM)
*   **Action**: The Log Collector ships the log entries to the SIEM database. The SIEM rule engine reads the logs and alerts: *"Warning: 10 login failures detected from IP address 192.168.1.50!"*
*   **Analogy**: The camera feed is sent to the central station, where a computer matches the intruder's pattern and sounds the warning alarm.

### Step 4: The Automated Playbook Responds (SOAR)
*   **Action**: The SOAR engine queries the database, matches the alert to the `brute_force_ip_block` playbook, and decides to block the source.
*   **Analogy**: The automated computer system identifies the lock-tampering behavior and activates the defense protocol.

### Step 5: The Intruder is Blocked (Mitigation)
*   **Action**: The system runs a command that drops all future packets from the attacker's IP address. The hacker's connection freezes, and the attack stops.
*   **Analogy**: The warehouse security system drops a heavy metal barrier in front of the door, locking the intruder out of the facility.

---

## 🟢 The Industrial SCADA Dashboard

In the **Operational Technology (OT)** zone, GotXA simulates a chemical oil refinery. 
*   **How it Works**: Sensors continuously measure the heater temperature and pressure. The SCADA dashboard reads these sensor values every 2 seconds and displays them as colored gauges (Green for safe, Red for emergency).
*   **If an Attack Occurs**: If a hacker tampers with the refinery temperature registers, the system alerts the SIEM, and the SOAR engine automatically restarts the simulator, cooling the heater back down to a safe state before damage occurs.
