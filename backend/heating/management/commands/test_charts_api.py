#!/usr/bin/env python
"""
Verificar que la API de gráficas funciona correctamente en todos los períodos
"""
from django.core.management.base import BaseCommand
from heating.charts_views import charts_data_api
from django.test import RequestFactory
from django.contrib.auth.models import User
import json
import traceback


class Command(BaseCommand):
    help = 'Verificar funcionamiento de la API de gráficas'

    def handle(self, *args, **options):
        self.stdout.write("=== Verificación API de Gráficas ===\n")
        
        try:
            factory = RequestFactory()
            user = User.objects.first()
            
            if not user:
                self.stdout.write("❌ No hay usuarios en la base de datos")
                return
            
            # Probar diferentes períodos
            periods = ['24h', '7d', '30d']
            
            for period in periods:
                self.stdout.write(f"🔍 Probando período: {period}")
                
                request = factory.get(f'/heating/charts/api/data/?period={period}')
                request.user = user
                
                try:
                    response = charts_data_api(request)
                    
                    if response.status_code == 200:
                        data = json.loads(response.content)
                        
                        # Verificar estructura de datos
                        sensor_labels = len(data['sensor_data']['labels'])
                        sensor_temp = len(data['sensor_data']['temperature'])
                        sensor_humidity = len(data['sensor_data']['humidity'])
                        sensor_heating = len(data['sensor_data']['heating_background'])
                        
                        monthly_labels = len(data['monthly_usage']['labels'])
                        monthly_hours = len(data['monthly_usage']['hours'])
                        
                        self.stdout.write(f"✅ {period}: {sensor_labels} puntos de sensor, {monthly_labels} meses")
                        
                        # Verificar consistencia de datos
                        if sensor_labels == sensor_temp == sensor_humidity == sensor_heating:
                            self.stdout.write(f"   ✅ Datos de sensor consistentes")
                        else:
                            self.stdout.write(f"   ❌ Datos de sensor inconsistentes: {sensor_labels}/{sensor_temp}/{sensor_humidity}/{sensor_heating}")
                        
                        if monthly_labels == monthly_hours == 12:
                            self.stdout.write(f"   ✅ Datos mensuales correctos (12 meses)")
                        else:
                            self.stdout.write(f"   ❌ Datos mensuales incorrectos: {monthly_labels}/{monthly_hours}")
                        
                        # Verificar estadísticas actuales
                        stats = data['current_stats']
                        self.stdout.write(f"   📊 Estado actual: {stats['temperature']}°C, {stats['humidity']}%, Calef: {stats['is_heating']}")
                        
                    else:
                        self.stdout.write(f"❌ Error {response.status_code} para período {period}")
                        
                except Exception as e:
                    self.stdout.write(f"❌ Excepción en período {period}: {str(e)}")
                    traceback.print_exc()
                
                self.stdout.write("")
            
            # Probar acceso directo a dashboard
            self.stdout.write("🔍 Verificando dashboard HTML...")
            from heating.charts_views import charts_dashboard_view
            
            request = factory.get('/heating/charts/')
            request.user = user
            
            try:
                response = charts_dashboard_view(request)
                if response.status_code == 200:
                    self.stdout.write("✅ Dashboard HTML se genera correctamente")
                    content_length = len(response.content)
                    self.stdout.write(f"   📄 Tamaño del HTML: {content_length} bytes")
                else:
                    self.stdout.write(f"❌ Error en dashboard: {response.status_code}")
            except Exception as e:
                self.stdout.write(f"❌ Error en dashboard: {str(e)}")
            
            self.stdout.write("\n🎯 URLs para probar:")
            self.stdout.write("   • Dashboard: http://localhost:8000/heating/charts/")
            self.stdout.write("   • API 24h: http://localhost:8000/heating/charts/api/data/?period=24h")
            self.stdout.write("   • API 7d: http://localhost:8000/heating/charts/api/data/?period=7d")
            self.stdout.write("   • API 30d: http://localhost:8000/heating/charts/api/data/?period=30d")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 VERIFICACIÓN COMPLETADA"))
            
        except Exception as e:
            self.stdout.write(f"❌ Error general: {str(e)}")
            traceback.print_exc()