from flask import Flask, request, jsonify, render_template_string
from functools import wraps
import time
from collections import defaultdict, deque
from datetime import datetime
import threading

app = Flask(__name__)

# ============================================
# CONFIGURACIÓN - CAMBIA ESTOS VALORES
# ============================================
NIVEL_PROTECCION = 3  # 0=Sin protección, 1=Rate Limiting, 2=Rate+CAPTCHA, 3=WAF completo

# Configuración Rate Limiting
MAX_REQUESTS = 10
TIME_WINDOW = 60

# Almacenamiento
request_counts = defaultdict(list)
captcha_verified = set()
blocked_ips = set()
request_log = deque(maxlen=500)
log_lock = threading.Lock()

# Estadísticas
stats = {
    'total': 0,
    'success': 0,
    'blocked': 0,
    'recent': deque(maxlen=200),
    'last_update': time.time()
}

def get_req_per_second():
    """Calcula requests por segundo"""
    with log_lock:
        if len(stats['recent']) < 2:
            return 0
        
        now = time.time()
        # Contar en últimos 2 segundos para tener mejor promedio
        count = sum(1 for t in stats['recent'] if now - t <= 2.0)
        return count / 2.0

# ============================================
# DECORADORES DE PROTECCIÓN
# ============================================
def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if NIVEL_PROTECCION < 1:
            return f(*args, **kwargs)
        
        ip = request.remote_addr
        current_time = time.time()
        
        request_counts[ip] = [t for t in request_counts[ip] if current_time - t < TIME_WINDOW]
        
        if len(request_counts[ip]) >= MAX_REQUESTS:
            log_request(ip, 'RATE_LIMITED')
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        request_counts[ip].append(current_time)
        return f(*args, **kwargs)
    
    return decorated_function

