from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime
import logging

logger = logging.getLogger(__name__)

class HeatingSettings(models.Model):
    """
    Configuración global del sistema de calefacción
    """
    name = models.CharField(max_length=100, default="Configuración Principal", help_text="Nombre de la configuración")
    
    # Temperatura por defecto (cuando no hay horarios activos)
    default_temperature = models.FloatField(
        default=18.0,
        validators=[MinValueValidator(15.0), MaxValueValidator(25.0)],
        help_text="Temperatura por defecto cuando no hay horarios activos (°C)"
    )
    
    # Tolerancia/histéresis
    hysteresis = models.FloatField(
        default=0.2,
        validators=[MinValueValidator(0.1), MaxValueValidator(0.5)],
        help_text="Diferencia de temperatura para evitar ciclos on/off constantes (°C)"
    )
    
    # Estado del sistema
    is_active = models.BooleanField(default=True, help_text="¿Está activo el sistema de calefacción?")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración de Calefacción"
        verbose_name_plural = "Configuraciones de Calefacción"
    
    def __str__(self):
        return f"{self.name} - {self.default_temperature}°C"
    
    @classmethod
    def get_current_settings(cls):
        """Obtiene la configuración activa actual"""
        return cls.objects.filter(is_active=True).first() or cls.objects.first()


class HeatingSchedule(models.Model):
    """
    Horarios de calefacción por días de la semana
    """
    WEEKDAYS = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    name = models.CharField(max_length=100, help_text="Nombre del horario")
    
    # Días de la semana (múltiples días separados por comas)
    weekdays = models.CharField(
        max_length=20,
        default="0,1,2,3,4",  # Por defecto laborables
        help_text="Días de la semana separados por comas (ej: '0,1,2,3,4' para L-V)"
    )
    
    # Horario
    start_time = models.TimeField(help_text="Hora de inicio")
    end_time = models.TimeField(help_text="Hora de fin")
    
    # Temperatura objetivo
    target_temperature = models.FloatField(
        validators=[MinValueValidator(10.0), MaxValueValidator(30.0)],
        help_text="Temperatura objetivo durante este horario (°C)"
    )
    
    # Estado
    is_active = models.BooleanField(default=True, help_text="¿Está activo este horario?")
    
    # Relación con configuración
    settings = models.ForeignKey(
        HeatingSettings, 
        on_delete=models.CASCADE, 
        related_name='schedules',
        null=True, 
        blank=True,
        help_text="Configuración asociada"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Horario de Calefacción"
        verbose_name_plural = "Horarios de Calefacción"
        ordering = ['start_time']
    
    def __str__(self):
        days_display = self.get_weekdays_display()
        return f"{days_display} {self.start_time}-{self.end_time} ({self.target_temperature}°C)"
    
    def get_weekdays_list(self):
        """Obtiene la lista de días como integers"""
        if not self.weekdays:
            return []
        return [int(day.strip()) for day in self.weekdays.split(',') if day.strip().isdigit()]
    
    def get_weekdays_display(self):
        """Obtiene la representación legible de los días"""
        weekdays_dict = dict(self.WEEKDAYS)
        days = self.get_weekdays_list()
        
        if not days:
            return "Sin días"
        
        # Casos especiales para mostrar nombres más amigables
        if set(days) == {0, 1, 2, 3, 4}:  # Lunes a Viernes
            return "Laborables"
        elif set(days) == {5, 6}:  # Sábado y Domingo
            return "Fines de semana"
        elif len(days) == 7:  # Todos los días
            return "Todos los días"
        elif len(days) == 1:  # Un solo día
            return weekdays_dict.get(days[0], str(days[0]))
        else:  # Múltiples días específicos
            day_names = [weekdays_dict.get(day, str(day)) for day in sorted(days)]
            return ", ".join(day_names)
    
    def set_weekdays_from_list(self, days_list):
        """Establece los días desde una lista de integers"""
        if isinstance(days_list, list):
            self.weekdays = ','.join(str(day) for day in sorted(days_list))
        else:
            self.weekdays = str(days_list)
    
    def is_active_now(self):
        """Verifica si este horario está activo en este momento"""
        if not self.is_active:
            return False
            
        # Usar tiempo local usando timezone.localtime() nativo de Django
        now_local = timezone.localtime()  # Convierte automáticamente a zona local configurada
        current_weekday = now_local.weekday()  # 0=Monday, 6=Sunday
        current_time = now_local.time()
        
        # Verificar si el día actual está en la lista de días del horario
        weekdays_list = self.get_weekdays_list()
        if current_weekday not in weekdays_list:
            return False
        
        # Manejar horarios que cruzan medianoche
        if self.start_time <= self.end_time:
            return self.start_time <= current_time <= self.end_time
        else:
            return current_time >= self.start_time or current_time <= self.end_time
    
    @classmethod
    def get_current_active_schedule(cls):
        """Obtiene el horario activo actual"""
        for schedule in cls.objects.filter(is_active=True):
            if schedule.is_active_now():
                return schedule
        return None
    
    @classmethod
    def get_current_target_temperature(cls):
        """Obtiene la temperatura objetivo actual"""
        # Buscar horario activo
        active_schedule = cls.get_current_active_schedule()
        if active_schedule:
            return active_schedule.target_temperature
        
        # Si no hay horario activo, usar temperatura por defecto
        settings = HeatingSettings.get_current_settings()
        return settings.default_temperature if settings else 16.0
    
    @classmethod
    def create_workdays_schedule(cls, name, start_time, end_time, temperature, settings=None):
        """Crear horario para días laborables (L-V)"""
        schedule = cls.objects.create(
            name=name,
            weekdays="0,1,2,3,4",  # Lunes a Viernes
            start_time=start_time,
            end_time=end_time,
            target_temperature=temperature,
            settings=settings
        )
        return schedule
    
    @classmethod
    def create_weekend_schedule(cls, name, start_time, end_time, temperature, settings=None):
        """Crear horario para fines de semana (S-D)"""
        schedule = cls.objects.create(
            name=name,
            weekdays="5,6",  # Sábado y Domingo
            start_time=start_time,
            end_time=end_time,
            target_temperature=temperature,
            settings=settings
        )
        return schedule
    
    @classmethod
    def create_daily_schedule(cls, name, start_time, end_time, temperature, settings=None):
        """Crear horario para todos los días"""
        schedule = cls.objects.create(
            name=name,
            weekdays="0,1,2,3,4,5,6",  # Todos los días
            start_time=start_time,
            end_time=end_time,
            target_temperature=temperature,
            settings=settings
        )
        return schedule


class HeatingLog(models.Model):
    """
    Log de actividad del sistema de calefacción
    """
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Estado de la calefacción
    is_heating = models.BooleanField(help_text="¿Está encendida la calefacción?")
    
    # Temperaturas
    current_temperature = models.FloatField(null=True, blank=True, help_text="Temperatura actual (°C)")
    target_temperature = models.FloatField(null=True, blank=True, help_text="Temperatura objetivo (°C)")
    
    # Origen del cambio
    action_reason = models.CharField(
        max_length=100, 
        default="automatic",
        help_text="Razón del cambio (schedule, manual, default, etc.)"
    )
    
    # Datos adicionales del actuador (compatibilidad con mqtt_bridge)
    actuator_id = models.CharField(max_length=50, null=True, blank=True, help_text="ID del actuador")
    wifi_signal = models.IntegerField(null=True, blank=True, help_text="Señal WiFi del actuador")
    free_heap = models.BigIntegerField(null=True, blank=True, help_text="Memoria libre del actuador")
    source = models.CharField(max_length=50, default='system', help_text="Origen del log")
    
    class Meta:
        verbose_name = "Log de Calefacción"
        verbose_name_plural = "Logs de Calefacción"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['is_heating', '-timestamp']),
        ]
    
    def __str__(self):
        status = "Encendida" if self.is_heating else "Apagada"
        temp_info = f" ({self.current_temperature}°C → {self.target_temperature}°C)" if self.current_temperature else ""
        return f"{self.timestamp.strftime('%d/%m %H:%M')} - {status}{temp_info}"


