from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import HeatingSettings, HeatingSchedule
from .serializers import CurrentStatusSerializer

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
    return render(request, 'heating/dashboard.html')








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