def captcha_check(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if NIVEL_PROTECCION < 2:
            return f(*args, **kwargs)
        
        ip = request.remote_addr
        
        if ip in captcha_verified:
            return f(*args, **kwargs)
        
        captcha_token = request.args.get('captcha') or request.form.get('captcha')
        
        if captcha_token == "valid_token":
            captcha_verified.add(ip)
            return f(*args, **kwargs)
        
        log_request(ip, 'CAPTCHA_BLOCKED')
        return jsonify({'error': 'CAPTCHA required'}), 403
    
    return decorated_function

def waf_protection(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if NIVEL_PROTECCION < 3:
            return f(*args, **kwargs)
        
        ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        if ip in blocked_ips:
            log_request(ip, 'WAF_BLOCKED')
            return jsonify({'error': 'IP blocked'}), 403
        
        suspicious = [
            len(user_agent) < 10,
            'AttackBot' in user_agent,
            'bot' in user_agent.lower() and 'googlebot' not in user_agent.lower(),
        ]
        
        if any(suspicious):
            blocked_ips.add(ip)
            log_request(ip, 'WAF_BLOCKED')
            return jsonify({'error': 'Suspicious activity'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def log_request(ip, status):
    with log_lock:
        stats['total'] += 1
        stats['recent'].append(time.time())
        stats['last_update'] = time.time()
        
        if status == 'SUCCESS':
            stats['success'] += 1
        else:
            stats['blocked'] += 1
        
        request_log.append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'ip': ip,
            'status': status
        })

# ============================================
# RUTAS
# ============================================
@app.route('/')
def dashboard():
    protection_names = {
        0: "SIN PROTECCIÓN",
        1: "Rate Limiting",
        2: "Rate Limiting + CAPTCHA",
        3: "WAF Completo"
    }
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🛡️ Servidor DDoS Demo</title>
        <meta charset="UTF-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            .header h1 { color: #333; font-size: 2.5em; margin-bottom: 10px; }
            .status-badge {
                display: inline-block;
                padding: 15px 30px;
                background: ''' + ('#4CAF50' if NIVEL_PROTECCION > 0 else '#f44336') + ''';
                color: white;
                border-radius: 50px;
                font-size: 1.2em;
                font-weight: bold;
                margin-top: 10px;
            }
            .alert-crashed {
                background: #000;
                color: #ff0000;
                padding: 40px;
                border-radius: 15px;
                margin: 20px 0;
                font-size: 2em;
                text-align: center;
                font-weight: bold;
                animation: crashBlink 0.5s infinite;
                display: none;
                border: 5px solid #ff0000;
            }
            @keyframes crashBlink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.3; }
            }
            .alert-attack {
                background: #ff4444;
                color: white;
                padding: 25px;
                border-radius: 10px;
                margin: 20px 0;
                font-size: 1.5em;
                text-align: center;
                font-weight: bold;
                animation: blink 1s infinite;
                display: none;
            }
            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.6; }
            }
            .big-stat {
                background: white;
                text-align: center;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                margin-bottom: 20px;
            }
            .big-stat-value {
                font-size: 5em;
                font-weight: bold;
                color: #667eea;
                display: block;
            }
            .big-stat-label {
                font-size: 1.3em;
                color: #666;
                margin-top: 10px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .card {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .card h3 { color: #667eea; margin-bottom: 15px; font-size: 1.3em; }
            .stat {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #eee;
            }
            .stat:last-child { border-bottom: none; }
            .stat-label { color: #666; font-weight: 500; }
            .stat-value { color: #333; font-weight: bold; font-size: 1.1em; }
            .log-container {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                max-height: 400px;
                overflow-y: auto;
            }
            .log-entry {
                padding: 8px 12px;
                margin: 5px 0;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-size: 0.85em;
            }
            .log-success { background: #d4edda; color: #155724; }
            .log-warning { background: #fff3cd; color: #856404; }
            .log-danger { background: #f8d7da; color: #721c24; }
            .protection-info {
                background: #e3f2fd;
                padding: 20px;
                border-left: 5px solid #2196F3;
                border-radius: 5px;
            }
            .refresh-btn {
                background: #667eea;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 1em;
                font-weight: bold;
                margin-top: 15px;
                transition: all 0.3s;
                width: 100%;
            }
            .refresh-btn:hover {
                background: #764ba2;
                transform: scale(1.02);
            }
            .server-status {
                text-align: center;
                padding: 15px;
                border-radius: 10px;
                margin: 10px 0;
                font-weight: bold;
                font-size: 1.2em;
            }
            .status-ok {
                background: #d4edda;
                color: #155724;
            }
            .status-warning {
                background: #fff3cd;
                color: #856404;
            }
            .status-danger {
                background: #f8d7da;
                color: #721c24;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛡️ Servidor de Demostración DDoS</h1>
                <div class="status-badge">
                    Nivel ''' + str(NIVEL_PROTECCION) + ''' - ''' + protection_names[NIVEL_PROTECCION] + '''
                </div>
            </div>

            <div class="alert-crashed" id="alert-crashed">
                💀 SERVIDOR CAÍDO 💀<br>
                <span style="font-size: 0.6em;">No se puede responder a las peticiones</span>
            </div>

            <div class="alert-attack" id="alert-attack">
                🚨 ¡ATAQUE DDOS DETECTADO! 🚨<br>
                <span style="font-size: 0.6em;">Servidor bajo carga extrema</span>
            </div>

            <div class="server-status status-ok" id="server-status">
                ✅ SERVIDOR OPERATIVO
            </div>

            <div class="big-stat">
                <span class="big-stat-value" id="req-per-sec">0</span>
                <span class="big-stat-label">Requests por Segundo</span>
            </div>

            <div class="grid">
                <div class="card">
                    <h3>📊 Estadísticas</h3>
                    <div class="stat">
                        <span class="stat-label">Total Requests</span>
                        <span class="stat-value" id="total-requests">0</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Exitosos</span>
                        <span class="stat-value" id="success-count">0</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Bloqueados</span>
                        <span class="stat-value" id="blocked-count">0</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">IPs</span>
                        <span class="stat-value" id="total-ips">0</span>
                    </div>
                </div>

                <div class="card">
                    <h3>🔒 Protección</h3>
                    <div class="protection-info">
                        ''' + {
                            0: '<strong>❌ Sin Protección</strong><br>Servidor completamente vulnerable a ataques DDoS',
                            1: '<strong>✅ Rate Limiting</strong><br>Límite: ' + str(MAX_REQUESTS) + ' req/' + str(TIME_WINDOW) + 's por IP',
                            2: '<strong>✅ Rate + CAPTCHA</strong><br>Verificación humana requerida',
                            3: '<strong>✅ WAF Completo</strong><br>Detección y bloqueo automático'
                        }[NIVEL_PROTECCION] + '''
                    </div>
                    <button class="refresh-btn" onclick="updateNow()">🔄 Actualizar</button>
                </div>
            </div>

            <div class="log-container">
                <h3 style="color: #667eea; margin-bottom: 15px;">📝 Log de Requests</h3>
                <div id="log-content">Esperando peticiones...</div>
            </div>
        </div>

        <script>
            let consecutiveFailures = 0;
            let lastReqCount = 0;
            
            function updateNow() {
                fetch('/api/stats')
                    .then(r => r.json())
                    .then(data => {
                        consecutiveFailures = 0;
                        
                        const rps = Math.round(data.req_per_sec);
                        document.getElementById('req-per-sec').textContent = rps;
                        document.getElementById('total-requests').textContent = data.total;
                        document.getElementById('success-count').textContent = data.success;
                        document.getElementById('blocked-count').textContent = data.blocked;
                        document.getElementById('total-ips').textContent = data.ips;
                        
                        const alertCrashed = document.getElementById('alert-crashed');
                        const alertAttack = document.getElementById('alert-attack');
                        const serverStatus = document.getElementById('server-status');
                        
                        // Determinar estado del servidor
                        if (rps > 100) {
                            alertCrashed.style.display = 'none';
                            alertAttack.style.display = 'block';
                            serverStatus.className = 'server-status status-danger';
                            serverStatus.textContent = '⚠️ SERVIDOR SATURADO - CARGA CRÍTICA';
                        } else if (rps > 30) {
                            alertCrashed.style.display = 'none';
                            alertAttack.style.display = 'block';
                            serverStatus.className = 'server-status status-warning';
                            serverStatus.textContent = '⚠️ SERVIDOR BAJO ATAQUE';
                        } else if (rps > 0) {
                            alertCrashed.style.display = 'none';
                            alertAttack.style.display = 'none';
                            serverStatus.className = 'server-status status-ok';
                            serverStatus.textContent = '✅ SERVIDOR OPERATIVO';
                        } else {
                            alertCrashed.style.display = 'none';
                            alertAttack.style.display = 'none';
                            serverStatus.className = 'server-status status-ok';
                            serverStatus.textContent = '✅ SERVIDOR OPERATIVO (Sin tráfico)';
                        }
                        
                        const logDiv = document.getElementById('log-content');
                        if (data.logs.length > 0) {
                            logDiv.innerHTML = data.logs.slice(-50).reverse().map(log => {
                                let cls = 'log-success';
                                if (log.status === 'RATE_LIMITED') cls = 'log-warning';
                                if (log.status.includes('BLOCKED')) cls = 'log-danger';
                                
                                return `<div class="log-entry ${cls}">[${log.timestamp}] ${log.ip} - ${log.status}</div>`;
                            }).join('');
                        }
                    })
                    .catch(err => {
                        consecutiveFailures++;
                        console.error('Error al actualizar:', err);
                        
                        if (consecutiveFailures >= 3) {
                            document.getElementById('alert-crashed').style.display = 'block';
                            document.getElementById('alert-attack').style.display = 'none';
                            document.getElementById('server-status').className = 'server-status status-danger';
                            document.getElementById('server-status').textContent = '💀 SERVIDOR NO RESPONDE';
                        }
                    });
            }

            setInterval(updateNow, 1000);
            updateNow();
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/api/data')
@waf_protection
@captcha_check
@rate_limit
def api_data():
    ip = request.remote_addr
    log_request(ip, 'SUCCESS')
    
    # Simular procesamiento costoso sin protección
    if NIVEL_PROTECCION == 0:
        time.sleep(0.1)  # 100ms - hace vulnerable al servidor
    
    return jsonify({
        'status': 'ok',
        'level': NIVEL_PROTECCION,
        'time': time.time()
    })

@app.route('/api/stats')
def api_stats():
    with log_lock:
        return jsonify({
            'total': stats['total'],
            'success': stats['success'],
            'blocked': stats['blocked'],
            'ips': len(request_counts),
            'req_per_sec': get_req_per_second(),
            'logs': list(request_log)[-100:]
        })

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"🚀 Servidor DDoS Demo")
    print(f"📊 Nivel Protección: {NIVEL_PROTECCION}")
    print(f"🌐 http://localhost:5000")
    print(f"⚠️  Nivel 0 = MUY VULNERABLE (se caerá fácilmente)")
    print(f"{'='*60}\n")
    
    # Usar configuración de Flask para manejar pocas conexiones simultáneas
    # Esto hace que el servidor sea más vulnerable al DDoS
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, 
            use_reloader=False)