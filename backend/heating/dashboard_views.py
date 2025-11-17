from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.middleware.csrf import get_token
from django.utils import timezone
import json
from datetime import time

from .models import HeatingSettings, HeatingSchedule, HeatingLog, HeatingController
from .serializers import CurrentStatusSerializer, HeatingSettingsSerializer, HeatingScheduleSerializer

@login_required
def test_dashboard_data(request):
    """Vista de prueba para verificar que los datos están disponibles"""
    
    # Obtener datos ordenados por estado: activos, activados, desactivados
    settings_active = HeatingSettings.objects.filter(is_active=True).order_by('name')
    settings_inactive = HeatingSettings.objects.filter(is_active=False).order_by('name')
    settings = list(settings_active) + list(settings_inactive)
    
    schedules_all = HeatingSchedule.objects.all()
    schedules_active_now = [s for s in schedules_all if s.is_active and s.is_active_now()]
    schedules_enabled_not_now = [s for s in schedules_all if s.is_active and not s.is_active_now()]  
    schedules_disabled = [s for s in schedules_all if not s.is_active]
    schedules = schedules_active_now + schedules_enabled_not_now + schedules_disabled
    
    context = {
        'user': request.user,
        'settings_count': len(settings),
        'schedules_count': len(schedules),
        'settings_list': [(s.id, s.name, 'Activada' if s.is_active else 'Desactivada') for s in settings],
        'schedules_list': [(s.id, s.name, 
                          'Activo Ahora' if s.is_active and s.is_active_now() 
                          else 'Activado' if s.is_active 
                          else 'Desactivado', 
                          s.start_time, s.end_time) for s in schedules],
    }
    
    if request.GET.get('format') == 'json':
        from django.http import JsonResponse
        return JsonResponse(context, safe=False)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Dashboard Data</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .success {{ color: green; }}
            .error {{ color: red; }}
            .data {{ background: #f5f5f5; padding: 10px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>Dashboard Data Test</h1>
        
        <div class="success">✅ Usuario autenticado: {request.user.username}</div>
        
        <h2>Configuraciones ({len(settings)})</h2>
        <div class="data">
        {'<br>'.join([f"ID: {s[0]}, Nombre: {s[1]}, Estado: {s[2]}" for s in context['settings_list']])}
        </div>
        
        <h2>Horarios ({len(schedules)})</h2>
        <div class="data">
        {'<br>'.join([f"ID: {s[0]}, Nombre: {s[1]}, Estado: {s[2]}, Horario: {s[3]}-{s[4]}" for s in context['schedules_list']])}
        </div>
        
        <h2>Test de APIs con JavaScript</h2>
        <div id="api-test">
            <button onclick="testAPIs()">Probar APIs</button>
            <div id="results"></div>
        </div>
        
        <script>
        async function testAPIs() {{
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<p>Probando APIs...</p>';
            
            let results = [];
            
            // Test API Settings
            try {{
                const settingsResp = await fetch('/heating/api/settings/', {{
                    credentials: 'same-origin'
                }});
                results.push(`Settings API: ${{settingsResp.status}} - ${{settingsResp.ok ? 'OK' : 'ERROR'}}`);
                if (settingsResp.ok) {{
                    const data = await settingsResp.json();
                    results.push(`  → ${{data.length}} configuraciones encontradas`);
                }}
            }} catch (e) {{
                results.push(`Settings API: ERROR - ${{e.message}}`);
            }}
            
            // Test API Schedules  
            try {{
                const schedulesResp = await fetch('/heating/api/schedules/', {{
                    credentials: 'same-origin'
                }});
                results.push(`Schedules API: ${{schedulesResp.status}} - ${{schedulesResp.ok ? 'OK' : 'ERROR'}}`);
                if (schedulesResp.ok) {{
                    const data = await schedulesResp.json();
                    results.push(`  → ${{data.length}} horarios encontrados`);
                }}
            }} catch (e) {{
                results.push(`Schedules API: ERROR - ${{e.message}}`);
            }}
            
            // Test API Status
            try {{
                const statusResp = await fetch('/heating/api/status/', {{
                    credentials: 'same-origin'
                }});
                results.push(`Status API: ${{statusResp.status}} - ${{statusResp.ok ? 'OK' : 'ERROR'}}`);
                if (statusResp.ok) {{
                    const data = await statusResp.json();
                    results.push(`  → Temp objetivo: ${{data.target_temperature}}°C`);
                }}
            }} catch (e) {{
                results.push(`Status API: ERROR - ${{e.message}}`);
            }}
            
            resultsDiv.innerHTML = '<pre>' + results.join('\\n') + '</pre>';
        }}
        </script>
    </body>
    </html>
    """
    
    return HttpResponse(html)


@login_required
def dashboard_view(request):
    """Servir el dashboard HTML estático - requiere login"""
    # Crear el contenido HTML con el username del usuario
    username = request.user.username
    html_content = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="CSRF_TOKEN_PLACEHOLDER">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="shortcut icon" type="image/x-icon" href="/favicon.ico">
    <title>🏠 Dashboard Calefacción</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f8f9fa; color: #333; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .header { background: #6c757d; color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { font-size: 1.5rem; font-weight: 600; margin: 0; }
        .nav-links { display: flex; gap: 1rem; }
        .nav-links a { color: white; text-decoration: none; padding: 0.5rem 1rem; border-radius: 4px; background: rgba(255,255,255,0.1); transition: background 0.2s; }
        .nav-links a:hover { background: rgba(255,255,255,0.2); }
        
        .status-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .status-card h3 {
            margin-top: 0;
            color: #6c757d;
            font-size: 1.2rem;
        }
        
        .temperature {
            font-size: 2em;
            margin: 10px 0;
            font-weight: bold;
            /* Color dinámico aplicado por JavaScript */
        }
        
        .heating-on {
            color: #e74c3c !important;
        }
        
        .heating-off {
            color: #95a5a6 !important;
        }
        
        .status-info {
            display: flex;
            justify-content: space-around;
            margin-top: 15px;
            text-align: center;
        }
        
        .status-info > div {
            flex: 1;
        }
        
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h3 { margin-top: 0; color: #6c757d; }
        .status { text-align: center; }
        .btn { padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .btn-primary { background: #6c757d; color: white; }
        .btn-success { background: #495057; color: white; }
        .btn-danger { background: #868e96; color: white; }
        .btn-warning { background: #adb5bd; color: white; }
        .btn:hover { opacity: 0.8; }
        .form-group { margin: 10px 0; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .schedule-item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 4px; }
        .schedule-active { border-color: #27ae60; background: #f8fff8; }
        .schedule-current { border-color: #e74c3c; background: #fff8f8; }
        .log-item { padding: 8px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: white; margin: 10% auto; padding: 20px; width: 80%; max-width: 500px; border-radius: 8px; }
        .close { float: right; font-size: 28px; cursor: pointer; }
        .weekday-selector { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; }
        .weekday-btn { padding: 10px; border: 1px solid #ddd; background: #f8f9fa; cursor: pointer; text-align: center; border-radius: 4px; }
        .weekday-btn.selected { background: #007bff; color: white; }
        .alert { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        
        @media (max-width: 768px) {
            .header {
                padding: 1rem;
                flex-direction: column;
                gap: 1rem;
            }

            .controls {
                justify-content: center;
            }

            .container {
                padding: 0 0.5rem;
            }
        }
    </style>
</head>
<body>
    <header class="header">
        <div>
            <h1>🏠 Dashboard Calefacción</h1>
        </div>
        <nav class="nav-links">
            <a href="/heating/charts/">📊 Gráficas</a>
            <a href="/admin/logout/" onclick="event.preventDefault(); document.getElementById('logout-form').submit();">🔚 Salir</a>
        </nav>
    </header>

    <form id="logout-form" method="post" action="/admin/logout/" style="display: none;">
        <input type="hidden" name="csrfmiddlewaretoken" value="CSRF_TOKEN_PLACEHOLDER">
    </form>

    <div class="container">

        <div id="alerts"></div>

        <!-- Estado Actual -->
        <div class="status-card">
            <h3>Estado Actual</h3>
            <div class="temperature" id="current-temp">--°C</div>
            <div id="heating-status">Sistema apagado</div>
            <div class="status-info">
                <div>Objetivo: <span id="target-temp">--°C</span></div>
                <div>Horario: <span id="current-schedule">--</span></div>
            </div>
        </div>

        <div class="cards">

        <!-- Horarios de Calefacción (primero para móvil) -->
        <div class="card">
            <h3>Horarios de Calefacción</h3>
            <div style="margin-bottom: 15px;">
                <button class="btn btn-success" onclick="dashboard.createNewSchedule()">➝ Nuevo Horario</button>
            </div>
            <div id="schedules-list"></div>
        </div>

        <!-- Configuraciones del Sistema -->
        <div class="card">
            <h3>Configuraciones del Sistema</h3>
            <div style="margin-bottom: 15px;">
                <button class="btn btn-success" onclick="dashboard.createNewSettings()">➞ Nueva Configuración</button>
            </div>
            <div id="settings-list">
                <p>Cargando configuraciones...</p>
            </div>
        </div>

        <!-- Últimos Logs -->
        <div class="card">
            <h3>Actividad Reciente</h3>
            <div id="recent-logs" style="max-height: 300px; overflow-y: auto;"></div>
        </div>
    </div>

    <!-- Modal para crear/editar horarios -->
    <div id="schedule-modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeScheduleModal()">&times;</span>
            <h3 id="schedule-modal-title">Nuevo Horario</h3>
            <div id="schedule-error-area" style="display: none; background: #ffebee; border: 1px solid #f44336; color: #c62828; padding: 10px; margin: 10px 0; border-radius: 4px;">
                <strong>⚠️ Error:</strong> <span id="schedule-error-message"></span>
            </div>
            <form id="schedule-form">
                <div class="form-group">
                    <label>Nombre:</label>
                    <input type="text" id="schedule-name" required>
                </div>
                <div class="form-group">
                    <label>Hora inicio:</label>
                    <input type="time" id="start-time" required>
                </div>
                <div class="form-group">
                    <label>Hora fin:</label>
                    <input type="time" id="end-time" required>
                </div>
                <div class="form-group">
                    <label>Temperatura objetivo (°C):</label>
                    <input type="number" id="target-temperature" min="10" max="30" step="0.5" required>
                </div>
                <div class="form-group">
                    <label>Días de la semana:</label>
                    <div class="weekday-selector" id="weekday-selector">
                        <div class="weekday-btn" data-day="0">L</div>
                        <div class="weekday-btn" data-day="1">M</div>
                        <div class="weekday-btn" data-day="2">X</div>
                        <div class="weekday-btn" data-day="3">J</div>
                        <div class="weekday-btn" data-day="4">V</div>
                        <div class="weekday-btn" data-day="5">S</div>
                        <div class="weekday-btn" data-day="6">D</div>
                    </div>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="schedule-is-active" checked> Activar horario
                    </label>
                    <small style="display: block; color: #666; margin-top: 5px;">Solo se validarán solapamientos si el horario está activo</small>
                </div>
                <div style="text-align: center; margin-top: 20px;">
                    <button type="button" class="btn btn-success" onclick="saveSchedule()">Guardar</button>
                    <button type="button" class="btn" onclick="closeScheduleModal()">Cancelar</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Modal para crear/editar configuraciones -->
    <div id="settings-modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeSettingsModal()">&times;</span>
            <h3 id="settings-modal-title">Nueva Configuración</h3>
            <div id="settings-error-area" style="display: none; background: #ffebee; border: 1px solid #f44336; color: #c62828; padding: 10px; margin: 10px 0; border-radius: 4px;">
                <strong>⚠️ Error:</strong> <span id="settings-error-message"></span>
            </div>
            <form id="settings-form">
                <div class="form-group">
                    <label>Nombre de la configuración:</label>
                    <input type="text" id="settings-name" required>
                </div>
                <div class="form-group">
                    <label>Temperatura por defecto (°C):</label>
                    <input type="number" id="settings-default-temp" min="15" max="25" step="0.5" required>
                </div>
                <div class="form-group">
                    <label>Histéresis (°C):</label>
                    <input type="number" id="settings-hysteresis" min="0.1" max="1" step="0.1" required>
                </div>

                <div style="text-align: center; margin-top: 20px;">
                    <button type="button" class="btn btn-success" onclick="saveSettings()">Guardar</button>
                    <button type="button" class="btn" onclick="closeSettingsModal()">Cancelar</button>
                </div>
            </form>
        </div>
    </div>

    <script src="/static/js/dashboard.js?v=2024-11-17-final"></script>
    <script>
        // El JavaScript externo ya maneja todo correctamente
        // No necesitamos JavaScript adicional aquí
    </script>
</body>
</html>
    """
    # Obtener token CSRF
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    
    # Reemplazar placeholders
    html_content = html_content.replace('USERNAME_PLACEHOLDER', username)
    html_content = html_content.replace('CSRF_TOKEN_PLACEHOLDER', csrf_token)
    
    return HttpResponse(html_content)








def status_api(request):
    """API para obtener estado actual (para actualización en tiempo real)"""
    try:
        serializer = CurrentStatusSerializer(None)
        data = serializer.to_representation(None)
        
        # Agregar información adicional
        data['system_time'] = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
        
        return JsonResponse(data)
    except Exception as e:
        # Debug: devolver el error para ver qué está pasando
        return JsonResponse({
            'error': str(e),
            'debug': 'Error en status_api'
        })