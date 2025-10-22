from django.db import models
from django.utils import timezone


class SensorReading(models.Model):
    """Modelo para almacenar las lecturas de sensores de temperatura y humedad"""
    
    SENSOR_TYPES = (
        ('temperature', 'Temperature'),
        ('humidity', 'Humidity'),
    )
    
    sensor_id = models.CharField(max_length=50, default='room_sensor')
    sensor_type = models.CharField(max_length=20, choices=SENSOR_TYPES)
    value = models.FloatField()
    unit = models.CharField(max_length=10, default='°C')
    timestamp = models.DateTimeField(default=timezone.now)
    location = models.CharField(max_length=100, default='Room')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['sensor_id', 'sensor_type']),
        ]
    
    def __str__(self):
        return f"{self.sensor_id} - {self.sensor_type}: {self.value}{self.unit} at {self.timestamp}"


class SensorStatus(models.Model):
    """Modelo para el estado de los sensores"""
    
    sensor_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    battery_level = models.IntegerField(null=True, blank=True, help_text="Battery level in percentage")
    
    class Meta:
        verbose_name_plural = "Sensor statuses"
    
    def __str__(self):
        return f"{self.name} ({self.sensor_id})"
    
    def is_online(self):
        """Verifica si el sensor está online (última lectura hace menos de 1 hora)"""
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).total_seconds() < 3600
