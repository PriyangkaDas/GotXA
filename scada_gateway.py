#!/usr/bin/env python3
"""
SCADA Gateway - Real-Time Modbus Polling, REST API & Parallel SIEM Ingestion
Continuously polls Modbus registers from OT PLCs, supports dynamic machine discovery,
and streams telemetry and security events in parallel to the SIEM.
"""

import json
import os
import logging
import time
import threading
import queue
from collections import deque
from datetime import datetime
from flask import Flask, jsonify, request
from pathlib import Path
import uuid
from concurrent.futures import ThreadPoolExecutor
import requests

try:
    from pymodbus.client import AsyncModbusTcpClient
    import asyncio
except ImportError as e:
    AsyncModbusTcpClient = None
    import asyncio
    logging.warning(f"pymodbus not available in local environment: {e}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SIEM_INGEST_URL = os.getenv('SIEM_INGEST_URL') or os.getenv('SIEM_INGRESS_URL') or 'http://backend:5000/api/ingest/events'
COLLECTOR_TOKEN = os.getenv('COLLECTOR_INGEST_TOKEN', '')
PLC_REFINERY_1_HOST = os.getenv('PLC_REFINERY_1_HOST', 'ot-plc-refinery-1')
PLC_REFINERY_2_HOST = os.getenv('PLC_REFINERY_2_HOST', 'ot-plc-refinery-2')

# ============================================================================
# PARALLEL HIGH-THROUGHPUT SIEM PUBLISHER
# ============================================================================

class SiemPublisher:
    """Non-blocking, parallel batch publisher for SCADA telemetry and security events."""
    def __init__(self):
        self.queue = queue.Queue(maxsize=10000)
        self.session = requests.Session()
        self.running = True
        self.worker_threads = []
        for i in range(2):
            t = threading.Thread(target=self._batch_worker, daemon=True, name=f"siem-pub-worker-{i}")
            t.start()
            self.worker_threads.append(t)

    def publish_event(self, event_type, host, message, level='info', device_meta=None, extra_meta=None):
        """Enqueue an event for asynchronous parallel transmission to SIEM."""
        device_meta = device_meta or {}
        extra_meta = extra_meta or {}
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        event = {
            'timestamp': timestamp,
            'log_source': device_meta.get('log_source') or f"SCADA_HMI_{host}" if 'hmi' in str(host).lower() else f"OT_Sensor_{host}",
            'source': 'ot-scada-gateway',
            'host': host,
            'event_type': event_type,
            'severity': level.capitalize() if level else 'Info',
            'level': level,
            'message': message,
            # OT Network & Industrial standard fields
            'src_ip': device_meta.get('src_ip', '10.50.20.14'),
            'src_mac': device_meta.get('src_mac', '00:1A:2B:3C:4D:5E'),
            'dest_ip': device_meta.get('dest_ip', '192.168.100.5' if 'refinery-1' in host else '192.168.100.6'),
            'dest_asset': device_meta.get('dest_asset', f"PLC_{host.replace('ot-plc-', '').replace('-', '_').upper()}"),
            'protocol': device_meta.get('protocol', 'ModbusTCP'),
            'action': device_meta.get('action', event_type),
            # MITRE ICS Mappings
            'mitre_ics_tactic': device_meta.get('mitre_ics_tactic', 'TA0104' if 'command' in event_type.lower() else 'TA0105'),
            'mitre_ics_technique': device_meta.get('mitre_ics_technique', 'T855' if 'command' in event_type.lower() else 'T836'),
            # SCADA HMI Audit standard fields
            'user': device_meta.get('user') or device_meta.get('actor') or 'operator_console',
            'session_id': device_meta.get('session_id', 'HMI-SESS-992B'),
            'tag_name': device_meta.get('tag_name') or device_meta.get('metric') or 'Process_Value',
            'previous_value': str(device_meta.get('previous_value', '')),
            'new_value': str(device_meta.get('value') or device_meta.get('new_value', '')),
            'process_area': device_meta.get('process_area', 'Refinery_Process_Zone_1' if 'refinery-1' in host else 'Refinery_Process_Zone_2'),
            'device': {
                'hostname': host,
                'device_type': 'plc' if 'plc' in host.lower() else 'scada',
                'metadata': {
                    'reported_by': 'ot-scada-gateway',
                    **(device_meta or {}),
                    **(extra_meta or {})
                }
            }
        }
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            logger.warning("SIEM publisher queue full - dropping event")

    def publish_change(self, machine_id, metric, value, timestamp, previous_value=None):
        host = f"ot-plc-{machine_id}"
        self.publish_event(
            event_type='PLC_State_Change',
            host=host,
            message=f"OT Process Telemetry: {machine_id} tag '{metric}' updated to {value}",
            level='info',
            device_meta={
                'log_source': f"OT_Sensor_{machine_id.replace('-', '_')}",
                'machine_id': machine_id,
                'metric': metric,
                'tag_name': f"{machine_id}_{metric}".upper(),
                'previous_value': previous_value or (value - 0.5 if isinstance(value, (int, float)) else value),
                'value': value,
                'new_value': value,
                'action': 'Telemetry_Update',
                'dest_asset': f"PLC_{machine_id.replace('-', '_').upper()}",
                'protocol': 'ModbusTCP',
                'mitre_ics_tactic': 'TA0105',
                'mitre_ics_technique': 'T836'
            }
        )

    def publish_command(self, machine_id, command, value, reason, status, actor):
        host = f"ot-plc-{machine_id}"
        level = 'critical' if command == 'emergency_stop' else ('high' if status == 'rejected' else 'info')
        mitre_technique = 'T803' if command == 'emergency_stop' else ('T855' if status == 'rejected' else 'T836')
        self.publish_event(
            event_type='Command_Execution',
            host=host,
            message=f"SCADA HMI / OT Command: Operator '{actor}' executed {command}={value} on {machine_id} (Status: {status}, Reason: {reason})",
            level=level,
            device_meta={
                'log_source': f"SCADA_HMI_Node_{machine_id.replace('-', '_')}",
                'machine_id': machine_id,
                'command': command,
                'action': command,
                'value': value,
                'new_value': value,
                'user': actor,
                'actor': actor,
                'status': status,
                'tag_name': f"{machine_id}_{command}".upper(),
                'dest_asset': f"PLC_{machine_id.replace('-', '_').upper()}",
                'protocol': 'ModbusTCP',
                'mitre_ics_tactic': 'TA0104',
                'mitre_ics_technique': mitre_technique,
                'process_area': 'Refinery_Process_Zone_1' if '1' in machine_id else 'Refinery_Process_Zone_2'
            }
        )

    def publish_alarm(self, alarm_id, machine_id, metric, status, message, severity):
        host = f"ot-plc-{machine_id}"
        self.publish_event(
            event_type='Alarm_Event',
            host=host,
            message=f"OT Process Alarm [{alarm_id}] on {machine_id} {metric}: {message} (State: {status})",
            level=severity.lower(),
            device_meta={
                'log_source': f"OT_Sensor_{machine_id.replace('-', '_')}",
                'alarm_id': alarm_id,
                'machine_id': machine_id,
                'metric': metric,
                'tag_name': f"{machine_id}_{metric}".upper(),
                'status': status,
                'action': 'Threshold_Breach',
                'dest_asset': f"PLC_{machine_id.replace('-', '_').upper()}",
                'protocol': 'ModbusTCP',
                'mitre_ics_tactic': 'TA0108',
                'mitre_ics_technique': 'T803'
            }
        )

    def publish_machine_discovered(self, machine_id, name, host, port):
        self.publish_event(
            event_type='New_Asset_Detection',
            host=host,
            message=f"New industrial asset discovered on OT network segment: {name} ({machine_id}) at {host}:{port}",
            level='warn',
            device_meta={
                'log_source': 'OT_Sensor_Discovery',
                'machine_id': machine_id,
                'name': name,
                'host': host,
                'dest_ip': host,
                'dest_asset': name,
                'port': port,
                'action': 'Asset_Registered',
                'protocol': 'ModbusTCP',
                'mitre_ics_tactic': 'TA0102',
                'mitre_ics_technique': 'T846'
            }
        )

    def _batch_worker(self):
        """Worker thread that drains the queue and posts batches to SIEM."""
        while self.running:
            batch = []
            try:
                # Wait for at least one item
                item = self.queue.get(timeout=1.0)
                batch.append(item)
                # Drain additional items up to batch size 50
                while len(batch) < 50:
                    try:
                        batch.append(self.queue.get_nowait())
                    except queue.Empty:
                        break
            except queue.Empty:
                continue

            if not batch:
                continue

            try:
                headers = {'Content-Type': 'application/json'}
                if COLLECTOR_TOKEN:
                    headers['X-Collector-Token'] = COLLECTOR_TOKEN
                response = self.session.post(SIEM_INGEST_URL, json={'events': batch}, headers=headers, timeout=5)
                if response.status_code not in (200, 202):
                    logger.warning(f"SIEM ingestion returned status {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to post batch to SIEM: {e}")

siem_publisher = SiemPublisher()

# ============================================================================
# FLASK APPLICATION
# ============================================================================

app = Flask(__name__)

# ============================================================================
# DYNAMIC MACHINE REGISTRY & MODBUS POLLING ENGINE
# ============================================================================

CONTROL_LOCK = threading.Lock()
COMMANDS = {}
AUDIT_LOG = deque(maxlen=500)
ALARMS = {}

DEFAULT_MACHINES = {
    'refinery-1': {
        'name': 'Refinery 1 Heater',
        'host': PLC_REFINERY_1_HOST,
        'port': 5003,
        'slave_id': 1,
        'poll_interval': 2,
        'registers': {
            'temperature': {'addr': 0, 'qty': 1, 'scale': 0.1, 'unit': '°C', 'threshold_high': 210, 'threshold_low': 150},
            'pressure': {'addr': 1, 'qty': 1, 'scale': 0.1, 'unit': 'PSI', 'threshold_high': 75, 'threshold_low': 35}
        },
        'controls': [
            {'command': 'set_temperature', 'label': 'Temperature setpoint', 'min': 150, 'max': 220, 'unit': '°C', 'reg_addr': 0},
            {'command': 'set_heater_enabled', 'label': 'Heater enabled', 'type': 'toggle'},
            {'command': 'emergency_stop', 'label': 'Emergency stop', 'type': 'action'},
            {'command': 'reset_emergency_stop', 'label': 'Reset emergency stop', 'type': 'action'},
        ],
        'control_state': {'heater_enabled': True, 'emergency_stopped': False}
    },
    'refinery-2': {
        'name': 'Refinery 2 Flow Unit',
        'host': PLC_REFINERY_2_HOST,
        'port': 5004,
        'slave_id': 1,
        'poll_interval': 2,
        'registers': {
            'flow_rate': {'addr': 2, 'qty': 1, 'scale': 0.1, 'unit': 'L/min', 'threshold_high': 95, 'threshold_low': 25}
        },
        'controls': [
            {'command': 'set_flow_rate', 'label': 'Flow-rate setpoint', 'min': 20, 'max': 100, 'unit': 'L/min', 'reg_addr': 2},
            {'command': 'set_pump_enabled', 'label': 'Pump enabled', 'type': 'toggle'},
            {'command': 'emergency_stop', 'label': 'Emergency stop', 'type': 'action'},
            {'command': 'reset_emergency_stop', 'label': 'Reset emergency stop', 'type': 'action'},
        ],
        'control_state': {'pump_enabled': True, 'emergency_stopped': False}
    },
}

class ModbusPoller:
    """Dynamic multi-machine Modbus polling engine."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.machines = json.loads(json.dumps(DEFAULT_MACHINES))
        self.data = {}
        self.history = {}
        self.active_tasks = {}
        self.event_loop = None

        for machine_id, config in self.machines.items():
            self._init_machine_structures(machine_id, config)

    def _init_machine_structures(self, machine_id, config):
        key = machine_id.replace('-', '_')
        initial_data = {'status': 'offline', 'last_update': None}
        for reg_name in config.get('registers', {}):
            initial_data[reg_name] = 0.0
        self.data[key] = initial_data
        self.data[machine_id] = initial_data

        if machine_id not in self.history:
            self.history[machine_id] = {reg_name: deque(maxlen=900) for reg_name in config.get('registers', {})}

    def _record(self, machine_id, metric, value, timestamp):
        history = self.history.get(machine_id, {}).get(metric)
        if history is None:
            return
        previous = history[-1]['value'] if history else None
        history.append({'timestamp': timestamp, 'value': value})
        if previous != value:
            siem_publisher.publish_change(machine_id, metric, value, timestamp)

    def get_data(self):
        with self.lock:
            return json.loads(json.dumps(self.data))

    def get_history(self, machine_id, metric):
        with self.lock:
            return list(self.history.get(machine_id, {}).get(metric, []))

    def register_machine(self, machine_id, config):
        """Dynamically add or update a machine at runtime and spawn polling."""
        with self.lock:
            self.machines[machine_id] = config
            self._init_machine_structures(machine_id, config)
        
        siem_publisher.publish_machine_discovered(
            machine_id=machine_id,
            name=config.get('name', machine_id),
            host=config.get('host', machine_id),
            port=config.get('port', 5002)
        )

        # Spawn polling task if loop is running
        if self.event_loop and self.event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.poll_machine(machine_id), self.event_loop)
            logger.info(f"Dynamically spawned poller for new machine: {machine_id}")

    async def poll_machine(self, machine_id):
        """Asynchronously poll registers for a specific machine."""
        config = self.machines[machine_id]
        host = config.get('host', 'localhost')
        port = config.get('port', 5003)
        slave_id = config.get('slave_id', 1)
        poll_interval = config.get('poll_interval', 2)
        key = machine_id.replace('-', '_')

        last_status = None

        while True:
            try:
                client = AsyncModbusTcpClient(host=host, port=port)
                await client.connect()
                
                if client.connected:
                    logger.info(f"Connected to PLC machine {machine_id} ({host}:{port})")
                    if last_status != 'online':
                        last_status = 'online'
                        siem_publisher.publish_event(
                            'SCADA_PLC_ONLINE', f"ot-plc-{machine_id}",
                            f"PLC connection established for {machine_id} on {host}:{port}",
                            level='info'
                        )

                while client.connected:
                    try:
                        timestamp = datetime.utcnow().isoformat()
                        updates = {}
                        has_error = False

                        for reg_name, reg_info in config.get('registers', {}).items():
                            addr = reg_info.get('addr', 0)
                            qty = reg_info.get('qty', 1)
                            scale = reg_info.get('scale', 0.1)

                            result = await client.read_holding_registers(addr, qty, slave=slave_id)
                            if not result.isError():
                                val = round(result.registers[0] * scale, 2)
                                updates[reg_name] = val
                                self._record(machine_id, reg_name, val, timestamp)
                            else:
                                has_error = True
                                logger.warning(f"Error reading {machine_id} register {reg_name} (addr {addr})")

                        with self.lock:
                            is_stopped = self.machines.get(machine_id, {}).get('control_state', {}).get('emergency_stopped', False)
                            status = 'stopped' if is_stopped else ('error' if has_error else 'online')
                            self.data[key].update(updates)
                            self.data[key]['last_update'] = timestamp
                            self.data[key]['status'] = status
                            self.data[key]['emergency_stopped'] = is_stopped

                            self.data[machine_id].update(updates)
                            self.data[machine_id]['last_update'] = timestamp
                            self.data[machine_id]['status'] = status
                            self.data[machine_id]['emergency_stopped'] = is_stopped

                        await asyncio.sleep(poll_interval)

                    except Exception as e:
                        logger.error(f"Polling cycle error for {machine_id}: {e}")
                        with self.lock:
                            self.data[key]['status'] = 'error'
                            self.data[machine_id]['status'] = 'error'
                        break

                client.close()

            except Exception as e:
                logger.debug(f"PLC {machine_id} connection error: {e}")
                with self.lock:
                    self.data[key]['status'] = 'offline'
                    self.data[machine_id]['status'] = 'offline'
                if last_status != 'offline':
                    last_status = 'offline'
                    siem_publisher.publish_event(
                        'SCADA_PLC_OFFLINE', f"ot-plc-{machine_id}",
                        f"PLC connection unreachable for {machine_id} on {host}:{port}",
                        level='warn'
                    )
                await asyncio.sleep(5)

poller = ModbusPoller()

def machine_status(machine_id):
    data = poller.get_data()
    key = machine_id.replace('-', '_')
    res = data.get(key) or data.get(machine_id) or {'status': 'offline', 'last_update': None}
    if poller.machines.get(machine_id, {}).get('control_state', {}).get('emergency_stopped'):
        res['status'] = 'stopped'
        res['emergency_stopped'] = True
    return res

def refresh_alarms():
    """Inspect all registered machine telemetry against configured thresholds."""
    with CONTROL_LOCK:
        for machine_id, config in poller.machines.items():
            status = machine_status(machine_id)
            for reg_name, reg_info in config.get('registers', {}).items():
                val = status.get(reg_name)
                if val is None:
                    continue

                th_high = reg_info.get('threshold_high')
                th_low = reg_info.get('threshold_low')

                if th_high is not None:
                    alarm_id = f"{machine_id}-{reg_name}-high"
                    active = val > th_high
                    if active and alarm_id not in ALARMS:
                        alarm = {
                            'id': alarm_id, 'machine_id': machine_id, 'metric': reg_name,
                            'severity': 'high', 'message': f'{reg_name} high threshold ({th_high}) exceeded: {val}',
                            'raised_at': datetime.utcnow().isoformat(), 'status': 'active'
                        }
                        ALARMS[alarm_id] = alarm
                        siem_publisher.publish_alarm(alarm_id, machine_id, reg_name, 'active', alarm['message'], 'high')
                    elif not active and alarm_id in ALARMS and ALARMS[alarm_id]['status'] == 'active':
                        ALARMS[alarm_id]['status'] = 'cleared'
                        siem_publisher.publish_alarm(alarm_id, machine_id, reg_name, 'cleared', f'{reg_name} returned to normal: {val}', 'info')

                if th_low is not None:
                    alarm_id = f"{machine_id}-{reg_name}-low"
                    active = val < th_low
                    if active and alarm_id not in ALARMS:
                        alarm = {
                            'id': alarm_id, 'machine_id': machine_id, 'metric': reg_name,
                            'severity': 'high', 'message': f'{reg_name} low threshold ({th_low}) breached: {val}',
                            'raised_at': datetime.utcnow().isoformat(), 'status': 'active'
                        }
                        ALARMS[alarm_id] = alarm
                        siem_publisher.publish_alarm(alarm_id, machine_id, reg_name, 'active', alarm['message'], 'high')
                    elif not active and alarm_id in ALARMS and ALARMS[alarm_id]['status'] == 'active':
                        ALARMS[alarm_id]['status'] = 'cleared'
                        siem_publisher.publish_alarm(alarm_id, machine_id, reg_name, 'cleared', f'{reg_name} returned to normal: {val}', 'info')

async def write_machine_register(machine_id, reg_addr, value):
    config = poller.machines.get(machine_id)
    if not config:
        raise RuntimeError(f"Machine {machine_id} not configured")
    host = config.get('host', 'localhost')
    port = config.get('port', 5003)
    slave_id = config.get('slave_id', 1)

    client = AsyncModbusTcpClient(host=host, port=port)
    await client.connect()
    if not client.connected:
        raise RuntimeError(f"PLC {machine_id} connection unavailable at {host}:{port}")
    try:
        result = await client.write_register(reg_addr, int(value * 10), slave=slave_id)
        if result.isError():
            raise RuntimeError('PLC rejected the register write')
    finally:
        client.close()

def record_command(machine_id, command, value, reason, status, rejection_reason=None):
    command_id = str(uuid.uuid4())
    actor = request.headers.get('X-Operator', 'anonymous-operator')
    entry = {
        'command_id': command_id, 'machine_id': machine_id, 'command': command,
        'value': value, 'reason': reason, 'actor': actor,
        'requested_at': datetime.utcnow().isoformat(), 'status': status,
    }
    if status == 'applied':
        entry['applied_at'] = datetime.utcnow().isoformat()
    if rejection_reason:
        entry['rejection_reason'] = rejection_reason
    with CONTROL_LOCK:
        COMMANDS[command_id] = entry
        AUDIT_LOG.appendleft(entry)
    
    siem_publisher.publish_command(machine_id, command, value, reason, status, actor)
    return entry

def start_polling():
    """Start async polling engine in a dedicated background event loop."""
    def polling_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        poller.event_loop = loop
        
        # Gather all current machine pollers
        tasks = [poller.poll_machine(m_id) for m_id in poller.machines]
        loop.run_until_complete(asyncio.gather(*tasks))
    
    thread = threading.Thread(target=polling_thread, daemon=True, name="scada-polling-engine")
    thread.start()
    logger.info("Started SCADA dynamic Modbus polling engine")

# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.route('/api/modbus', methods=['GET'])
def get_modbus_data():
    """Get current Modbus register values for all machines."""
    try:
        data = poller.get_data()
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error in /api/modbus: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/modbus/<machine_id>', methods=['GET'])
def get_machine_modbus(machine_id):
    """Get telemetry data for a specific machine."""
    try:
        data = poller.get_data()
        key = machine_id.replace('-', '_')
        result = data.get(key) or data.get(machine_id)
        if not result:
            return jsonify({"error": "Machine not found"}), 404
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in /api/modbus/{machine_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scada/machines', methods=['GET'])
def list_machines():
    """List all machines, live statuses, and controls."""
    refresh_alarms()
    items = []
    for machine_id, definition in poller.machines.items():
        st = machine_status(machine_id)
        items.append({
            'id': machine_id,
            'name': definition.get('name', machine_id),
            'controls': definition.get('controls', []),
            'status': st.get('status', 'online'),
            'telemetry': st,
            'control_state': definition.get('control_state', {})
        })
    return jsonify({'items': items})

@app.route('/api/scada/machines/register', methods=['POST'])
def register_new_machine():
    """Dynamically register a new machine/PLC into the SCADA network."""
    body = request.get_json(silent=True) or {}
    machine_id = body.get('id')
    if not machine_id:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'Machine id is required'}}), 400
    
    name = body.get('name', f"PLC Unit {machine_id}")
    host = body.get('host', f"ot-plc-{machine_id}")
    port = int(body.get('port', 5005))
    registers = body.get('registers', {'process_val': {'addr': 0, 'qty': 1, 'scale': 0.1, 'unit': 'Units'}})
    controls = body.get('controls', [{'command': 'emergency_stop', 'label': 'Emergency stop', 'type': 'action'}])
    
    config = {
        'name': name,
        'host': host,
        'port': port,
        'slave_id': int(body.get('slave_id', 1)),
        'poll_interval': int(body.get('poll_interval', 2)),
        'registers': registers,
        'controls': controls,
        'control_state': {}
    }
    
    poller.register_machine(machine_id, config)
    return jsonify({
        'status': 'registered',
        'machine': {'id': machine_id, **config}
    }), 201

@app.route('/api/scada/machines/<machine_id>/commands', methods=['POST'])
def submit_command(machine_id):
    """Validate, apply, and audit a SCADA command."""
    if machine_id not in poller.machines:
        return jsonify({'error': {'code': 'NotFound', 'message': 'Machine not found'}}), 404
    
    body = request.get_json(silent=True) or {}
    command = body.get('command')
    value = body.get('value')
    reason = body.get('reason', '')
    
    machine_def = poller.machines[machine_id]
    allowed = {control['command']: control for control in machine_def.get('controls', [])}
    if command not in allowed:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'Unsupported command'}}), 400
    if command == 'emergency_stop' and not reason:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'A reason is required for emergency stop'}}), 400

    try:
        control = allowed[command]
        if 'min' in control and 'max' in control:
            value = float(value)
            if not (control['min'] <= value <= control['max']):
                entry = record_command(machine_id, command, value, reason, 'rejected', 'Value outside allowed operating range')
                return jsonify(entry), 422
            
            reg_addr = control.get('reg_addr', 0)
            asyncio.run(write_machine_register(machine_id, reg_addr, value))
        elif control.get('type') == 'toggle':
            if not isinstance(value, bool):
                return jsonify({'error': {'code': 'BadRequest', 'message': 'Toggle value must be boolean'}}), 400
            with CONTROL_LOCK:
                machine_def.setdefault('control_state', {})[command] = value
                clean_key = command.replace('set_', '')
                machine_def.setdefault('control_state', {})[clean_key] = value
        elif command == 'emergency_stop':
            asyncio.run(write_machine_register(machine_id, 0, 0))
            with CONTROL_LOCK:
                machine_def.setdefault('control_state', {})['emergency_stopped'] = True
            with poller.lock:
                key = machine_id.replace('-', '_')
                poller.data[key]['status'] = 'stopped'
                poller.data[key]['emergency_stopped'] = True
                poller.data[machine_id]['status'] = 'stopped'
                poller.data[machine_id]['emergency_stopped'] = True
        elif command == 'reset_emergency_stop':
            with CONTROL_LOCK:
                machine_def.setdefault('control_state', {})['emergency_stopped'] = False
            with poller.lock:
                key = machine_id.replace('-', '_')
                poller.data[key]['status'] = 'online'
                poller.data[key]['emergency_stopped'] = False
                poller.data[machine_id]['status'] = 'online'
                poller.data[machine_id]['emergency_stopped'] = False

        entry = record_command(machine_id, command, value, reason, 'applied')
        return jsonify(entry), 202
    except Exception as exc:
        logger.error(f"SCADA command error: {exc}")
        entry = record_command(machine_id, command, value, reason, 'rejected', str(exc))
        return jsonify(entry), 503

@app.route('/api/control', methods=['POST'])
def scada_generic_control():
    """Generic control endpoint compatible with backend proxy."""
    body = request.get_json(silent=True) or {}
    machine_id = body.get('machine_id', 'refinery-1')
    return submit_command(machine_id)

@app.route('/api/scada/commands/<command_id>', methods=['GET'])
def get_command(command_id):
    with CONTROL_LOCK:
        entry = COMMANDS.get(command_id)
    if not entry:
        return jsonify({'error': {'code': 'NotFound', 'message': 'Command not found'}}), 404
    return jsonify(entry)

@app.route('/api/scada/machines/<machine_id>/history', methods=['GET'])
def machine_history(machine_id):
    if machine_id not in poller.machines:
        return jsonify({'error': {'code': 'NotFound', 'message': 'Machine not found'}}), 404
    metric = request.args.get('metric')
    valid_metrics = set(poller.machines[machine_id].get('registers', {}).keys())
    if metric not in valid_metrics:
        return jsonify({'error': {'code': 'BadRequest', 'message': f'metric is required and must be one of {list(valid_metrics)}'}}), 400
    return jsonify({'machine_id': machine_id, 'metric': metric, 'samples': poller.get_history(machine_id, metric)})

@app.route('/api/scada/alarms', methods=['GET'])
def list_alarms():
    refresh_alarms()
    with CONTROL_LOCK:
        items = list(ALARMS.values())
    return jsonify({'items': items})

@app.route('/api/scada/alarms/<alarm_id>/acknowledge', methods=['POST'])
def acknowledge_alarm(alarm_id):
    body = request.get_json(silent=True) or {}
    with CONTROL_LOCK:
        alarm = ALARMS.get(alarm_id)
        if not alarm:
            return jsonify({'error': {'code': 'NotFound', 'message': 'Alarm not found'}}), 404
        alarm['status'] = 'acknowledged'
        alarm['acknowledged_at'] = datetime.utcnow().isoformat()
        actor = request.headers.get('X-Operator', 'anonymous-operator')
        alarm['acknowledged_by'] = actor
        alarm['note'] = body.get('note', '')
        siem_publisher.publish_alarm(
            alarm_id=alarm_id,
            machine_id=alarm.get('machine_id', 'unknown'),
            metric=alarm.get('metric', ''),
            status='acknowledged',
            message=f"Alarm acknowledged by {actor}: {alarm['note']}",
            severity='info'
        )
        return jsonify(alarm)

@app.route('/api/scada/audit', methods=['GET'])
def control_audit():
    machine_id = request.args.get('machine_id')
    with CONTROL_LOCK:
        items = [item for item in AUDIT_LOG if not machine_id or item['machine_id'] == machine_id]
    return jsonify({'items': items})

@app.route('/health', methods=['GET'])
def health():
    data = poller.get_data()
    is_any_online = any(m.get('status') == 'online' for m in data.values() if isinstance(m, dict))
    status = 'healthy' if is_any_online else 'degraded'
    return jsonify({
        "status": status,
        "service": "scada-gateway",
        "machines_count": len(poller.machines),
        "machines": {m_id: poller.data.get(m_id, {}).get('status', 'unknown') for m_id in poller.machines}
    }), 200

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🏢 SCADA Gateway - Dynamic Modbus Engine & Parallel SIEM Ingestion")
    logger.info("=" * 70)
    
    start_polling()
    time.sleep(2)
    
    logger.info("Starting SCADA Gateway HTTP Server on port 5002")
    app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)
