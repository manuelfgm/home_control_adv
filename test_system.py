#!/usr/bin/env python3
"""
Script de prueba para el sistema Home Control
Simula sensores y actuadores para verificar funcionamiento
"""

import json
import time
import random
import paho.mqtt.client as mqtt
import requests
from datetime import datetime

# Configuración
MQTT_HOST = "localhost"
MQTT_PORT = 1883
DJANGO_URL = "http://localhost:8000"

def test_mqtt_connection():
    """Probar conexión MQTT"""
    print("🔌 Probando conexión MQTT...")
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ MQTT conectado correctamente")
            client.publish("test", "Hello from test script")
        else:
            print(f"❌ Error conectando MQTT: {rc}")
    
    def on_message(client, userdata, msg):
        print(f"📩 Mensaje recibido: {msg.topic} -> {msg.payload.decode()}")
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.subscribe("test")
        client.loop_start()
        time.sleep(2)
        client.loop_stop()
        client.disconnect()
        return True
    except Exception as e:
        print(f"❌ Error MQTT: {e}")
        return False

def test_django_api():
    """Probar API de Django"""
    print("🌐 Probando API de Django...")
    
    try:
        # Health check
        response = requests.get(f"{DJANGO_URL}/health/", timeout=5)
        if response.status_code == 200:
            print("✅ Django health check OK")
        else:
            print(f"⚠️  Django health check: {response.status_code}")
        
        # API de sensores
        response = requests.get(f"{DJANGO_URL}/sensors/api/readings/", timeout=5)
        if response.status_code in [200, 401]:  # 401 es OK (necesita auth)
            print("✅ API de sensores disponible")
        else:
            print(f"⚠️  API de sensores: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Error Django: {e}")
        return False

def simulate_sensor_data():
    """Simular datos de sensor"""
    print("🌡️  Simulando datos de sensor...")
    
    client = mqtt.Client()
    
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        
        # Simular datos de temperatura y humedad
        for i in range(3):
            data = {
                "sensor_id": "test_sensor",
                "temperature": round(random.uniform(18.0, 25.0), 1),
                "humidity": round(random.uniform(40.0, 70.0), 1),
                "timestamp": datetime.now().isoformat(),
                "wifi_signal": random.randint(-80, -30)
            }
            
            topic = "home/sensors/test_sensor/data"
            message = json.dumps(data)
            
            client.publish(topic, message)
            print(f"📤 Enviado: {data['temperature']}°C, {data['humidity']}%")
            time.sleep(1)
        
        client.disconnect()
        return True
    except Exception as e:
        print(f"❌ Error simulando sensor: {e}")
        return False

def simulate_heating_control():
    """Simular control de calefacción"""
    print("🔥 Simulando control de calefacción...")
    
    client = mqtt.Client()
    
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        
        # Simular comando de encendido
        command = {
            "action": "turn_on",
            "target_temperature": 22.0,
            "mode": "manual",
            "timestamp": datetime.now().isoformat()
        }
        
        topic = "home/heating/control"
        message = json.dumps(command)
        
        client.publish(topic, message)
        print(f"📤 Comando enviado: {command['action']}")
        
        time.sleep(2)
        
        # Simular estado de calefacción
        status = {
            "is_heating": True,
            "current_temperature": 20.5,
            "target_temperature": 22.0,
            "mode": "manual",
            "timestamp": datetime.now().isoformat()
        }
        
        status_topic = "home/heating/status"
        status_message = json.dumps(status)
        
        client.publish(status_topic, status_message)
        print(f"📤 Estado enviado: calefacción {'ON' if status['is_heating'] else 'OFF'}")
        
        client.disconnect()
        return True
    except Exception as e:
        print(f"❌ Error simulando calefacción: {e}")
        return False

def test_mqtt_bridge():
    """Probar que el bridge MQTT-Django funciona"""
    print("🌉 Probando MQTT Bridge...")
    
    # Simular datos y esperar que lleguen a Django
    simulate_sensor_data()
    time.sleep(3)  # Dar tiempo al bridge para procesar
    
    try:
        # Verificar que los datos llegaron a Django
        response = requests.get(f"{DJANGO_URL}/sensors/api/readings/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('results') and len(data['results']) > 0:
                print("✅ Bridge MQTT-Django funcionando")
                print(f"📊 Últimas lecturas: {len(data['results'])}")
                return True
            else:
                print("⚠️  No se encontraron datos recientes")
                return False
        else:
            print(f"⚠️  No se puede verificar bridge: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verificando bridge: {e}")
        return False

def main():
    """Ejecutar todas las pruebas"""
    print("🧪 INICIANDO PRUEBAS DEL SISTEMA HOME CONTROL")
    print("=" * 50)
    
    tests = [
        ("MQTT Connection", test_mqtt_connection),
        ("Django API", test_django_api),
        ("Sensor Simulation", simulate_sensor_data),
        ("Heating Control", simulate_heating_control),
        ("MQTT Bridge", test_mqtt_bridge),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en {test_name}: {e}")
            results.append((test_name, False))
        
        time.sleep(1)
    
    # Resumen
    print("\n" + "=" * 50)
    print("📋 RESUMEN DE PRUEBAS")
    print("=" * 50)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    print(f"\n🎯 Total: {passed_tests}/{total_tests} pruebas exitosas")
    
    if passed_tests == total_tests:
        print("🎉 ¡Todos los tests pasaron! Sistema funcionando correctamente.")
    else:
        print("⚠️  Algunos tests fallaron. Revisar configuración.")
    
    print(f"\n🌐 Dashboard: {DJANGO_URL}/")
    print(f"🔧 Admin: {DJANGO_URL}/admin/")

if __name__ == "__main__":
    main()