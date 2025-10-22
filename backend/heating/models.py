from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class HeatingSchedule(models.Model):
    """Modelo para configurar horarios de calefacción"""
    
    DAYS_OF_WEEK = (
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    )
    
    name = models.CharField(max_length=100, help_text="Nombre descriptivo para el horario")
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField(help_text="Hora de inicio")
    end_time = models.TimeField(help_text="Hora de fin")
    target_temperature = models.FloatField(
        validators=[MinValueValidator(5), MaxValueValidator(35)],
        help_text="Temperatura objetivo en °C"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['day_of_week', 'start_time', 'end_time']
    
    def __str__(self):
        return f"{self.name} - {self.get_day_of_week_display()}: {self.start_time}-{self.end_time} ({self.target_temperature}°C)"


class HeatingControl(models.Model):
    """Modelo para el estado del control de calefacción"""
    
    STATUS_CHOICES = (
        ('off', 'Apagado'),
        ('on', 'Encendido'),
        ('auto', 'Automático'),
        ('manual', 'Manual'),
    )
    
    controller_id = models.CharField(max_length=50, unique=True, default='main_heating')
    name = models.CharField(max_length=100, default='Calefacción Principal')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='auto')
    is_heating = models.BooleanField(default=False)
    current_temperature = models.FloatField(null=True, blank=True)
    target_temperature = models.FloatField(null=True, blank=True)
    manual_override = models.BooleanField(default=False)
    manual_override_until = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Heating controls"
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    def is_manual_override_active(self):
        """Verifica si el override manual está activo"""
        if not self.manual_override:
            return False
        if self.manual_override_until and timezone.now() > self.manual_override_until:
            return False
        return True


class HeatingLog(models.Model):
    """Modelo para registrar el histórico de la calefacción"""
    
    ACTION_CHOICES = (
        ('turn_on', 'Encendido'),
        ('turn_off', 'Apagado'),
        ('schedule_start', 'Inicio programado'),
        ('schedule_end', 'Fin programado'),
        ('manual_override', 'Override manual'),
        ('temperature_reached', 'Temperatura alcanzada'),
    )
    
    controller_id = models.CharField(max_length=50, default='main_heating')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)
    temperature_before = models.FloatField(null=True, blank=True)
    temperature_after = models.FloatField(null=True, blank=True)
    target_temperature = models.FloatField(null=True, blank=True)
    reason = models.TextField(blank=True, help_text="Razón del cambio")
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="Duración en minutos (para acciones de apagado)")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['controller_id', 'action']),
        ]
    
    def __str__(self):
        return f"{self.controller_id} - {self.get_action_display()} at {self.timestamp}"


class TemperatureThreshold(models.Model):
    """Modelo para configurar umbrales de temperatura"""
    
    name = models.CharField(max_length=100, unique=True)
    high_temperature = models.FloatField(
        validators=[MinValueValidator(10), MaxValueValidator(40)],
        help_text="Temperatura alta en °C"
    )
    low_temperature = models.FloatField(
        validators=[MinValueValidator(5), MaxValueValidator(35)],
        help_text="Temperatura baja en °C"
    )
    hysteresis = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.1), MaxValueValidator(5)],
        help_text="Histéresis en °C para evitar conmutación frecuente"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name}: {self.low_temperature}°C - {self.high_temperature}°C"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.low_temperature >= self.high_temperature:
            raise ValidationError('La temperatura baja debe ser menor que la temperatura alta')
