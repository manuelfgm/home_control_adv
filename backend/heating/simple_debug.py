from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def simple_debug_view(request):
    """Vista debug ultra simple para probar las APIs"""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Debug</title>
        <style>body { font-family: Arial, sans-serif; padding: 20px; }</style>
    </head>
    <body>
        <h1>Debug Simple - APIs del Dashboard</h1>
        
        <div>
            <h2>Usuario: """ + str(request.user.username) + """</h2>
            <p>Autenticado: """ + str(request.user.is_authenticated) + """</p>
        </div>
        
        <div id="status">
            <h3>🔄 Cargando datos...</h3>
        </div>
        
        <script>
        async function loadAll() {
            const statusDiv = document.getElementById('status');
            let html = '<h3>Resultados de APIs</h3>';
            
            // Test cada API una por una
            const apis = [
                { name: 'Status', url: '/heating/api/status/' },
                { name: 'Settings', url: '/heating/api/settings/' },
                { name: 'Schedules', url: '/heating/api/schedules/' },
                { name: 'Logs', url: '/heating/api/logs/' }
            ];
            
            for (const api of apis) {
                try {
                    console.log(`🔄 Probando ${api.name}...`);
                    
                    const response = await fetch(api.url, {
                        credentials: 'same-origin'
                    });
                    
                    console.log(`📡 ${api.name} Response:`, response.status, response.statusText);
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log(`✅ ${api.name} Data:`, data);
                        
                        html += `
                            <div style="margin: 10px 0; padding: 10px; border: 1px solid green;">
                                <h4>✅ ${api.name}</h4>
                                <p>Status: ${response.status}</p>
                                <p>Type: ${Array.isArray(data) ? 'Array' : typeof data}</p>
                                <p>Length/Keys: ${Array.isArray(data) ? data.length : Object.keys(data).length}</p>
                                <pre style="max-height: 200px; overflow: auto;">${JSON.stringify(data, null, 2)}</pre>
                            </div>
                        `;
                    } else {
                        console.error(`❌ ${api.name} Error:`, response.status);
                        const text = await response.text();
                        html += `
                            <div style="margin: 10px 0; padding: 10px; border: 1px solid red;">
                                <h4>❌ ${api.name}</h4>
                                <p>Status: ${response.status}</p>
                                <p>Error: ${text.substring(0, 200)}</p>
                            </div>
                        `;
                    }
                } catch (error) {
                    console.error(`💥 ${api.name} Exception:`, error);
                    html += `
                        <div style="margin: 10px 0; padding: 10px; border: 1px solid red;">
                            <h4>💥 ${api.name}</h4>
                            <p>Exception: ${error.message}</p>
                        </div>
                    `;
                }
            }
            
            statusDiv.innerHTML = html;
        }
        
        // Cargar al iniciar
        window.onload = loadAll;
        </script>
    </body>
    </html>
    """
    
    return HttpResponse(html)