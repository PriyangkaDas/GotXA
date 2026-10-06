#!/usr/bin/env python3
"""
Targeted SQL Injection Simulation Script
Tests authentication filters and input sanitization on Corporate Portal and Backend APIs.
"""

import time
import requests
from colorama import init, Fore, Style

init(autoreset=True)

TARGET_URL = "http://backend:5000/api/corporate/auth/login"

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "admin' --",
    "' UNION SELECT NULL, username, password FROM users --",
    "admin' #",
    "' OR 1=1 --",
    "admin' AND 1=1 --"
]

def run_sqli_test():
    print(f"{Fore.CYAN}[*] Starting SQL Injection Simulation/Detection Test...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[*] Target endpoint: {TARGET_URL}{Style.RESET_ALL}\n")

    for i, payload in enumerate(SQLI_PAYLOADS, 1):
        data = {"username": payload, "password": "dummy_password_123"}
        try:
            res = requests.post(TARGET_URL, json=data, timeout=5)
            print(f"{Fore.MAGENTA}[*] Payload #{i}: [ {payload} ] -> Status: {res.status_code}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[!] Error executing SQLi probe #{i}: {e}{Style.RESET_ALL}")
        time.sleep(1)

    print(f"\n{Fore.CYAN}[✓] SQLi audit simulation completed. Audit logs recorded in SIEM.{Style.RESET_ALL}")

if __name__ == "__main__":
    run_sqli_test()
