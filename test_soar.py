#!/usr/bin/env python3
"""
GotXA Cyber Range — SOAR Verification and Threat Testing Framework

This script automates the verification of threat detection rules and corresponding
SOAR responses. It triggers various simulated attacks and system anomalies, then
polls the SIEM API to ensure the SOAR Engine executes the correct mitigation playbooks.

Threat Scenarios Tested:
1. Brute Force Attempt -> IP Block (Real iptables DROP)
2. Brute Force Threshold -> Credential Lock (Simulated locking)
3. Remote Code Execution -> Container Isolation (Real docker network disconnect)
4. Critical System Error -> Service Restart (Real docker restart)
5. Network Anomaly -> IP Block + Rate Limit (Real iptables + Rate limit)
6. Warning Event -> Monitoring Escalation (Simulated monitoring frequency increase)
"""

import sys
import time
import requests
import json

import os
SIEM_URL = os.getenv("SIEM_URL", "http://localhost:5000")
PORTAL_URL = os.getenv("PORTAL_URL", "http://localhost:5000")

# Load collector ingestion token from environment or .env file
COLLECTOR_TOKEN = os.getenv("COLLECTOR_INGEST_TOKEN")
if not COLLECTOR_TOKEN:
    try:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip().startswith("COLLECTOR_INGEST_TOKEN="):
                        COLLECTOR_TOKEN = line.strip().split("=", 1)[1].strip('"\'')
                        break
    except Exception:
        pass
if not COLLECTOR_TOKEN:
    COLLECTOR_TOKEN = "gotxa_dev_collector_token_change_me"

INGEST_HEADERS = {
    "X-Collector-Token": COLLECTOR_TOKEN,
    "Content-Type": "application/json"
}

