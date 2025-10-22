#!/usr/bin/env python3
"""
Evaluador de horarios de calefacción independiente.
No depende de Django, se conecta directamente a la base de datos.
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime, time
from pathlib import Path
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Configurar paths
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / "backend" / ".env"
DB_FILE = PROJECT_ROOT / "backend" / "db.sqlite3"
LOG_FILE = PROJECT_ROOT / "logs" / "heating_standalone.log"

# Crear directorio de logs si no existe
LOG_FILE.parent.mkdir(exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler() if '--verbose' in sys.argv else logging.NullHandler()
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
MQTT_TOPIC_HEATING = f"{MQTT_USERNAME}/feeds/{os.getenv('MQTT_TOPIC_HEATING', 'home.heating.control')}"

class HeatingEvaluator:
    def __init__(self):
        self.db_connection = None
        self.mqtt_client = None
        
    def connect_db(self):
        """Conecta a la base de datos SQLite"""
        try:
            self.db_connection = sqlite3.connect(DB_FILE)
            self.db_connection.row_factory = sqlite3.Row
            logger.info("Conectado a la base de datos")
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            raise
            
    def setup_mqtt(self):
        """Configura cliente MQTT para enviar comandos"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            logger.info("Cliente MQTT configurado")
        except Exception as e:
            logger.error(f"Error configurando MQTT: {e}")
    
    def get_heating_control(self, controller_id='main_heating'):
        """Obtiene el estado actual del control de calefacción"""
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT * FROM heating_heatingcontrol 
            WHERE controller_id = ?
        """, (controller_id,))
        
        result = cursor.fetchone()
        if not result:
            # Crear control si no existe
            cursor.execute("""
                INSERT INTO heating_heatingcontrol 
                (controller_id, name, status, is_heating, manual_override, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (controller_id, 'Calefacción Principal', 'auto', False, False, datetime.now().isoformat()))
            self.db_connection.commit()
            return self.get_heating_control(controller_id)
        
        return dict(result)
    
    def get_current_target_temperature(self):
        """Obtiene la temperatura objetivo para el momento actual"""
        now = datetime.now()
        current_day = now.weekday()  # 0 = Lunes, 6 = Domingo
        current_time = now.time()
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT target_temperature FROM heating_heatingschedule
            WHERE day_of_week = ? 
            AND is_active = 1
            AND time(start_time) <= time(?)
            AND time(end_time) >= time(?)
            ORDER BY target_temperature DESC
            LIMIT 1
        """, (current_day, current_time.strftime('%H:%M:%S'), current_time.strftime('%H:%M:%S')))
        
        result = cursor.fetchone()
        return result['target_temperature'] if result else None
    
    def should_turn_on_heating(self, current_temp, target_temp, currently_heating):
        """Determina si se debe encender la calefacción usando histéresis"""
        # Obtener histéresis configurada
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT hysteresis FROM heating_temperaturethreshold 
            WHERE is_active = 1 
            LIMIT 1
        """)
        result = cursor.fetchone()
        hysteresis = result['hysteresis'] if result else 0.5
        
        if currently_heating:
            # Si ya está calentando, mantener hasta alcanzar temperatura objetivo
            return current_temp < target_temp
        else:
            # Si no está calentando, encender si está por debajo de objetivo - histéresis
            return current_temp < (target_temp - hysteresis)
    
    def is_manual_override_active(self, control):
        """Verifica si el override manual está activo"""
        if not control['manual_override']:
            return False
        
        if control['manual_override_until']:
            override_until = datetime.fromisoformat(control['manual_override_until'])
            if datetime.now() > override_until:
                return False
        
        return True
    
    def send_heating_command(self, command, controller_id='main_heating'):
        """Envía comando de calefacción via MQTT"""
        try:
            if not self.mqtt_client:
                self.setup_mqtt()
            
            message = {
                'controller_id': controller_id,
                'command': command,
                'timestamp': datetime.now().isoformat()
            }
            
            result = self.mqtt_client.publish(MQTT_TOPIC_HEATING, json.dumps(message))
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Comando enviado: {command} a {controller_id}")
                return True
            else:
                logger.error(f"Error enviando comando MQTT: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error enviando comando: {e}")
            return False
    
    def log_heating_event(self, controller_id, action, reason, current_temp=None, target_temp=None):
        """Registra evento en el log de calefacción"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO heating_heatinglog 
                (controller_id, action, timestamp, temperature_before, target_temperature, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (controller_id, action, datetime.now().isoformat(), current_temp, target_temp, reason))
            self.db_connection.commit()
        except Exception as e:
            logger.error(f"Error registrando evento: {e}")
    
    def turn_on_heating(self, control, reason=""):
        """Enciende la calefacción"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                UPDATE heating_heatingcontrol 
                SET is_heating = 1, last_updated = ?
                WHERE controller_id = ?
            """, (datetime.now().isoformat(), control['controller_id']))
            
            self.db_connection.commit()
            
            # Registrar evento
            self.log_heating_event(
                control['controller_id'], 
                'turn_on', 
                reason,
                control.get('current_temperature'),
                control.get('target_temperature')
            )
            
            # Enviar comando MQTT
            self.send_heating_command('ON', control['controller_id'])
            
            logger.info(f"🔥 Calefacción encendida: {reason}")
            
        except Exception as e:
            logger.error(f"Error encendiendo calefacción: {e}")
    
    def turn_off_heating(self, control, reason=""):
        """Apaga la calefacción"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                UPDATE heating_heatingcontrol 
                SET is_heating = 0, last_updated = ?
                WHERE controller_id = ?
            """, (datetime.now().isoformat(), control['controller_id']))
            
            self.db_connection.commit()
            
            # Registrar evento
            self.log_heating_event(
                control['controller_id'], 
                'turn_off', 
                reason,
                control.get('current_temperature'),
                control.get('target_temperature')
            )
            
            # Enviar comando MQTT
            self.send_heating_command('OFF', control['controller_id'])
            
            logger.info(f"❄️ Calefacción apagada: {reason}")
            
        except Exception as e:
            logger.error(f"Error apagando calefacción: {e}")
    
    def evaluate_heating_state(self, controller_id='main_heating'):
        """Evalúa si la calefacción debe estar encendida o apagada"""
        try:
            control = self.get_heating_control(controller_id)
            current_temperature = control.get('current_temperature')
            
            if current_temperature is None:
                logger.warning("No hay temperatura actual disponible")
                return
            
            # Solo evaluar si está en modo automático y no hay override manual
            if control['status'] != 'auto':
                logger.info(f"Controlador no está en modo automático (modo: {control['status']})")
                return
            
            if self.is_manual_override_active(control):
                logger.info("Override manual activo, saltando evaluación automática")
                return
            
            # Verificar si hay un horario activo
            target_temp = self.get_current_target_temperature()
            
            if target_temp is None:
                # No hay horario activo, apagar calefacción
                if control['is_heating']:
                    self.turn_off_heating(control, "Fuera de horario programado")
                return
            
            # Actualizar temperatura objetivo en la base de datos
            cursor = self.db_connection.cursor()
            cursor.execute("""
                UPDATE heating_heatingcontrol 
                SET target_temperature = ?
                WHERE controller_id = ?
            """, (target_temp, controller_id))
            self.db_connection.commit()
            control['target_temperature'] = target_temp
            
            # Aplicar lógica de histéresis
            should_heat = self.should_turn_on_heating(
                current_temperature, 
                target_temp, 
                control['is_heating']
            )
            
            if should_heat and not control['is_heating']:
                self.turn_on_heating(
                    control, 
                    f"Temperatura {current_temperature}°C < objetivo {target_temp}°C"
                )
            elif not should_heat and control['is_heating']:
                self.turn_off_heating(
                    control, 
                    f"Temperatura {current_temperature}°C >= objetivo {target_temp}°C"
                )
            else:
                logger.info(f"Sin cambios - T:{current_temperature}°C, Obj:{target_temp}°C, Estado:{'ON' if control['is_heating'] else 'OFF'}")
                
        except Exception as e:
            logger.error(f"Error evaluando estado de calefacción: {e}")
    
    def close(self):
        """Cierra conexiones"""
        if self.db_connection:
            self.db_connection.close()
        if self.mqtt_client:
            self.mqtt_client.disconnect()

def main():
    """Función principal"""
    verbose = '--verbose' in sys.argv
    controller_id = 'main_heating'
    
    # Buscar argumentos
    for i, arg in enumerate(sys.argv):
        if arg == '--controller-id' and i + 1 < len(sys.argv):
            controller_id = sys.argv[i + 1]
    
    if verbose:
        print(f"🔥 Evaluando calefacción para controlador: {controller_id}")
    
    # Verificar configuración
    if not MQTT_USERNAME or not MQTT_PASSWORD:
        logger.error("Configuración MQTT incompleta. Revisar archivo .env")
        sys.exit(1)
    
    if not DB_FILE.exists():
        logger.error(f"Base de datos no encontrada: {DB_FILE}")
        sys.exit(1)
    
    # Evaluar calefacción
    evaluator = HeatingEvaluator()
    try:
        evaluator.connect_db()
        evaluator.evaluate_heating_state(controller_id)
    except Exception as e:
        logger.error(f"Error en evaluación: {e}")
        sys.exit(1)
    finally:
        evaluator.close()
    
    if verbose:
        print("✅ Evaluación completada")

if __name__ == "__main__":
    main()