import json
import paho.mqtt.client as mqtt
import threading
from django.conf import settings


class MQTTService:
    """
    Servicio para enviar comandos MQTT desde Django
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if not self.initialized:
            self.client = None
            self.connected = False
            self.mqtt_host = getattr(settings, 'MQTT_HOST', 'localhost')
            self.mqtt_port = getattr(settings, 'MQTT_PORT', 1883)
            self.mqtt_username = getattr(settings, 'MQTT_USERNAME', '')
            self.mqtt_password = getattr(settings, 'MQTT_PASSWORD', '')
            self.initialized = True
    
    def connect(self):
        """Conectar al broker MQTT"""
        try:
            if self.client is None:
                self.client = mqtt.Client()
                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect
                
                if self.mqtt_username and self.mqtt_password:
                    self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            if not self.connected:
                self.client.connect_async(self.mqtt_host, self.mqtt_port, 60)
                self.client.loop_start()

            # Añadir un retardo de 3 segundos
            import time
            time.sleep(3)
                
        except Exception as e:
            logger.error(f"Error conectando a MQTT: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info("Conectado a MQTT broker")
        else:
            logger.error(f"Error conectando a MQTT: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        logger.info("Desconectado de MQTT broker")
    
    def send_actuator_command(self, actuator_id, temperature, action):
        """
        Enviar comando al actuador via MQTT
        
        Args:
            actuator_id (str): ID del actuador (ej: 'boiler')
            temperature (float): Temperatura actual
            action (str): 'turn_on' o 'turn_off'
        """
        try:
            self.connect()
            
            topic = f"home/actuator/{actuator_id}/command"
            
            command = {
                "temperature": temperature,
                "action": action,
                "timestamp": timezone.now().isoformat()
            }
            
            message = json.dumps(command)
            
            if self.client and self.connected:
                result = self.client.publish(topic, message)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Comando enviado a {topic}: {message}")
                    return True
                else:
                    logger.error(f"Error enviando comando MQTT: {result.rc}")
            else:
                logger.error("Cliente MQTT no conectado")
                
        except Exception as e:
            logger.error(f"Error enviando comando MQTT: {e}")
        
        return False


class HeatingController:
    """
    Controlador automático de calefacción
    """
    
    @staticmethod
    def calculate_heating_decision(current_temperature, sensor_id=None):
        """
        Calcula si debe encender/apagar la calefacción basado en temperatura actual
        
        Args:
            current_temperature (float): Temperatura actual del sensor
            sensor_id (str): ID del sensor (opcional, para logs)
            
        Returns:
            dict: {
                'should_heat': bool,
                'target_temperature': float,
                'current_temperature': float,
                'reason': str,
                'hysteresis_applied': bool
            }
        """
        try:
            # Obtener configuración actual
            settings = HeatingSettings.get_current_settings()
            if not settings or not settings.is_active:
                return {
                    'should_heat': False,
                    'target_temperature': 0.0,
                    'current_temperature': current_temperature,
                    'reason': 'sistema_desactivado',
                    'hysteresis_applied': False
                }
            
            # Obtener temperatura objetivo (horarios o por defecto)
            target_temperature = HeatingSchedule.get_current_target_temperature()
            
            # Obtener último estado de calefacción
            last_log = HeatingLog.objects.first()  # Ya ordenado por -timestamp
            last_heating_state = last_log.is_heating if last_log else False
            
            # Aplicar lógica de histéresis
            hysteresis = settings.hysteresis
            should_heat = False
            hysteresis_applied = False
            reason = "temperatura_objetivo"
            
            if last_heating_state:
                # Si estaba encendida, apagar solo si temperatura > objetivo + histéresis
                if current_temperature >= target_temperature + hysteresis:
                    should_heat = False
                    reason = "temperatura_alcanzada"
                    hysteresis_applied = True
                else:
                    should_heat = True
                    reason = "manteniendo_temperatura"
            else:
                # Si estaba apagada, encender solo si temperatura < objetivo - histéresis
                if current_temperature <= target_temperature - hysteresis:
                    should_heat = True
                    reason = "temperatura_baja"
                    hysteresis_applied = True
                else:
                    should_heat = False
                    reason = "temperatura_adecuada"
            
            return {
                'should_heat': should_heat,
                'target_temperature': target_temperature,
                'current_temperature': current_temperature,
                'reason': reason,
                'hysteresis_applied': hysteresis_applied,
                'last_state': last_heating_state
            }
            
        except Exception as e:
            # En caso de error, por seguridad apagar calefacción
            logger.error(f"Error calculando decisión de calefacción: {e}")
            return {
                'should_heat': False,
                'target_temperature': 0.0,
                'current_temperature': current_temperature,
                'reason': f'error_{str(e)}',
                'hysteresis_applied': False
            }
    
    @staticmethod
    def log_heating_decision(decision_data, actuator_id=None, source='automatic_control'):
        """
        Registra la decisión de calefacción en los logs
        """
        try:
            HeatingLog.objects.create(
                is_heating=decision_data['should_heat'],
                current_temperature=decision_data['current_temperature'],
                target_temperature=decision_data['target_temperature'],
                action_reason=decision_data['reason'],
                actuator_id=actuator_id,
                source=source
            )
        except Exception as e:
            logger.error(f"Error logging heating decision: {e}")
    
    @staticmethod
    def process_sensor_reading(sensor_id, temperature):
        """
        Procesa una lectura de sensor y envía comando al actuador si es necesario
        
        Args:
            sensor_id (str): ID del sensor
            temperature (float): Temperatura leída
            
        Returns:
            dict: Información sobre la decisión tomada
        """
        try:
            # Calcular decisión
            decision = HeatingController.calculate_heating_decision(temperature, sensor_id)
            
            # Registrar en logs
            HeatingController.log_heating_decision(decision, 'boiler', 'sensor_reading')
            
            # Enviar comando MQTT al actuador
            mqtt_service = MQTTService()
            action = "turn_on" if decision['should_heat'] else "turn_off"
            
            command_sent = mqtt_service.send_actuator_command(
                actuator_id='boiler',
                temperature=temperature,
                action=action
            )
            
            logger.info(f"Sensor {sensor_id}: {temperature}°C")
            logger.info(f"{action} (target: {decision['target_temperature']}°C)")
            logger.info(f"Hysteresis applied: {decision['hysteresis_applied']}")
            
            return {
                'decision': decision,
                'command_sent': command_sent,
                'action': action,
                'actuator_id': 'boiler'
            }
            
        except Exception as e:
            logger.error(f"Error procesando lectura de sensor {sensor_id}: {e}")
            return {
                'decision': {'should_heat': False, 'reason': f'error_{str(e)}'},
                'command_sent': False,
                'action': 'turn_off',
                'actuator_id': 'boiler'
            }