# ANSI Terminal Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_banner():
    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{GREEN}      [SOAR] GOTXA CYBER RANGE - THREAT TESTING FRAMEWORK{RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

def check_services():
    print(f"{BOLD}[*] Checking cyber range service health...{RESET}")
    
    # Check SIEM
    try:
        r = requests.get(f"{SIEM_URL}/health", timeout=3)
        if r.status_code == 200:
            print(f"  {GREEN}[+] SIEM Server: HEALTHY{RESET}")
        else:
            print(f"  {RED}[-] SIEM Server: UNHEALTHY (Status {r.status_code}){RESET}")
            sys.exit(1)
    except Exception as e:
        print(f"  {RED}[-] SIEM Server: UNREACHABLE ({e}){RESET}")
        sys.exit(1)
        
    # Check Corporate Portal
    try:
        r = requests.get(PORTAL_URL, timeout=3)
        if r.status_code == 200:
            print(f"  {GREEN}[+] Corporate Portal: HEALTHY{RESET}")
        else:
            print(f"  {RED}[-] Corporate Portal: UNHEALTHY (Status {r.status_code}){RESET}")
            sys.exit(1)
    except Exception as e:
        print(f"  {RED}[-] Corporate Portal: UNREACHABLE ({e}){RESET}")
        sys.exit(1)
    print()

def clear_alert_queue():
    print(f"{BOLD}[*] Maintenance: Clearing the active alert queue in PostgreSQL...{RESET}")
    try:
        import subprocess
        # Clear alert queue by setting status to Investigating
        cmd = ["docker", "exec", "Database", "psql", "-U", "siem_user", "-d", "siem_db", "-c", "UPDATE alerts SET status = 'Investigating' WHERE status = 'Open';"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except Exception:
            cmd = ["docker", "exec", "siem-postgres", "psql", "-U", "siem_user", "-d", "siem_db", "-c", "UPDATE alerts SET status = 'Investigating' WHERE status = 'Open';"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"  {GREEN}[+] Active queue cleared successfully ({res.stdout.strip()}){RESET}\n")
    except Exception as e:
        print(f"  {YELLOW}[!] Database maintenance query failed: {e}{RESET}")
        print(f"  Continuing test suite...\n")

def wait_for_soar_action(alert_rule, action_type, timeout_sec=25):
    """Poll the SIEM SOAR actions endpoint until the expected action is found and completed."""
    print(f"  {BOLD}[i] Waiting for SOAR Engine to process rule '{alert_rule}'...{RESET}")
    start_time = time.time()
    
    while time.time() - start_time < timeout_sec:
        try:
            r = requests.get(f"{SIEM_URL}/api/v1/soar/actions?limit=25", timeout=3)
            if r.status_code == 200:
                actions = r.json().get('data', [])
                for action in actions:
                    # Match action
                    if action.get('action_type') == action_type and alert_rule in action.get('description', ''):
                        if action.get('status') == 'completed':
                            print(f"  {GREEN}[+] SOAR Mitigated: {action.get('description')}{RESET}")
                            print(f"    {CYAN}Status: {action.get('status').upper()}{RESET}")
                            detail = action.get('result_detail', '').replace('\n', '\n    ')
                            print(f"    {CYAN}Execution Trail:{RESET}\n    {detail}\n")
                            return True
                        elif action.get('status') == 'failed':
                            print(f"  {RED}[-] SOAR Failed on {action_type} playbook (Action ID: {action.get('id')}){RESET}")
                            return False
            time.sleep(2)
        except Exception as e:
            time.sleep(2)
            
    print(f"  {RED}[-] Timeout: No completed SOAR action for '{alert_rule}' / '{action_type}' found within {timeout_sec} seconds.{RESET}\n")
    return False

def test_critical_system_error():
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    print(f"{BOLD}[TEST 1] Critical System Error (Service Restart Playbook){RESET}")
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    
    print("[*] Simulating a fatal kernel crash on corporate-portal-agent...")
    payload = {
        "message": "Critical System Error: FATAL: kernel panic - out of memory, killing process group",
        "host": "corp-portal-agent",
        "level": "CRITICAL"
    }
    
    r = requests.post(f"{SIEM_URL}/logs/ingest", json=payload, headers=INGEST_HEADERS)
    if r.status_code != 200:
        print(f"  {RED}Failed to send log payload (Status {r.status_code}){RESET}\n")
        return False
        
    success = wait_for_soar_action("Critical System Error", "service_restart")
    if success:
        print("  [*] Sleeping for 6 seconds to allow corporate portal service to complete reboot...")
        time.sleep(6)
    return success

def test_privilege_escalation():
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    print(f"{BOLD}[TEST 2] Privilege Escalation (Container Isolation Playbook){RESET}")
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    
    print("[*] Triggering diagnostic RCE injection with sudo credentials (10 times to flush collector)...")
    for i in range(10):
        try:
            requests.post(f"{PORTAL_URL}/diagnostic", data={"host": f"127.0.0.1; sudo whoami # {i}"}, timeout=2)
        except Exception:
            pass
        
    success = wait_for_soar_action("Privilege Escalation", "container_isolate")
    
    # Restore connection if isolated
    if success:
        print("[*] Restoring corporate portal network connection...")
        try:
            import subprocess
            for net in ["gotxa_gotxa-net", "gotxa-net"]:
                for container in ["corp-portal-frontend", "SoC"]:
                    subprocess.run(["docker", "network", "connect", net, container], capture_output=True)
            print(f"  {GREEN}[+] Network connection restored.{RESET}\n")
        except Exception as e:
            print(f"  {RED}Failed to restore network connection: {e}{RESET}\n")
    return success

def test_brute_force():
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    print(f"{BOLD}[TEST 3] Brute Force Threshold (IP Block + Credential Lock){RESET}")
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    
    print("[*] Generating 10 invalid authentication attempts on corporate portal...")
    for i in range(10):
        try:
            requests.post(f"{PORTAL_URL}/login", data={"username": "sysadmin", "password": f"pwd{i}"}, timeout=2)
        except Exception:
            pass
            
    print("  [*] Authentications sent. Checking SOAR containment results...")
    
    # Check IP Block
    ip_blocked = wait_for_soar_action("Brute Force Threshold", "ip_block")
    # Check Credential Lock
    cred_locked = wait_for_soar_action("Brute Force Threshold", "credential_lock")
    
    return ip_blocked and cred_locked

def test_network_anomaly():
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    print(f"{BOLD}[TEST 4] Network Anomaly Detected (IP Block + Rate Limit){RESET}")
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    
    print("[*] Ingesting NMAP port scanner logs from corporate workstation...")
    payload = {
        "message": "Network Anomaly Detected: NMAP port scan activity detected from source IP 192.168.1.205",
        "host": "corp-workstation-agent",
        "src_ip": "192.168.1.205",
        "level": "HIGH"
    }
    
    r = requests.post(f"{SIEM_URL}/logs/ingest", json=payload, headers=INGEST_HEADERS)
    if r.status_code != 200:
        print(f"  {RED}Failed to send log payload (Status {r.status_code}){RESET}\n")
        return False
        
    # Check IP Block
    ip_blocked = wait_for_soar_action("Network Anomaly Detected", "ip_block")
    # Check Rate Limiting
    rate_limited = wait_for_soar_action("Network Anomaly Detected", "rate_limit")
    
    return ip_blocked and rate_limited

def test_warning_monitoring():
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    print(f"{BOLD}[TEST 5] Warning Event (Monitoring Escalation Playbook){RESET}")
    print(f"{BOLD}{YELLOW}------------------------------------------------------------{RESET}")
    
    print("[*] Ingesting device heat warning from operational refinery PLC...")
    payload = {
        "message": "high temperature warning threshold exceeded (78C)",
        "host": "ot-plc-refinery-1",
        "level": "WARN"
    }
    
    r = requests.post(f"{SIEM_URL}/logs/ingest", json=payload, headers=INGEST_HEADERS)
    if r.status_code != 200:
        print(f"  {RED}Failed to send log payload (Status {r.status_code}){RESET}\n")
        return False
        
    return wait_for_soar_action("Warning Event", "monitor_escalation")

def run_test_suite():
    print_banner()
    check_services()
    clear_alert_queue()
    
    results = {}
    
    # Run Tests
    results["Critical System Error (Service Restart)"] = test_critical_system_error()
    results["Privilege Escalation (Container Isolation)"] = test_privilege_escalation()
    results["Brute Force (IP Block & Account Lockout)"] = test_brute_force()
    results["Network Anomaly (IP Block & Rate Limit)"] = test_network_anomaly()
    results["Warning Event (Monitoring Escalation)"] = test_warning_monitoring()
    
    # Print Summary Report
    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{GREEN}                  SOAR THREAT TESTING SUMMARY REPORT{RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")
    
    all_passed = True
    for test_name, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        if not passed:
            all_passed = False
        print(f"  {BOLD}{test_name:<50}{status:>10}")
        
    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    if all_passed:
        print(f"  {BOLD}{GREEN}[+] SUCCESS: All SOAR playbooks and detection loops verified successfully!{RESET}")
    else:
        print(f"  {BOLD}{RED}[-] FAILURE: One or more SOAR playbooks failed or timed out during verification.{RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

if __name__ == "__main__":
    run_test_suite()
