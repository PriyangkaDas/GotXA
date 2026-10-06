#!/usr/bin/env python3
"""
Log Collector with Real-Time Dashboard (FIXED)
Correct log delimiter: ] (not ]:]
"""

import os, sys, time, json, logging, requests, threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from collections import deque
from flask import Flask, jsonify, render_template_string
from werkzeug.serving import make_server

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SIEM_INGRESS_URL = os.getenv('SIEM_INGRESS_URL', 'http://backend:5000/api/ingest/events')
COLLECTOR_TOKEN = os.getenv('COLLECTOR_INGEST_TOKEN', '')
COLLECTOR_PORT = int(os.getenv('COLLECTOR_PORT', '5006'))
LOG_DIRS = ['/logs/corp-portal', '/logs/corp-database', '/logs/corp-workstation', '/logs/ot-scada', '/logs/ot-plc-1', '/logs/ot-plc-2']

raw_log_buffer = deque(maxlen=500)
buffer_lock = threading.Lock()

app = Flask(__name__)

DASHBOARD_HTML = r'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>🔍 Raw Log Stream</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Courier New',monospace;background:#0a0e27;color:#00ff88;height:100vh;overflow:hidden}.container{display:flex;flex-direction:column;height:100vh}.header{background:#1a1f3a;border-bottom:2px solid #00ff88;padding:12px 16px;display:flex;justify-content:space-between;align-items:center}.header h1{font-size:1.3em;letter-spacing:2px;text-shadow:0 0 10px #00ff88}.controls{display:flex;gap:10px;align-items:center}button{background:#00ff88;color:#0a0e27;border:none;padding:8px 16px;border-radius:4px;font-weight:bold;cursor:pointer;font-size:0.9em}button:hover{background:#00dd77;box-shadow:0 0 10px #00ff88}.toggle-label{color:#00ff88;display:flex;align-items:center;gap:8px;font-size:0.9em}input[type="checkbox"]{accent-color:#00ff88}.status{color:#00ff88;font-size:0.85em;display:flex;align-items:center;gap:6px}.status-dot{width:10px;height:10px;background:#00ff88;border-radius:50%;animation:pulse 1.5s infinite}@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}.log-container{flex:1;overflow-y:auto;background:#0a0e27;padding:16px;line-height:1.5}.log-entry{background:rgba(0,255,136,0.05);border-left:3px solid #00ff88;padding:10px 12px;margin-bottom:8px;border-radius:2px;font-size:0.95em;white-space:pre-wrap;word-break:break-all}.log-entry:hover{background:rgba(0,255,136,0.1)}.log-entry.highlight{border-left-color:#ff4444;background:rgba(255,68,68,0.05)}.json-key{color:#00ff88;font-weight:bold}.json-string{color:#ffaa00}.json-number{color:#ff55ff}.json-boolean{color:#55aaff}.empty-state{display:flex;align-items:center;justify-content:center;height:100%;color:#004400;font-size:1.2em;text-align:center;flex-direction:column;gap:12px}.spinner{width:20px;height:20px;border:2px solid #00664400;border-top-color:#00ff88;border-radius:50%;animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.stats{font-size:0.85em;color:#00aa66;margin-right:12px}.log-container::-webkit-scrollbar{width:8px}.log-container::-webkit-scrollbar-track{background:#0a0e27}.log-container::-webkit-scrollbar-thumb{background:#00ff88;border-radius:4px}</style></head><body><div class="container"><div class="header"><div><h1>🔍 RAW LOG STREAM</h1></div><div class="controls"><div class="stats">Logs: <span id="log-count">0</span></div><label class="toggle-label"><input type="checkbox" id="auto-scroll" checked>Auto-Scroll</label><button onclick="togglePause()">▶ Pause</button><button onclick="clearScreen()">Clear</button><div class="status"><div class="status-dot"></div><span>STREAMING</span></div></div></div><div class="log-container" id="log-container"><div class="empty-state"><div class="spinner"></div><div>[SYSTEM READY] Waiting for incoming telemetry...</div></div></div></div><script>let isPaused=false,autoScroll=true,lastLogCount=0,emptyStateShown=true;const container=document.getElementById('log-container'),countEl=document.getElementById('log-count'),emptyEl=container.querySelector('.empty-state');async function updateLogs(){if(isPaused)return;try{const r=await fetch('/api/raw-stream'),logs=await r.json();if(countEl.textContent=logs.length,logs.length===0){if(!emptyStateShown){container.innerHTML='';emptyEl.style.display='flex';container.appendChild(emptyEl);emptyStateShown=true}return}if(emptyStateShown&&(container.innerHTML='',emptyStateShown=false),logs.length>lastLogCount){logs.slice(lastLogCount).forEach(log=>{const e=document.createElement('div');e.className='log-entry',('ERROR'===log.level||'HIGH'===log.level)&&e.classList.add('highlight'),e.innerHTML=highlight(JSON.stringify(log,null,2)),container.appendChild(e)})}lastLogCount=logs.length,autoScroll&&(container.scrollTop=container.scrollHeight)}catch(e){console.error('Error:',e)}}function highlight(json){return(json=json.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')).replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,m=>{let c='json-number';return/^"/.test(m)&&(c=/:$/.test(m)?'json-key':'json-string'),/true|false/.test(m)&&(c='json-boolean'),/null/.test(m)&&(c='json-null'),'<span class="'+c+'">'+m+'</span>'})}function togglePause(){isPaused=!isPaused}function clearScreen(){container.innerHTML='',lastLogCount=0,countEl.textContent='0',emptyStateShown=true}document.getElementById('auto-scroll').addEventListener('change',e=>{autoScroll=e.target.checked}),setInterval(updateLogs,2000),updateLogs()</script></body></html>'''

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/raw-stream')
def get_raw_stream():
    try:
        with buffer_lock:
            return jsonify(list(raw_log_buffer))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ====== DYNAMIC LOG COLLECTION & PARALLEL PROCESSING ======

