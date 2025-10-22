from django.db import models
from django.utils import timezone


class DashboardConfig(models.Model):
    """Configuración general del dashboard"""
    
    name = models.CharField(max_length=100, unique=True)
    refresh_interval = models.IntegerField(default=30, help_text="Intervalo de actualización en segundos")
    temperature_unit = models.CharField(max_length=2, choices=[('C', '°C'), ('F', '°F')], default='C')
    show_humidity = models.BooleanField(default=True)
    show_heating_status = models.BooleanField(default=True)
    data_retention_days = models.IntegerField(default=365, help_text="Días para mantener datos históricos")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Dashboard configurations"
    
    def __str__(self):
        return self.name


class Alert(models.Model):
    """Modelo para alertas del sistema"""
    
    ALERT_TYPES = (
        ('sensor_offline', 'Sensor Offline'),
        ('temperature_high', 'Temperatura Alta'),
        ('temperature_low', 'Temperatura Baja'),
        ('heating_failure', 'Fallo de Calefacción'),
        ('system_error', 'Error del Sistema'),
    )
    
    SEVERITY_LEVELS = (
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    )
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    is_acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'severity']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_severity_display()} - {self.title}"
