#!/usr/bin/env python3
"""
Cliente MQTT independiente para el sistema de control de calefacción.
No depende de Django, se conecta directamente a la base de datos.
"""

import os
import sys
import json
import sqlite3
import logging
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Configurar paths
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / "backend" / ".env"
DB_FILE = PROJECT_ROOT / "backend" / "db.sqlite3"
LOG_FILE = PROJECT_ROOT / "logs" / "mqtt_standalone.log"

# Crear directorio de logs si no existe
LOG_FILE.parent.mkdir(exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv(ENV_FILE)

# Configuración MQTT
MQTT_BROKER = os.getenv('MQTT_BROKER', 'io.adafruit.com')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_KEEPALIVE = int(os.getenv('MQTT_KEEPALIVE', 60))

# Topics MQTT
MQTT_TOPIC_SENSOR = f"{MQTT_USERNAME}/feeds/{os.getenv('MQTT_TOPIC_SENSOR', 'home.room.status')}"
MQTT_TOPIC_HEATING = f"{MQTT_USERNAME}/feeds/{os.getenv('MQTT_TOPIC_HEATING', 'home.heating.control')}"
MQTT_TOPIC_STATUS = f"{MQTT_USERNAME}/feeds/home.heating.status"

class StandaloneMQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.is_connected = False
        self.db_connection = None
        
    def connect_db(self):
        """Conecta a la base de datos SQLite"""
        try:
            self.db_connection = sqlite3.connect(DB_FILE)
            self.db_connection.row_factory = sqlite3.Row
            logger.info("Conectado a la base de datos")
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            
    def on_connect(self, client, userdata, flags, rc):
        """Callback cuando se conecta al broker MQTT"""
        if rc == 0:
            self.is_connected = True
            logger.info("Conectado al broker MQTT")
            client.subscribe(MQTT_TOPIC_SENSOR)
            logger.info(f"Suscrito a: {MQTT_TOPIC_SENSOR}")
        else:
            self.is_connected = False
            logger.error(f"Error conectando al broker MQTT: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback cuando se desconecta del broker"""
        self.is_connected = False
        logger.warning(f"Desconectado del broker MQTT: {rc}")
    
    def on_message(self, client, userdata, msg):
        """Callback cuando se recibe un mensaje MQTT"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.info(f"Mensaje recibido en {topic}: {payload}")
            
            if MQTT_TOPIC_SENSOR in topic:
                self.process_sensor_data(payload)
                
        except Exception as e:
            logger.error(f"Error procesando mensaje MQTT: {e}")
    
    def process_sensor_data(self, payload):
        """Procesa los datos recibidos de los sensores"""
        try:
            if not self.db_connection:
                self.connect_db()
                
            data = json.loads(payload)
            sensor_id = data.get('sensor_id', 'room_sensor')
            timestamp = datetime.now().isoformat()
            
            cursor = self.db_connection.cursor()
            
            # Actualizar estado del sensor
            cursor.execute("""
                INSERT OR REPLACE INTO sensors_sensorstatus 
                (sensor_id, name, location, is_active, last_seen)
                VALUES (?, ?, ?, ?, ?)
            """, (sensor_id, f'Sensor {sensor_id}', 'Room', True, timestamp))
            
            # Guardar temperatura si está presente
            if 'temp' in data:
                cursor.execute("""
                    INSERT INTO sensors_sensorreading 
                    (sensor_id, sensor_type, value, unit, timestamp, location)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sensor_id, 'temperature', float(data['temp']), '°C', timestamp, 'Room'))
                
                # Actualizar control de calefacción
                self.update_heating_control(float(data['temp']))
            
            # Guardar humedad si está presente
            if 'hum' in data:
                cursor.execute("""
                    INSERT INTO sensors_sensorreading 
                    (sensor_id, sensor_type, value, unit, timestamp, location)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sensor_id, 'humidity', float(data['hum']), '%', timestamp, 'Room'))
            
            self.db_connection.commit()
            logger.info(f"Datos del sensor {sensor_id} guardados correctamente")
            
        except Exception as e:
            logger.error(f"Error procesando datos del sensor: {e}")
            if self.db_connection:
                self.db_connection.rollback()
    
    def update_heating_control(self, current_temperature):
        """Actualiza el control de calefacción con la temperatura actual"""
        try:
            if not self.db_connection:
                return
                
            cursor = self.db_connection.cursor()
            
            # Actualizar temperatura actual
            cursor.execute("""
                UPDATE heating_heatingcontrol 
                SET current_temperature = ?, last_updated = ?
                WHERE controller_id = ?
            """, (current_temperature, datetime.now().isoformat(), 'main_heating'))
            
            if cursor.rowcount == 0:
                # Crear control si no existe
                cursor.execute("""
                    INSERT INTO heating_heatingcontrol 
                    (controller_id, name, status, is_heating, current_temperature, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ('main_heating', 'Calefacción Principal', 'auto', False, 
                     current_temperature, datetime.now().isoformat()))
            
            self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Error actualizando control de calefacción: {e}")
    
    def publish_heating_command(self, command, controller_id='main_heating'):
        """Publica un comando de calefacción"""
        try:
            if not self.is_connected:
                logger.warning("No conectado al broker MQTT")
                return False
                
            message = {
                'controller_id': controller_id,
                'command': command,
                'timestamp': datetime.now().isoformat()
            }
            
            result = self.client.publish(MQTT_TOPIC_HEATING, json.dumps(message))
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Comando enviado: {command} a {controller_id}")
                return True
            else:
                logger.error(f"Error enviando comando MQTT: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publicando comando de calefacción: {e}")
            return False
    
    def start(self):
        """Inicia el cliente MQTT"""
        try:
            self.connect_db()
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            self.client.loop_start()
            logger.info("Cliente MQTT iniciado")
            
            # Mantener corriendo
            while True:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error en cliente MQTT: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el cliente MQTT"""
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
            if self.db_connection:
                self.db_connection.close()
            logger.info("Cliente MQTT detenido")
        except Exception as e:
            logger.error(f"Error deteniendo cliente MQTT: {e}")

def signal_handler(sig, frame):
    """Maneja las señales de interrupción"""
    logger.info("Recibida señal de interrupción, cerrando...")
    sys.exit(0)

def main():
    """Función principal"""
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Iniciando cliente MQTT independiente...")
    
    # Verificar configuración
    if not MQTT_USERNAME or not MQTT_PASSWORD:
        logger.error("Configuración MQTT incompleta. Revisar archivo .env")
        sys.exit(1)
    
    if not DB_FILE.exists():
        logger.error(f"Base de datos no encontrada: {DB_FILE}")
        sys.exit(1)
    
    # Iniciar cliente
    client = StandaloneMQTTClient()
    try:
        client.start()
    except KeyboardInterrupt:
        logger.info("Interrupción manual")
    finally:
        client.stop()

if __name__ == "__main__":
    main()