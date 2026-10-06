#!/usr/bin/env python3
"""
GotXA Interactive Penetration Testing Console (New_Machine)
"""

import os
import sys
from colorama import init, Fore, Style

init(autoreset=True)

def show_banner():
    print(f"""{Fore.RED}
  ███▄    █ ▓█████  █     █░    ███▄ ▄███▓ ▄▄▄       ▄████▄   ██░ ██  ██▓ ███▄    █ ▓█████ 
  ██ ▀█   █ ▓█   ▀ ▓█░ █ ░█░   ▓██▒▀█▀ ██▒▒████▄    ▒██▀ ▀█  ▓██░ ██▒▓██▒ ██ ▀█   █ ▓█   ▀ 
 ▓██  ▀█ ██▒▒███   ▒█░ █ ░█    ▓██    ▓██░▒██  ▀█▄  ▒▓█    ▄ ▒██▀▀██░▒██▒▓██  ▀█ ██▒▒███   
 ▓██▒  ▐▌██▒▒▓█  ▄ ░░█ █ █▒    ▒██    ▒██ ░██▄▄▄▄██ ▒▓▓▄ ▄██▒░▓█ ░██ ░██░▓██▒  ▐▌██▒▒▓█  ▄ 
 ▒██░   ▓██░░▒████▒ ░░▀▄█▀░    ▒██▒   ░██▒ ▓█   ▓██▒▒ ▓███▀ ░░▓█▒░██▓░██░▒██░   ▓██░░▒████▒
 ░ ▒░   ▒ ▒ ░░ ▒░ ░  ░ ▒░ ▒     ░ ▒░   ░  ░ ▒▒   ▓▒█░░ ░▒ ▒  ░ ▒ ░░▒░▒░▓  ░ ▒░   ▒ ▒ ░░ ▒░ ░
 ░ ░░   ░ ▒░ ░ ░  ░    ░░ ░     ░  ░      ░  ▒   ▒▒ ░  ░  ▒    ▒ ░▒░ ░ ▒ ░░ ░░   ░ ▒░ ░ ░  ░
    ░   ░ ░    ░        ░      ░      ░     ░   ▒   ░         ░  ░░ ░ ▒ ░   ░   ░ ░    ░   
          ░    ░  ░       ░           ░         ░  ░░ ░       ░  ░  ░ ░           ░    ░  ░
                                                    ░                                      
{Fore.YELLOW}           >> GotXA Industrial & Corporate Penetration Testing Node <<{Style.RESET_ALL}
""")

def main_menu():
    show_banner()
    while True:
        print(f"{Fore.CYAN}[--- SELECT PENTEST ATTACK VECTOR ---]{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}[1]{Style.RESET_ALL} TCP Socket Port Scanner")
        print(f"  {Fore.GREEN}[2]{Style.RESET_ALL} Corporate Portal Brute Force & Credential Spray")
        print(f"  {Fore.GREEN}[3]{Style.RESET_ALL} SQL Injection Simulation/Detection Test")
        print(f"  {Fore.GREEN}[4]{Style.RESET_ALL} Industrial OT / SCADA Modbus Register Attack")
        print(f"  {Fore.GREEN}[5]{Style.RESET_ALL} Run All Attack Vectors Concurrently")
        print(f"  {Fore.RED}[0]{Style.RESET_ALL} Exit Console")
        print()

        choice = input(f"{Fore.YELLOW}New_Machine:~$ {Style.RESET_ALL}").strip()

        if choice == '1':
            os.system("python3 port_scanner.py")
        elif choice == '2':
            os.system("python3 attack_bruteforce.py")
        elif choice == '3':
            os.system("python3 attack_sqli.py")
        elif choice == '4':
            os.system("python3 attack_modbus_ot.py")
        elif choice == '5':
            os.system("bash run_all_attacks.sh")
        elif choice in ('0', 'q', 'exit'):
            print(f"{Fore.CYAN}Exiting New_Machine Pentest Suite.{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Invalid option selected.{Style.RESET_ALL}")
        print("\n" + "-"*60 + "\n")

if __name__ == "__main__":
    main_menu()
