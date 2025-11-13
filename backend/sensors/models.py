from django.db import models
from django.utils import timezone


class SensorReading(models.Model):
    """
    Modelo para almacenar lecturas de sensores ESP
    Formato JSON recibido:
    {
        "sensor_id": "livingroom",
        "temperature": 22.5,
        "humidity": 65.2,
        "timestamp": 123456,
        "wifi_signal": -45,
        "free_heap": 25000,
        "sensor_error": false
    }
    """
    sensor_id = models.CharField(max_length=50, help_text="ID del sensor")
    temperature = models.FloatField(null=True, blank=True, help_text="Temperatura en °C")
    humidity = models.FloatField(null=True, blank=True, help_text="Humedad en %")
    timestamp = models.BigIntegerField(null=True, blank=True, help_text="Timestamp del ESP (millis)")
    wifi_signal = models.IntegerField(null=True, blank=True, help_text="Fuerza de señal WiFi (dBm)")
    free_heap = models.BigIntegerField(null=True, blank=True, help_text="Memoria libre en bytes")
    sensor_error = models.BooleanField(default=False, help_text="Error en el sensor")
    
    # Campos adicionales para compatibilidad con mqtt_bridge
    source = models.CharField(max_length=50, default='mqtt_bridge', help_text="Origen del dato")
    
    # Campo automático de creación
    created_at = models.DateTimeField(default=timezone.now, help_text="Momento de recepción")
    
    class Meta:
        verbose_name = "Lectura de Sensor"
        verbose_name_plural = "Lecturas de Sensores"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sensor_id', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.sensor_id} - {self.temperature}°C - {self.created_at}"
    
    def save(self, *args, **kwargs):
        """
        Sobrescribir save para procesar automáticamente la lectura de temperatura
        """
        # Guardar primero la lectura
        super().save(*args, **kwargs)
        
        # Si tenemos temperatura, procesar control de calefacción
        if self.temperature is not None:
            try:
                # Importar aquí para evitar importaciones circulares
                from heating.models import HeatingController
                
                # Procesar la lectura para control automático
                result = HeatingController.process_sensor_reading(
                    sensor_id=self.sensor_id,
                    temperature=self.temperature
                )
                
                print(f"🌡️ Sensor {self.sensor_id}: {self.temperature}°C -> Acción: {result.get('action', 'none')}")
                
            except Exception as e:
                print(f"❌ Error procesando control automático: {e}")
