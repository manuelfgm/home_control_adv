#!/usr/bin/env python
"""
Comando Django para generar datos de prueba
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import random

from sensors.models import SensorReading
from heating.models import HeatingLog


class Command(BaseCommand):
    help = 'Genera datos de prueba para las gráficas'

    def handle(self, *args, **options):
        self.stdout.write("=== Generador de Datos de Prueba para Gráficas ===\n")
        
        # Verificar datos existentes
        sensor_count = SensorReading.objects.count()
        heating_count = HeatingLog.objects.count()
        
        self.stdout.write(f"📊 Datos actuales:")
        self.stdout.write(f"  • Lecturas de sensores: {sensor_count}")
        self.stdout.write(f"  • Logs de calefacción: {heating_count}")
        
        # Generar datos siempre para tener una buena visualización
        self.stdout.write("🔄 Regenerando datos para mejor visualización...")
        
        # Limpiar datos anteriores de prueba
        SensorReading.objects.filter(source__in=['sample_data', 'current_reading']).delete()
        HeatingLog.objects.filter(source__in=['sample_data', 'current_status']).delete()
        
        self.stdout.write(f"\n🔧 Generando datos de prueba realistas...")
        
        # Generar datos para las últimas 72 horas para tener buena visualización
        now = timezone.now()
        start_time = now - timedelta(hours=72)
        
        # Configuración base más realista
        base_temp = 18.5
        base_humidity = 45.0
        heating_on = False
        target_temp = 20.0
        
        generated_sensors = 0
        generated_heating = 0
        
        # Generar un punto cada 10 minutos para más detalle
        current_time = start_time
        while current_time <= now:
            
            # Simular efectos ambientales realistas
            hour = current_time.hour
            
            # Variación por hora del día (temperaturas más bajas por la noche)
            if 22 <= hour or hour <= 6:
                ambient_factor = -1.5  # Noche más fría
            elif 6 <= hour <= 9:
                ambient_factor = 0.5   # Mañana templada
            elif 14 <= hour <= 16:
                ambient_factor = 1.0   # Tarde más caliente
            else:
                ambient_factor = 0.0   # Resto del día normal
            
            # Variación natural pequeña
            temp_variation = random.uniform(-0.5, 0.5)
            humidity_variation = random.uniform(-2, 2)
            
            # Lógica realista de calefacción
            if heating_on:
                # La calefacción sube la temperatura gradualmente
                base_temp += random.uniform(0.1, 0.4)
                # Y reduce un poco la humedad
                base_humidity -= random.uniform(0, 1)
            else:
                # Sin calefacción, la temperatura tiende hacia la ambiente
                target_ambient = 16 + ambient_factor
                if base_temp > target_ambient:
                    base_temp -= random.uniform(0.05, 0.2)
                else:
                    base_temp += random.uniform(0, 0.1)
            
            # Mantener rangos realistas
            base_temp = max(14, min(26, base_temp))
            base_humidity = max(35, min(65, base_humidity + humidity_variation * 0.1))
            
            # Crear lectura de sensor
            if not SensorReading.objects.filter(created_at__exact=current_time).exists():
                SensorReading.objects.create(
                    sensor_id='livingroom',
                    temperature=round(base_temp + temp_variation, 1),
                    humidity=round(base_humidity, 1),
                    wifi_signal=random.randint(-60, -40),
                    free_heap=random.randint(20000, 30000),
                    sensor_error=False,
                    source='sample_data',
                    created_at=current_time
                )
                generated_sensors += 1
            
            # Lógica de calefacción más frecuente y realista
            if current_time.minute % 10 == 0:  # Evaluar cada 10 minutos
                # Horarios programados realistas
                if 6 <= hour <= 9:
                    target_temp = 21.5  # Mañana confortable
                elif 18 <= hour <= 23:
                    target_temp = 22.0  # Noche caliente
                elif 23 <= hour or hour <= 6:
                    target_temp = 18.0  # Noche fresca
                else:
                    target_temp = 19.5  # Día normal
                
                # Histéresis realista
                if not heating_on and base_temp < target_temp - 0.8:
                    heating_on = True
                elif heating_on and base_temp > target_temp + 0.3:
                    heating_on = False
            
            # Crear log de calefacción cuando cambia el estado o cada hora
            should_log = (current_time.minute == 0 or 
                         (current_time.minute % 20 == 0 and heating_on))
            
            if should_log:
                HeatingLog.objects.create(
                    timestamp=current_time,
                    is_heating=heating_on,
                    current_temperature=round(base_temp, 1),
                    target_temperature=target_temp,
                    action_reason='schedule_automatic' if 6 <= hour <= 9 or 18 <= hour <= 23 else 'schedule_eco',
                    actuator_id='boiler',
                    wifi_signal=random.randint(-50, -35),
                    free_heap=random.randint(22000, 28000),
                    source='sample_data'
                )
                generated_heating += 1
            
            current_time += timedelta(minutes=10)
        
        self.stdout.write(f"\n✅ Datos generados:")
        self.stdout.write(f"  • Nuevas lecturas de sensores: {generated_sensors}")
        self.stdout.write(f"  • Nuevos logs de calefacción: {generated_heating}")
        
        # Crear lecturas actuales más realistas
        current_hour = now.hour
        
        # Estado actual según la hora
        if 6 <= current_hour <= 9 or 18 <= current_hour <= 23:
            current_target = 21.5
            current_temp = 21.2
            current_heating = True
        else:
            current_target = 19.0
            current_temp = 19.8
            current_heating = False
        
        # Múltiples sensores para simular casa real
        sensors_data = [
            ('livingroom', current_temp, 48.5),
            ('bedroom', current_temp - 1.5, 52.0),
            ('kitchen', current_temp + 0.8, 45.2),
        ]
        
        for sensor_id, temp, humidity in sensors_data:
            SensorReading.objects.create(
                sensor_id=sensor_id,
                temperature=temp,
                humidity=humidity,
                wifi_signal=random.randint(-55, -35),
                free_heap=random.randint(20000, 30000),
                sensor_error=False,
                source='current_reading'
            )
        
        latest_heating = HeatingLog.objects.create(
            is_heating=current_heating,
            current_temperature=current_temp,
            target_temperature=current_target,
            action_reason='schedule_active' if current_heating else 'schedule_eco',
            actuator_id='boiler',
            wifi_signal=-42,
            free_heap=26500,
            source='current_status'
        )
        
        self.stdout.write(f"  • {len(sensors_data)} sensores creados con temperaturas: {[temp for _, temp, _ in sensors_data]}")
        self.stdout.write(f"  • Estado actual creado: Calefacción {'encendida' if latest_heating.is_heating else 'apagada'}")
        
        self.stdout.write(self.style.SUCCESS(f"\n🎯 Dashboard de gráficas listo en: http://localhost:8000/heating/charts/"))