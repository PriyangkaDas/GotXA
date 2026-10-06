#!/usr/bin/env python3
"""
TCP Socket Port Scanner
Scans common ports and services across the GotXA internal container network.
"""

import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from colorama import init, Fore, Style

init(autoreset=True)

TARGET_HOSTS = [
    ("Frontend", [80, 443]),
    ("SoC", [5000]),
    ("Database", [5432]),
    ("radisCache", [6379]),
    ("corp-portal-frontend", [80]),
    ("scada-frontend", [80]),
    ("siem-soar-frontend", [80]),
    ("ot-scada-gateway", [5002]),
    ("gotxa-log-collector", [5006])
]

def scan_port(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        result = s.connect_ex((host, port))
        if result == 0:
            print(f"  {Fore.GREEN}[OPEN]{Style.RESET_ALL} Port {port:<5} on {host}")
            s.close()
            return port, True
        s.close()
        return port, False
    except Exception:
        return port, False

def run_network_scan():
    print(f"{Fore.CYAN}===================================================={Style.RESET_ALL}")
    print(f"{Fore.CYAN}    GotXA TCP Socket Port Scanner                  {Style.RESET_ALL}")
    print(f"{Fore.CYAN}===================================================={Style.RESET_ALL}\n")

    for host, ports in TARGET_HOSTS:
        print(f"{Fore.YELLOW}[*] Scanning Target Host: {host}{Style.RESET_ALL}")
        with ThreadPoolExecutor(max_workers=5) as executor:
            for port in ports:
                executor.submit(scan_port, host, port)
        print()

    print(f"{Fore.CYAN}[✓] Network reconnaissance scan complete.{Style.RESET_ALL}")

if __name__ == "__main__":
    run_network_scan()
