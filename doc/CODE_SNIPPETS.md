# GotXA — Core Code Snippets & Implementation Guide

This reference document contains production code implementations, operational commands, and integration snippets across the GotXA platform.

---

## 1. Parallel Telemetry & SIEM Ingestion (`scada_gateway.py`)

Asynchronous batch publisher with non-blocking queueing and multi-worker dispatching:

```python
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
        timestamp = datetime.utcnow().isoformat()
        event = {
            'timestamp': timestamp + 'Z',
            'level': level,
            'source': 'ot-scada-gateway',
            'host': host,
            'message': message,
            'event_type': event_type,
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

    def _batch_worker(self):
        """Worker thread draining the queue and posting batches to SIEM."""
        while self.running:
            batch = []
            try:
                item = self.queue.get(timeout=1.0)
                batch.append(item)
                while len(batch) < 50:
                    try:
                        batch.append(self.queue.get_nowait())
                    except queue.Empty:
                        break
            except queue.Empty:
                continue

            if not batch or not COLLECTOR_TOKEN:
                continue

            try:
                headers = {'X-Collector-Token': COLLECTOR_TOKEN, 'Content-Type': 'application/json'}
                self.session.post(SIEM_INGEST_URL, json={'events': batch}, headers=headers, timeout=5)
            except Exception as e:
                logger.error(f"Failed to post batch to SIEM: {e}")
```

---

## 2. Dynamic Machine Registration & Auto-Discovery

### Dynamic Registration API (`scada_gateway.py`)
```python
@app.route('/api/scada/machines/register', methods=['POST'])
def register_new_machine():
    """Dynamically register a new machine/PLC into the SCADA network."""
    body = request.get_json(silent=True) or {}
    machine_id = body.get('id')
    if not machine_id:
        return jsonify({'error': {'code': 'BadRequest', 'message': 'Machine id is required'}}), 400
    
    config = {
        'name': body.get('name', f"PLC Unit {machine_id}"),
        'host': body.get('host', f"ot-plc-{machine_id}"),
        'port': int(body.get('port', 5005)),
        'slave_id': int(body.get('slave_id', 1)),
        'poll_interval': int(body.get('poll_interval', 2)),
        'registers': body.get('registers', {'process_val': {'addr': 0, 'qty': 1, 'scale': 0.1, 'unit': 'Units'}}),
        'controls': body.get('controls', [{'command': 'emergency_stop', 'label': 'Emergency stop', 'type': 'action'}]),
        'control_state': {}
    }
    
    poller.register_machine(machine_id, config)
    return jsonify({'status': 'registered', 'machine': {'id': machine_id, **config}}), 201
```

### Dynamic File Watcher Discovery (`log_collector.py`)
```python
def discover_log_files(self):
    """Dynamically scan log base directory to discover all machine log files."""
    discovered = []
    base_path = Path(os.getenv('LOGS_BASE_DIR', LOGS_BASE_DIR))
    if not base_path.exists():
        return discovered

    for dir_entry in base_path.iterdir():
        if dir_entry.is_dir():
            dir_name = dir_entry.name
            host = self._infer_host(dir_name)
            source_type = 'corporate' if 'corp' in dir_name.lower() else 'operational'
            
            if host not in self.known_machines:
                self.known_machines.add(host)
                logger.info(f"✨ New machine discovered in logs: {host} (dir: {dir_name})")

            for log_file in dir_entry.glob('*.log'):
                if log_file.is_file():
                    discovered.append((log_file, host, source_type))
    return discovered
```

---

## 3. Real Modbus Register Operation Logging (`modbus_plc_server.py`)

```python
class SimpleSlaveContext(ModbusBaseSlaveContext):
    """Instrumented Modbus slave context logging real register write operations."""
    def setValues(self, fx, addr, values):
        for i, value in enumerate(values):
            curr_addr = addr + i
            old_val = self.hr.get(curr_addr)
            self.hr[curr_addr] = value
            reg_addr = INDEX_TO_ADDR.get(curr_addr, 40001 + curr_addr)
            reg_name = ADDR_TO_NAME.get(reg_addr, f'reg_{reg_addr}')
            
            if old_val is not None and old_val != value:
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
```

---

## 4. Automated SOAR Playbook Execution (`app/playbooks.py`)

```python
@staticmethod
def execute_ip_block(target_ip: str, reason: str) -> ActionResult:
    """Inserts an iptables DROP rule inside the container, with safety whitelisting."""
    start = time.time()
    command = f"iptables -A INPUT -s {target_ip} -j DROP"

    # Whitelist local loopback and internal container networks
    is_safe_ip = (
        target_ip == '127.0.0.1' or
        target_ip.startswith('172.24.0.') or
        target_ip.startswith('172.26.0.') or
        target_ip.startswith('172.17.0.')
    )

    if not REAL_MODE or target_ip == 'unknown-source' or is_safe_ip:
        logger.info(f"🛡️ [SOAR SIMULATED] IP Block: {command} (Reason: {reason})")
        return ActionResult(success=True, detail=f"[SIMULATED] IP Block Action: {command}", execution_time_ms=5)

    try:
        subprocess.run(["iptables", "-A", "INPUT", "-s", target_ip, "-j", "DROP"], capture_output=True, text=True, check=True)
        return ActionResult(success=True, detail=f"[REAL WORLD] IP Blocked Successfully: {command}", execution_time_ms=10)
    except Exception as e:
        return ActionResult(success=False, detail=f"Failed to apply iptables rule: {e}", execution_time_ms=10)
```

---

## 5. Useful Operational Curl Commands

### 1. Ingest Events
```bash
curl -X POST http://localhost:5000/api/ingest/events \
  -H "Content-Type: application/json" \
  -H "X-Collector-Token: $COLLECTOR_INGEST_TOKEN" \
  -d '{
    "events": [
      {
        "timestamp": "2026-09-01T01:30:00Z",
        "level": "info",
        "source": "ot-plc-refinery-1",
        "host": "ot-plc-refinery-1",
        "message": "PROCESS_TELEMETRY: temperature = 185.0",
        "device": {"hostname": "ot-plc-refinery-1", "device_type": "plc"}
      }
    ]
  }'
```

### 2. Stream Live Security Events
```bash
curl -X GET "http://localhost:5000/api/raw-stream?limit=25" \
  -H "X-User-ID: admin"
```

### 3. Register a New SCADA Machine Dynamically
```bash
curl -X POST http://localhost:5002/api/scada/machines/register \
  -H "Content-Type: application/json" \
  -d '{
    "id": "refinery-3",
    "name": "Refinery 3 Distillation Unit",
    "host": "ot-plc-refinery-3",
    "port": 5005,
    "registers": {
      "column_pressure": {"addr": 0, "qty": 1, "scale": 0.1, "unit": "bar", "threshold_high": 100}
    }
  }'
```

### 4. Query All Discovered Devices
```bash
curl -X GET http://localhost:5000/api/devices \
  -H "X-User-ID: admin"
```