LOGS_BASE_DIR = os.getenv('LOGS_BASE_DIR', '/logs')
DEFAULT_LOG_DIRS = [
    '/logs/corp-portal', '/logs/corp-database', '/logs/corp-workstation',
    '/logs/ot-scada', '/logs/ot-plc-1', '/logs/ot-plc-2'
]

class ParallelLogCollector:
    """Multi-threaded dynamic log collector that auto-detects new machines and files."""
    
    def __init__(self):
        self.offsets = {}
        self.lock = threading.Lock()
        self.buffer = deque(maxlen=5000)
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="log-collect-worker")
        self.known_machines = set()
        self.session = requests.Session()
    
    def run(self):
        logger.info("💾 Dynamic Parallel Log Collector started")
        
        # Start background flusher thread
        flusher_thread = threading.Thread(target=self._flusher_loop, daemon=True, name="siem-flusher")
        flusher_thread.start()

        while True:
            try:
                log_files = self.discover_log_files()
                
                # Process discovered log files concurrently
                futures = [self.executor.submit(self.process_log_file, path, host, source_type)
                           for path, host, source_type in log_files]
                
                # Wait for all files to be read in this iteration
                for f in futures:
                    try:
                        f.result(timeout=10)
                    except Exception as exc:
                        logger.error(f"Worker task error: {exc}")
                
            except Exception as e:
                logger.error(f"Collector cycle error: {e}", exc_info=True)
            
            time.sleep(2)

    def discover_log_files(self):
        """Dynamically scan log base directory to discover all machine log files."""
        discovered = []
        base_path = Path(os.getenv('LOGS_BASE_DIR', LOGS_BASE_DIR))
        
        if not base_path.exists():
            return discovered

        # Scan for direct log files in /logs/ (e.g., ot-instrumentation.log)
        try:
            for p in base_path.glob('*.log'):
                if p.is_file():
                    host = p.stem
                    source_type = 'operational' if 'ot' in host.lower() else 'corporate'
                    discovered.append((p, host, source_type))
        except Exception as e:
            logger.debug(f"Error scanning root log files: {e}")

        # Scan for machine directories in /logs/*/
        try:
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
        except Exception as e:
            logger.debug(f"Error scanning machine directories: {e}")

        return discovered

    def _infer_host(self, dir_name):
        """Map directory name to canonical host name."""
        name = dir_name.lower()
        if 'corp-portal' in name: return 'corp-portal-agent'
        if 'corp-database' in name or 'corp-db' in name: return 'corp-database-agent'
        if 'corp-workstation' in name: return 'corp-workstation-agent'
        if 'ot-scada' in name: return 'ot-scada-gateway'
        if 'ot-plc-1' in name or 'refinery-1' in name: return 'ot-plc-refinery-1'
        if 'ot-plc-2' in name or 'refinery-2' in name: return 'ot-plc-refinery-2'
        if name.startswith('ot-') or name.startswith('corp-'): return name
        if 'plc' in name: return f"ot-{name}"
        return name

    def process_log_file(self, log_path, host, source_type):
        """Read newly appended lines from a single log file."""
        key = str(log_path)
        offset = self.offsets.get(key, 0)

        try:
            if not log_path.exists():
                return
            
            file_size = log_path.stat().st_size
            if offset > file_size:
                logger.info(f"ℹ️ File truncated: {log_path} (offset {offset} > size {file_size}). Resetting.")
                offset = 0

            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(offset)
                lines = f.readlines()
                new_offset = f.tell()

            self.offsets[key] = new_offset

            if not lines:
                return

            parsed_entries = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                entry = self._parse_line(line, host, source_type)
                if entry:
                    parsed_entries.append(entry)

            if parsed_entries:
                with self.lock:
                    self.buffer.extend(parsed_entries)
                with buffer_lock:
                    raw_log_buffer.extend(parsed_entries)
                logger.info(f"✓ Read {len(parsed_entries)} logs from {host} ({log_path.name})")

        except Exception as e:
            logger.error(f"Error processing {log_path}: {e}")

    def _parse_line(self, line, default_host, source_type):
        """Robust parser supporting JSON lines and structured log formats."""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Try parsing JSON log format
        if line.startswith('{') and line.endswith('}'):
            try:
                data = json.loads(line)
                ts = data.get('timestamp') or timestamp
                level = str(data.get('level', 'INFO')).upper()
                msg = data.get('message') or str(data)
                host = data.get('host') or data.get('source') or default_host
                device_info = data.get('device') or {
                    'hostname': host,
                    'device_type': 'plc' if 'plc' in host.lower() else ('scada' if 'scada' in host.lower() else 'server')
                }
                return {
                    'timestamp': ts,
                    'level': level,
                    'message': msg,
                    'host': host,
                    'source_type': source_type,
                    'device': device_info
                }
            except Exception:
                pass

        # 2. Try parsing [timestamp] Level - Host - Message
        if line.startswith('['):
            try:
                closing_idx = line.find(']')
                if closing_idx != -1:
                    ts = line[1:closing_idx].strip()
                    remainder = line[closing_idx + 1:].strip()
                    
                    level = 'INFO'
                    host = default_host
                    msg = remainder

                    if ' - ' in remainder:
                        parts = remainder.split(' - ', 2)
                        if len(parts) == 3:
                            level, host, msg = parts[0].strip().upper(), parts[1].strip(), parts[2].strip()
                        elif len(parts) == 2:
                            level, msg = parts[0].strip().upper(), parts[1].strip()
                    elif ': ' in remainder:
                        parts = remainder.split(': ', 1)
                        atype, details = parts[0].strip(), parts[1].strip()
                        severity = 'HIGH' if any(x in atype.upper() for x in ['ERROR', 'FAILURE', 'INJECTION', 'COMMAND', 'ALERT', 'CRITICAL']) else ('MEDIUM' if any(x in atype.upper() for x in ['AUTH', 'SQL', 'WARN']) else 'LOW')
                        level = severity
                        msg = f"{atype}: {details}"

                    return {
                        'timestamp': ts,
                        'level': level,
                        'message': msg,
                        'host': host,
                        'source_type': source_type,
                        'device': {
                            'hostname': host,
                            'device_type': 'plc' if 'plc' in host.lower() else ('scada' if 'scada' in host.lower() else 'server')
                        }
                    }
            except Exception:
                pass

        # 3. Fallback generic raw log line
        severity = 'HIGH' if any(k in line.upper() for k in ['ERROR', 'EXCEPTION', 'FAIL', 'ALERT', 'CRITICAL']) else 'INFO'
        return {
            'timestamp': timestamp,
            'level': severity,
            'message': line,
            'host': default_host,
            'source_type': source_type,
            'device': {
                'hostname': default_host,
                'device_type': 'plc' if 'plc' in default_host.lower() else 'server'
            }
        }

    def _flusher_loop(self):
        """Asynchronous flusher that sends batches to SIEM without blocking log readers."""
        while True:
            batch = []
            with self.lock:
                while self.buffer and len(batch) < 100:
                    batch.append(self.buffer.popleft())
            
            if batch:
                self._send_batch_to_siem(batch)
            
            time.sleep(1)

    def _send_batch_to_siem(self, batch):
        """Post a batch of normalized logs to SIEM ingress endpoint."""
        try:
            if not COLLECTOR_TOKEN:
                logger.warning("COLLECTOR_INGEST_TOKEN is not configured - discarding batch")
                return

            headers = {
                "Content-Type": "application/json",
                "X-Collector-Token": COLLECTOR_TOKEN
            }
            logger.info(f"📤 Forwarding {len(batch)} logs to SIEM ({SIEM_INGRESS_URL})...")
            r = self.session.post(SIEM_INGRESS_URL, json={'events': batch}, headers=headers, timeout=8)
            if r.status_code in (200, 202):
                logger.info(f"✓ SIEM accepted {len(batch)} logs (Status {r.status_code})")
            else:
                logger.error(f"✗ SIEM rejected batch with status {r.status_code}: {r.text}")
                # Re-queue batch on transient server error
                if r.status_code >= 500:
                    with self.lock:
                        for item in reversed(batch):
                            self.buffer.appendleft(item)
        except Exception as e:
            logger.error(f"Failed to transmit logs to SIEM: {e}")
            with self.lock:
                for item in reversed(batch):
                    self.buffer.appendleft(item)

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🔍 DEDICATED PARALLEL LOG COLLECTOR - DYNAMIC MACHINE DISCOVERY")
    logger.info("=" * 70)
    
    logger.info(f"Log Base Directory: {LOGS_BASE_DIR}")
    logger.info(f"Forwarding Target: {SIEM_INGRESS_URL}")
    logger.info(f"Dashboard: http://0.0.0.0:{COLLECTOR_PORT}/")
    logger.info(f"API: http://0.0.0.0:{COLLECTOR_PORT}/api/raw-stream")
    
    # Start collector in background
    collector = ParallelLogCollector()
    t = threading.Thread(target=collector.run, daemon=True, name="collector-main")
    t.start()
    
    # Start Flask dashboard server
    logger.info(f"✓ Starting Flask dashboard on port {COLLECTOR_PORT}")
    server = make_server('0.0.0.0', COLLECTOR_PORT, app, threaded=True)
    server.serve_forever()
