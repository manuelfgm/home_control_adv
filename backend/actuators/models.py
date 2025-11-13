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
