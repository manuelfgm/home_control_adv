from django.db import models
from django.utils import timezone


class ActuatorStatus(models.Model):
    """
    Modelo para almacenar estado de actuadores ESP
    Formato JSON recibido:
    {
        "actuator_id": "boiler",
        "is_heating": true,
        "timestamp": 123456,
        "wifi_signal": -45,
        "free_heap": 25000,
        "temperature": 22.5
    }
    """
    actuator_id = models.CharField(max_length=50, help_text="ID del actuador")
    is_heating = models.BooleanField(default=False, help_text="¿Está encendida la calefacción?")
    timestamp = models.BigIntegerField(null=True, blank=True, help_text="Timestamp del ESP (millis)")
    wifi_signal = models.IntegerField(null=True, blank=True, help_text="Fuerza de señal WiFi (dBm)")
    free_heap = models.BigIntegerField(null=True, blank=True, help_text="Memoria libre en bytes")
    temperature = models.FloatField(null=True, blank=True, help_text="Temperatura del actuador en °C")
    
    # Campos adicionales para compatibilidad
    source = models.CharField(max_length=50, default='mqtt_bridge', help_text="Origen del dato")
    
    # Campo automático de creación
    created_at = models.DateTimeField(default=timezone.now, help_text="Momento de recepción")
    
    class Meta:
        verbose_name = "Estado de Actuador"
        verbose_name_plural = "Estados de Actuadores"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actuator_id', '-created_at']),
        ]
    
    def __str__(self):
        status = "Encendido" if self.is_heating else "Apagado"
        return f"{self.actuator_id} - {status} - {self.created_at}"


class ActuatorReadings(models.Model):
    """
    Modelo separado para lecturas continuas de actuadores (no comandos)
    Este modelo NO dispara control automático para evitar bucles
    """
    actuator_id = models.CharField(max_length=50, help_text="ID del actuador")
    is_heating = models.BooleanField(default=False, help_text="Estado actual de calefacción")
    temperature = models.FloatField(null=True, blank=True, help_text="Temperatura actual en °C")
    timestamp = models.BigIntegerField(null=True, blank=True, help_text="Timestamp del ESP (millis)")
    wifi_signal = models.IntegerField(null=True, blank=True, help_text="Señal WiFi (dBm)")
    free_heap = models.BigIntegerField(null=True, blank=True, help_text="Memoria libre en bytes")
    
    # Metadata
    source = models.CharField(max_length=50, default='mqtt_bridge', help_text="Origen del dato")
    created_at = models.DateTimeField(default=timezone.now, help_text="Momento de recepción")
    
    # Campo para identificar si es una lectura automática (no comando)
    reading_type = models.CharField(
        max_length=20, 
        choices=[
            ('status_report', 'Reporte de Estado'),
            ('response_to_command', 'Respuesta a Comando'),
            ('periodic_reading', 'Lectura Periódica')
        ],
        default='periodic_reading',
        help_text="Tipo de lectura para evitar bucles"
    )
    
    class Meta:
        verbose_name = "Lectura de Actuador"
        verbose_name_plural = "Lecturas de Actuadores"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actuator_id', '-created_at']),
            models.Index(fields=['reading_type', '-created_at']),
        ]
    
    def __str__(self):
        status = "🔥" if self.is_heating else "❄️"
        return f"{self.actuator_id} {status} {self.temperature}°C - {self.created_at.strftime('%H:%M:%S')}"
