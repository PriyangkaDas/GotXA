import os
import time
import requests

# Operational Endpoint Configuration
BASE_URL = os.getenv("TARGET_HOST", "http://localhost:5000")
TARGET_URL = os.getenv("TARGET_URL", f"{BASE_URL}/login")

def run_service_log_test():
    """
    Sends standard HTTP requests designed to test how the web application 
    logs diagnostic status codes and operational messages to the SIEM.
    """
    print("[*] Initiating operational log telemetry test...")
    
    # Standard operational test cases (e.g., malformed content types, bad routes)
    test_cases = [
        {"desc": "Testing missing input parameters", "data": {}},
        {"desc": "Testing invalid endpoint path", "url": f"{BASE_URL}/invalid_route"},
    ]
    
    for case in test_cases:
        target = case.get("url", TARGET_URL)
        try:
            print(f"[*] Running test case: {case['desc']}")
            res = requests.post(target, data=case.get("data", {}), timeout=3)
            print(f"[+] Server responded | Status Code: {res.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[-] Connection event recorded: {e}")
            
        time.sleep(1)

if __name__ == "__main__":
    run_service_log_test()