#!/usr/bin/env python3
"""
OT PLC Modbus Server - Refinery Simulation
Simple Modbus TCP server
"""

import json
import logging
import random
import time
import os
from datetime import datetime
from threading import Thread
from pathlib import Path

try:
    from pymodbus.server import StartAsyncTcpServer
    from pymodbus.device import ModbusDeviceIdentification
    from pymodbus.datastore.context import ModbusBaseSlaveContext, ModbusServerContext
    import asyncio
except ImportError as e:
    StartAsyncTcpServer = None
    ModbusDeviceIdentification = None
    class ModbusBaseSlaveContext: pass
    class ModbusServerContext: pass
    import asyncio
    logging.warning(f"pymodbus not available in local environment: {e}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# MODBUS PARAMETERS
# ============================================================================

# ============================================================================
# MODBUS PARAMETERS
# ============================================================================

AGENT_NAME = os.getenv('AGENT_NAME', 'ot-plc-unknown')
LOG_DIR = f"/logs/ot-{AGENT_NAME.split('-')[-1]}"
LOG_FILE = f"{LOG_DIR}/app.log"
SIEM_LOG_FILE = f"/logs/ot-instrumentation.log"

# Support dynamic register configuration or presets
if 'refinery-1' in AGENT_NAME:
    MODBUS_PORT = int(os.getenv('MODBUS_PORT', '5003'))
    REGISTERS = {'temperature': 40001, 'pressure': 40002}
    INITIAL_VALUES = {'temperature': 1800, 'pressure': 500}
    THRESHOLDS = {'temperature': (1700, 2100), 'pressure': (450, 750)}
elif 'refinery-2' in AGENT_NAME:
    MODBUS_PORT = int(os.getenv('MODBUS_PORT', '5004'))
    REGISTERS = {'flow_rate': 40003}
    INITIAL_VALUES = {'flow_rate': 500}
    THRESHOLDS = {'flow_rate': (250, 800)}
else:
    # Generic / dynamic PLC machine configuration
    MODBUS_PORT = int(os.getenv('MODBUS_PORT', '5005'))
    REGISTERS = json.loads(os.getenv('REGISTERS_JSON', '{"process_value": 40001}'))
    INITIAL_VALUES = json.loads(os.getenv('INITIAL_VALUES_JSON', '{"process_value": 500}'))
    THRESHOLDS = json.loads(os.getenv('THRESHOLDS_JSON', '{"process_value": [100, 900]}'))

# Map register address to name for fast lookup
ADDR_TO_NAME = {addr: name for name, addr in REGISTERS.items()}
INDEX_TO_ADDR = {addr - 40001: addr for addr in REGISTERS.values()}

# ============================================================================
# LOGGING ENGINE
# ============================================================================

def init_log_directory():
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    Path(SIEM_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

def log_event(event_type, details, level="INFO", metadata=None):
    """Write structured real operational event logs."""
    timestamp = datetime.utcnow().isoformat()
    msg = f"{event_type}: {details}"
    
    # Text line format for collector: [timestamp] level - host - message
    log_line = f"[{timestamp}] {level} - {AGENT_NAME} - {msg}\n"
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_line)
    except Exception as e:
        logger.debug(f"Failed to write to {LOG_FILE}: {e}")

    # Structured JSON log line for SIEM ingestion / collector
    try:
        entry = {
            'timestamp': timestamp + 'Z',
            'level': level,
            'source': AGENT_NAME,
            'host': AGENT_NAME,
            'message': msg,
            'event_type': event_type,
            'device': {
                'hostname': AGENT_NAME,
                'device_type': 'plc',
                'metadata': metadata or {}
            }
        }
        with open(SIEM_LOG_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        logger.debug(f"Failed to write to {SIEM_LOG_FILE}: {e}")

# ============================================================================
# SIMPLE IN-MEMORY DATASTORE WITH LOGGING
# ============================================================================

class SimpleSlaveContext(ModbusBaseSlaveContext):
    """Instrumented Modbus slave context that logs real register operations."""
    
    def __init__(self):
        super().__init__()
        self.hr = {}  # Holding registers
        
        # Initialize
        for reg_name, reg_addr in REGISTERS.items():
            index = reg_addr - 40001
            self.hr[index] = INITIAL_VALUES[reg_name]
    
    def validate(self, fx, addr, quantity=1):
        return 0 <= addr < 100 and 0 < quantity <= 100
    
    def getValues(self, fx, addr, quantity=1):
        values = [self.hr.get(addr + i, 0) for i in range(quantity)]
        return values
    
    def setValues(self, fx, addr, values):
        for i, value in enumerate(values):
            curr_addr = addr + i
            old_val = self.hr.get(curr_addr)
            self.hr[curr_addr] = value
            reg_addr = INDEX_TO_ADDR.get(curr_addr, 40001 + curr_addr)
            reg_name = ADDR_TO_NAME.get(reg_addr, f'reg_{reg_addr}')
            
            if old_val is not None and old_val != value:
                # Determine if threshold breach occurs
                threshold = THRESHOLDS.get(reg_name)
                level = "INFO"
                if threshold:
                    min_val, max_val = threshold
                    if value < min_val or value > max_val:
                        level = "HIGH"
                
                log_event(
                    'MODBUS_REGISTER_WRITE',
                    f"Register {reg_addr} ({reg_name}) value updated from {old_val/10:.1f} to {value/10:.1f}",
                    level=level,
                    metadata={'register': reg_addr, 'name': reg_name, 'old_value': old_val/10.0, 'new_value': value/10.0}
                )

# ============================================================================
# PROCESS SIMULATION WITH REAL DYNAMICS
# ============================================================================

def simulate(context):
    logger.info(f"Process dynamics controller started for {AGENT_NAME}")
    log_event('PLC_PROCESS_START', f"PLC controller initialized for {AGENT_NAME} on port {MODBUS_PORT}", level="INFO")
    
    last_reported_values = {}
    
    while True:
        try:
            time.sleep(2)
            slave = context[1]
            
            for reg_name, reg_addr in REGISTERS.items():
                idx = reg_addr - 40001
                current = slave.getValues(3, idx, 1)[0]
                
                # Apply natural process fluctuations if running, keep at 0 if stopped
                if current <= 50:
                    new_val = 0
                elif 'temperature' in reg_name:
                    delta = (random.random() - 0.48) * 4.0
                    new_val = max(1500, min(2300, int(current + delta)))
                elif 'pressure' in reg_name:
                    delta = (random.random() - 0.48) * 3.0
                    new_val = max(300, min(850, int(current + delta)))
                elif 'flow' in reg_name:
                    delta = (random.random() - 0.48) * 6.0
                    new_val = max(150, min(1050, int(current + delta)))
                else:
                    delta = (random.random() - 0.48) * 2.0
                    new_val = max(0, int(current + delta))
                
                slave.setValues(3, idx, [new_val])
                
                # Check for significant state changes or threshold alerts
                prev_reported = last_reported_values.get(reg_name)
                val_change = abs(new_val - prev_reported) if prev_reported is not None else 999
                
                threshold = THRESHOLDS.get(reg_name)
                is_out_of_bounds = False
                if threshold:
                    min_v, max_v = threshold
                    if new_val < min_v or new_val > max_v:
                        is_out_of_bounds = True

                # Log real state changes when threshold is breached or value changed significantly
                if is_out_of_bounds:
                    log_event(
                        'PROCESS_THRESHOLD_ALERT',
                        f"Threshold alert: {reg_name} is {new_val/10:.1f} (operating range: {threshold[0]/10:.1f}-{threshold[1]/10:.1f})",
                        level="HIGH",
                        metadata={'register': reg_addr, 'name': reg_name, 'value': new_val/10.0, 'threshold_exceeded': True}
                    )
                    last_reported_values[reg_name] = new_val
                elif val_change >= 20 or prev_reported is None: # Significant change (>= 2.0 units)
                    log_event(
                        'PROCESS_TELEMETRY',
                        f"Operational state: {reg_name} = {new_val/10:.1f}",
                        level="INFO",
                        metadata={'register': reg_addr, 'name': reg_name, 'value': new_val/10.0}
                    )
                    last_reported_values[reg_name] = new_val
                    
        except Exception as e:
            logger.error(f"Process controller error: {e}")
            log_event('PLC_CONTROLLER_ERROR', f"Internal process error: {str(e)}", level="ERROR")
            time.sleep(5)

async def start_server(context):
    logger.info(f"Starting Modbus TCP server on port {MODBUS_PORT}")
    log_event('PLC_SERVICE_ONLINE', f"Modbus TCP listener active on 0.0.0.0:{MODBUS_PORT}", level="INFO")
    
    await StartAsyncTcpServer(
        context,
        address=('0.0.0.0', MODBUS_PORT)
    )

# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("=" * 60)
    logger.info(f"OT PLC Server: {AGENT_NAME}")
    logger.info("=" * 60)
    
    init_log_directory()
    
    # Create context and initialize
    slave = SimpleSlaveContext()
    context = ModbusServerContext(slaves={1: slave}, single=False)
    
    for name, addr in REGISTERS.items():
        val = INITIAL_VALUES[name]
        logger.info(f"Register {addr} ({name}): {val/10:.1f}")
    
    # Start simulation
    Thread(target=simulate, args=(context,), daemon=True).start()
    
    # Start server
    try:
        asyncio.run(start_server(context))
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        log_event('PLC_SERVICE_OFFLINE', f"PLC server {AGENT_NAME} shut down cleanly", level="INFO")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        log_event('PLC_FATAL_ERROR', f"Server crashed: {str(e)}", level="CRITICAL")
        exit(1)

if __name__ == '__main__':
    main()

