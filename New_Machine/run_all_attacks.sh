#!/usr/bin/env bash
echo "=========================================================="
echo "    🚀 Running Full Penetration Testing Suite on GotXA    "
echo "=========================================================="

echo "[1/4] Running Reconnaissance Port Scan..."
python3 port_scanner.py

echo "[2/4] Launching Corporate Portal SQL Injection Test..."
python3 attack_sqli.py

echo "[3/4] Launching Corporate Portal Brute Force Attack..."
python3 attack_bruteforce.py

echo "[4/4] Launching OT / SCADA Modbus Register Attack..."
python3 attack_modbus_ot.py

echo "=========================================================="
echo "    ✅ All Penetration Test Attacks Executed Successfully! "
echo "    Check SIEM SOC Console (http://localhost/) for Alerts "
echo "=========================================================="
