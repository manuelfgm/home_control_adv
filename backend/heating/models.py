from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime


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
        default=0.5,
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
    day_of_week = models.IntegerField(choices=WEEKDAYS, help_text="Día de la semana")
    
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
        ordering = ['day_of_week', 'start_time']
        unique_together = ['day_of_week', 'start_time', 'end_time', 'settings']
    
    def __str__(self):
        day_name = dict(self.WEEKDAYS)[self.day_of_week]
        return f"{day_name} {self.start_time}-{self.end_time} ({self.target_temperature}°C)"
    
    def is_active_now(self):
        """Verifica si este horario está activo en este momento"""
        if not self.is_active:
            return False
            
        now = timezone.now()
        current_weekday = now.weekday()  # 0=Monday, 6=Sunday
        current_time = now.time()
        
        if current_weekday != self.day_of_week:
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
        return settings.default_temperature if settings else 18.0


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
