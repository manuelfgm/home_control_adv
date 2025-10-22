import json
import logging
import threading
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
import paho.mqtt.client as mqtt
from sensors.models import SensorReading, SensorStatus
from heating.models import HeatingControl, HeatingLog

logger = logging.getLogger(__name__)


class MQTTClient:
    """Cliente MQTT para comunicación con sensores y controladores"""
    
    def __init__(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.is_connected = False
        self.lock = threading.Lock()
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback cuando se conecta al broker MQTT"""
        if rc == 0:
            self.is_connected = True
            logger.info("Conectado al broker MQTT")
            # Suscribirse a los topics de sensores
            client.subscribe(f"{settings.MQTT_USERNAME}/feeds/{settings.MQTT_TOPIC_SENSOR}")
            logger.info(f"Suscrito a: {settings.MQTT_USERNAME}/feeds/{settings.MQTT_TOPIC_SENSOR}")
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
            
            # Procesar mensaje de sensor
            if settings.MQTT_TOPIC_SENSOR in topic:
                self.process_sensor_data(payload)
                
        except Exception as e:
            logger.error(f"Error procesando mensaje MQTT: {e}")
    
    def process_sensor_data(self, payload):
        """Procesa los datos recibidos de los sensores"""
        try:
            data = json.loads(payload)
            
            # Obtener o crear el estado del sensor
            sensor_id = data.get('sensor_id', 'room_sensor')
            sensor_status, created = SensorStatus.objects.get_or_create(
                sensor_id=sensor_id,
                defaults={
                    'name': f'Sensor {sensor_id}',
                    'location': 'Room',
                    'is_active': True
                }
            )
            sensor_status.last_seen = timezone.now()
            sensor_status.save()
            
            # Guardar temperatura si está presente
            if 'temp' in data:
                SensorReading.objects.create(
                    sensor_id=sensor_id,
                    sensor_type='temperature',
                    value=float(data['temp']),
                    unit='°C',
                    location=sensor_status.location
                )
                
                # Actualizar el control de calefacción con la temperatura actual
                self.update_heating_control(float(data['temp']))
            
            # Guardar humedad si está presente
            if 'hum' in data:
                SensorReading.objects.create(
                    sensor_id=sensor_id,
                    sensor_type='humidity',
                    value=float(data['hum']),
                    unit='%',
                    location=sensor_status.location
                )
                
            logger.info(f"Datos del sensor {sensor_id} guardados correctamente")
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error procesando datos del sensor: {e}")
    
    def update_heating_control(self, current_temperature):
        """Actualiza el control de calefacción basado en la temperatura actual"""
        try:
            control, created = HeatingControl.objects.get_or_create(
                controller_id='main_heating',
                defaults={
                    'name': 'Calefacción Principal',
                    'status': 'auto'
                }
            )
            
            control.current_temperature = current_temperature
            control.save()
            
            # Si está en modo automático, evaluar si encender/apagar
            if control.status == 'auto' and not control.is_manual_override_active():
                from heating.heating_logic import HeatingLogic
                heating_logic = HeatingLogic()
                heating_logic.evaluate_heating_state(control)
                
        except Exception as e:
            logger.error(f"Error actualizando control de calefacción: {e}")
    
    def connect(self):
        """Conecta al broker MQTT"""
        try:
            with self.lock:
                if not self.is_connected:
                    self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, settings.MQTT_KEEPALIVE)
                    self.client.loop_start()
                    logger.info("Cliente MQTT iniciado")
        except Exception as e:
            logger.error(f"Error conectando al broker MQTT: {e}")
    
    def disconnect(self):
        """Desconecta del broker MQTT"""
        try:
            with self.lock:
                if self.is_connected:
                    self.client.loop_stop()
                    self.client.disconnect()
                    logger.info("Cliente MQTT desconectado")
        except Exception as e:
            logger.error(f"Error desconectando del broker MQTT: {e}")
    
    def publish_heating_command(self, command, controller_id='main_heating'):
        """Publica un comando de calefacción"""
        try:
            if not self.is_connected:
                logger.warning("No conectado al broker MQTT")
                return False
                
            topic = f"{settings.MQTT_USERNAME}/feeds/{settings.MQTT_TOPIC_HEATING}"
            message = {
                'controller_id': controller_id,
                'command': command,
                'timestamp': timezone.now().isoformat()
            }
            
            result = self.client.publish(topic, json.dumps(message))
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Comando enviado: {command} a {controller_id}")
                
                # Registrar en el log
                HeatingLog.objects.create(
                    controller_id=controller_id,
                    action='turn_on' if command == 'ON' else 'turn_off',
                    reason=f"Comando MQTT: {command}"
                )
                
                return True
            else:
                logger.error(f"Error enviando comando MQTT: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publicando comando de calefacción: {e}")
            return False


# Instancia global del cliente MQTT
mqtt_client = MQTTClient()