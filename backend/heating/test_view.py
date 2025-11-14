from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import HeatingSettings, HeatingSchedule

@login_required
def test_dashboard_data(request):
    """Vista de prueba para verificar que los datos están disponibles"""
    
    # Obtener datos directamente
    settings = HeatingSettings.objects.all()
    schedules = HeatingSchedule.objects.all()
    
    context = {
        'user': request.user,
        'settings_count': settings.count(),
        'schedules_count': schedules.count(),
        'settings_list': [(s.id, s.name, s.is_active) for s in settings],
        'schedules_list': [(s.id, s.name, s.is_active, s.start_time, s.end_time) for s in schedules],
    }
    
    if request.GET.get('format') == 'json':
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
        
        <h2>Configuraciones ({settings.count()})</h2>
        <div class="data">
        {'<br>'.join([f"ID: {s[0]}, Nombre: {s[1]}, Activa: {s[2]}" for s in context['settings_list']])}
        </div>
        
        <h2>Horarios ({schedules.count()})</h2>
        <div class="data">
        {'<br>'.join([f"ID: {s[0]}, Nombre: {s[1]}, Activo: {s[2]}, Horario: {s[3]}-{s[4]}" for s in context['schedules_list']])}
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
    
    return render(request, 'heating/test.html', context) if False else JsonResponse({'html': html}, safe=False)