#!/usr/bin/env python
"""
Script para generar datos de prueba para las gráficas
"""
import os
import django
import sys
from datetime import datetime, timedelta
import random

# Configurar Django
sys.path.append('/home/manu/personalcode/home_control_adv/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from sensors.models import SensorReading
from heating.models import HeatingLog

def generate_sample_data():
    print("=== Generador de Datos de Prueba para Gráficas ===\n")
    
    # Verificar datos existentes
    sensor_count = SensorReading.objects.count()
    heating_count = HeatingLog.objects.count()
    
    print(f"📊 Datos actuales:")
    print(f"  • Lecturas de sensores: {sensor_count}")
    print(f"  • Logs de calefacción: {heating_count}")
    
    if sensor_count > 10 and heating_count > 10:
        print("✅ Ya hay suficientes datos para las gráficas")
        return
    
    print(f"\n🔧 Generando datos de prueba...")
    
    # Generar datos para las últimas 48 horas
    now = timezone.now()
    start_time = now - timedelta(hours=48)
    
    # Configuración base
    base_temp = 20.0
    base_humidity = 50.0
    heating_on = False
    target_temp = 21.0
    
    generated_sensors = 0
    generated_heating = 0
    
    # Generar un punto cada 15 minutos
    current_time = start_time
    while current_time <= now:
        
        # Simular variación de temperatura
        temp_variation = random.uniform(-2, 2)
        humidity_variation = random.uniform(-10, 10)
        
        # Si la calefacción está encendida, la temperatura sube lentamente
        if heating_on:
            base_temp += random.uniform(0, 0.5)
        else:
            base_temp += random.uniform(-0.3, 0.1)
        
        # Mantener rangos realistas
        base_temp = max(15, min(25, base_temp))
        base_humidity = max(30, min(70, base_humidity + humidity_variation * 0.1))
        
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
        
        # Lógica simple de calefacción cada hora
        if current_time.minute == 0:
            if base_temp < target_temp - 1:
                heating_on = True
            elif base_temp > target_temp + 0.5:
                heating_on = False
            
            # Cambiar objetivo según hora del día (simulando horarios)
            hour = current_time.hour
            if 6 <= hour <= 9 or 18 <= hour <= 23:
                target_temp = 22.0  # Más caliente en horarios activos
            else:
                target_temp = 19.0  # Más fresco el resto del tiempo
        
        # Crear log de calefacción cada 30 minutos
        if current_time.minute in [0, 30]:
            if not HeatingLog.objects.filter(timestamp__exact=current_time).exists():
                HeatingLog.objects.create(
                    timestamp=current_time,
                    is_heating=heating_on,
                    current_temperature=round(base_temp, 1),
                    target_temperature=target_temp,
                    action_reason='sample_schedule',
                    actuator_id='boiler',
                    source='sample_data'
                )
                generated_heating += 1
        
        current_time += timedelta(minutes=15)
    
    print(f"\n✅ Datos generados:")
    print(f"  • Nuevas lecturas de sensores: {generated_sensors}")
    print(f"  • Nuevos logs de calefacción: {generated_heating}")
    
    # Crear una lectura actual
    latest_sensor = SensorReading.objects.create(
        sensor_id='livingroom',
        temperature=21.5,
        humidity=55.0,
        wifi_signal=-45,
        free_heap=25000,
        sensor_error=False,
        source='current_reading'
    )
    
    latest_heating = HeatingLog.objects.create(
        is_heating=True,
        current_temperature=21.5,
        target_temperature=22.0,
        action_reason='automatic',
        actuator_id='boiler',
        source='current_status'
    )
    
    print(f"  • Lectura actual creada: {latest_sensor.temperature}°C, {latest_sensor.humidity}%")
    print(f"  • Estado actual creado: Calefacción {'encendida' if latest_heating.is_heating else 'apagada'}")
    
    print(f"\n🎯 Dashboard de gráficas listo en: http://localhost:8000/heating/charts/")

if __name__ == '__main__':
    generate_sample_data()