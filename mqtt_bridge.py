#!/usr/bin/env python3
"""
MQTT to Django Bridge
Escucha mensajes MQTT y los envía a Django via API REST
"""

import json
import logging
import time
import os
import requests
from datetime import datetime
import paho.mqtt.client as mqtt
from typing import Dict, Any
import signal
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

DJANGO_BASE_URL = os.getenv('DJANGO_URL', 'http://localhost:8000')
DJANGO_API_KEY = os.getenv('DJANGO_API_KEY', 'your_api_key_here')
MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mqtt_bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MQTTBridge')

class MQTTDjangoBridge:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Configurar credenciales MQTT si están disponibles
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        self.running = True
        self.session = requests.Session()
        
        # Headers para Django API
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-API-Key': DJANGO_API_KEY,
        })
        
        # Mapeo de topics MQTT a endpoints Django
        self.topic_mapping = {
            # Nuevos topics de sensor_mqtt y actuator_mqtt
            'home/sensors/+/data': self.handle_sensor_data,
            'home/actuator/+/data': self.handle_actuator_data,
            'home/actuator/+/command': self.handle_actuator_command
        }

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Conectado al broker MQTT")
            # Suscribirse a todos los topics
            for topic in self.topic_mapping.keys():
                client.subscribe(topic)
                logger.info(f"Suscrito a: {topic}")
        else:
            logger.error(f"Error conectando al MQTT broker: {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Desconectado del broker MQTT: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.info(f"Mensaje recibido - Topic: {topic}, Payload: {payload}")
            
            # Encontrar el handler apropiado
            for topic_pattern, handler in self.topic_mapping.items():
                if self.topic_matches(topic, topic_pattern):
                    handler(topic, payload)
                    break
            else:
                logger.warning(f"No hay handler para el topic: {topic}")
                
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")

    def topic_matches(self, topic: str, pattern: str) -> bool:
        """Verifica si un topic coincide con un patrón (soporta +)"""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(topic_parts) != len(pattern_parts):
            return False
            
        for t, p in zip(topic_parts, pattern_parts):
            if p != '+' and p != t:
                return False
        return True

    def clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Limpia el diccionario eliminando campos con valor None"""
        return {k: v for k, v in data.items() if v is not None}

    def send_to_django(self, endpoint: str, data: Dict[str, Any]) -> bool:
        """Envía datos a Django via API REST"""
        try:
            # Limpiar datos antes de enviar
            clean_data = self.clean_data(data)
            
            url = f"{DJANGO_BASE_URL}/{endpoint}/"
            response = self.session.post(url, json=clean_data, timeout=10)
            
            if response.status_code in [200, 201, 203]:
                logger.info(f"Datos enviados exitosamente a {endpoint}")
                return True
            else:
                logger.error(f"Error enviando a Django: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión con Django: {e}")
            return False

    def handle_sensor_data(self, topic: str, payload: str):
        """Maneja datos de sensores: home/sensors/SENSOR_ID/data"""
        try:
            # Convertir JSON a diccionario Python
            data = json.loads(payload)
            sensor_id = data.get('sensor_id', topic.split('/')[2])
            
            logger.info(f"Procesando datos del sensor {sensor_id}")
            
            # Preparar diccionario con todos los campos del sensor
            sensor_dict = {
                'sensor_id': data.get('sensor_id', sensor_id),
                'temperature': data.get('temperature'),
                'humidity': data.get('humidity'),
                'timestamp': data.get('timestamp'),
                'wifi_signal': data.get('wifi_signal'),
                'free_heap': data.get('free_heap'),
                'sensor_error': data.get('sensor_error', False),
                'source': 'mqtt_bridge'
            }
            
            # Enviar diccionario a Django
            self.send_to_django('sensors/api/readings', sensor_dict)
            
        except json.JSONDecodeError:
            logger.error(f"Payload JSON inválido: {payload}")
        except Exception as e:
            logger.error(f"Error manejando datos de sensor: {e}")

    def handle_actuator_data(self, topic: str, payload: str):
        """
        Maneja datos de actuadores: home/actuator/ACTUATOR_ID/data
        Ahora usa ActuatorReadings para evitar bucles infinitos de control
        """
        try:
            # Convertir JSON a diccionario Python
            data = json.loads(payload)
            actuator_id = data.get('actuator_id', topic.split('/')[2])
            
            logger.info(f"Procesando lectura del actuador {actuator_id} (sin disparar control automático)")
            
            # Preparar diccionario para ActuatorReadings (NO dispara control automático)
            reading_dict = {
                'actuator_id': data.get('actuator_id', actuator_id),
                'is_heating': data.get('is_heating', False),
                'timestamp': data.get('timestamp'),
                'wifi_signal': data.get('wifi_signal'),
                'free_heap': data.get('free_heap'),
                'temperature': data.get('temperature'),
                'source': 'mqtt_bridge',
                'reading_type': 'periodic_reading'  # Marca como lectura periódica, no comando
            }
            
            # Enviar a ActuatorReadings (NO dispara control automático)
            success = self.send_to_django('actuators/api/readings', reading_dict)
            
            if success:
                logger.info(f"✅ Lectura de actuador {actuator_id} registrada (sin bucle)")
            else:
                logger.error(f"❌ Error registrando lectura de actuador {actuator_id}")
            
        except json.JSONDecodeError:
            logger.error(f"Payload JSON inválido para actuador: {payload}")
        except Exception as e:
            logger.error(f"Error manejando datos de actuador: {e}")

    def handle_actuator_command(self, topic: str, payload: str):
        """Maneja datos de actuadores: home/actuator/ACTUATOR_ID/command"""
        try:
            actuator_id = topic.split('/')[2]
            data = json.loads(payload)

            logger.info(f"Comando enviado al actuador {actuator_id}: {data}")

        except Exception as e:
            logger.error(f"Error manejando comando de actuador: {e}")

    def handle_sensor_status(self, topic: str, payload: str):
        """Maneja estado de sensores: home/sensors/SENSOR_ID/status"""
        try:
            sensor_id = topic.split('/')[2]
            data = json.loads(payload)
            
            django_data = {
                'sensor_id': sensor_id,
                'online': data.get('online', True),
                'battery': data.get('battery'),
                'signal_strength': data.get('signal_strength'),
                'last_seen': datetime.now().isoformat(),
                'source': 'mqtt_bridge'
            }
            
            self.send_to_django('sensors/api/status', django_data)
            
        except Exception as e:
            logger.error(f"Error manejando estado de sensor: {e}")

    def run(self):
        """Ejecutar el bridge"""
        logger.info("Iniciando MQTT to Django Bridge...")
        
        try:
            self.client.connect(MQTT_HOST, MQTT_PORT, 60)
            self.client.loop_start()
            
            logger.info(f"Bridge ejecutándose. Conectado a MQTT: {MQTT_HOST}:{MQTT_PORT}")
            logger.info(f"Django URL: {DJANGO_BASE_URL}")
            logger.info(f"Topics suscritos: {list(self.topic_mapping.keys())}")
            
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Deteniendo bridge...")
        except Exception as e:
            logger.error(f"Error ejecutando bridge: {e}")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Bridge detenido")

    def stop(self):
        """Detener el bridge"""
        self.running = False

def signal_handler(signum, frame):
    """Manejar señales del sistema"""
    logger.info(f"Recibida señal {signum}, deteniendo...")
    bridge.stop()

if __name__ == "__main__":
    # Configurar manejo de señales
    bridge = MQTTDjangoBridge()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ejecutar bridge
    bridge.run()