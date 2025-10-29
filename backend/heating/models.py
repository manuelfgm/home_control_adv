from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


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
    
    # Campos para días múltiples
    monday = models.BooleanField(default=False, verbose_name="Lunes")
    tuesday = models.BooleanField(default=False, verbose_name="Martes")
    wednesday = models.BooleanField(default=False, verbose_name="Miércoles")
    thursday = models.BooleanField(default=False, verbose_name="Jueves")
    friday = models.BooleanField(default=False, verbose_name="Viernes")
    saturday = models.BooleanField(default=False, verbose_name="Sábado")
    sunday = models.BooleanField(default=False, verbose_name="Domingo")
    
    # Mantener compatibilidad con el modelo anterior
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK, null=True, blank=True)
    
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
        ordering = ['start_time']
    
    def clean(self):
        """Validación personalizada"""
        super().clean()
        
        # Verificar que al menos un día esté seleccionado
        days_selected = any([
            self.monday, self.tuesday, self.wednesday, self.thursday,
            self.friday, self.saturday, self.sunday
        ])
        
        if not days_selected and self.day_of_week is None:
            raise ValidationError("Debe seleccionar al menos un día de la semana")
        
        # Verificar que la hora de fin sea después de la hora de inicio
        if self.start_time >= self.end_time:
            raise ValidationError("La hora de fin debe ser posterior a la hora de inicio")
        
        # Verificar conflictos de horario
        self._check_schedule_conflicts()
    
    def _check_schedule_conflicts(self):
        """Verificar que no haya conflictos con otros horarios activos"""
        if not self.is_active:
            return
        
        active_days = self.get_active_days()
        
        # Buscar horarios que se solapen
        conflicting_schedules = HeatingSchedule.objects.filter(
            is_active=True,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(pk=self.pk if self.pk else None)
        
        for schedule in conflicting_schedules:
            schedule_days = schedule.get_active_days()
            
            # Verificar si hay días en común
            common_days = set(active_days) & set(schedule_days)
            if common_days:
                day_names = [self.DAYS_OF_WEEK[day][1] for day in common_days]
                raise ValidationError(
                    f"Conflicto de horario con '{schedule.name}' en {', '.join(day_names)} "
                    f"entre {self.start_time} y {self.end_time}"
                )
    
    def get_active_days(self):
        """Retorna lista de días activos (0-6)"""
        days = []
        day_fields = [
            ('monday', 0), ('tuesday', 1), ('wednesday', 2), ('thursday', 3),
            ('friday', 4), ('saturday', 5), ('sunday', 6)
        ]
        
        for field_name, day_number in day_fields:
            if getattr(self, field_name):
                days.append(day_number)
        
        # Compatibilidad con modelo anterior
        if not days and self.day_of_week is not None:
            days.append(self.day_of_week)
        
        return days
    
    def get_active_days_display(self):
        """Retorna string con días activos"""
        days = self.get_active_days()
        if not days:
            return "Ningún día"
        
        day_names = [self.DAYS_OF_WEEK[day][1] for day in sorted(days)]
        
        # Simplificar si son días consecutivos
        if len(days) == 7:
            return "Todos los días"
        elif set(days) == {0, 1, 2, 3, 4}:  # Lun-Vie
            return "Días laborables"
        elif set(days) == {5, 6}:  # Sab-Dom
            return "Fines de semana"
        elif len(day_names) <= 3:
            return ", ".join(day_names)
        else:
            return f"{', '.join(day_names[:3])} y {len(day_names)-3} más"
    
    def is_active_on_day(self, day_of_week):
        """Verificar si el horario está activo en un día específico"""
        if not self.is_active:
            return False
        
        return day_of_week in self.get_active_days()
    
    def is_active_now(self):
        """Verificar si el horario está activo ahora mismo"""
        now = timezone.now()
        current_day = now.weekday()
        current_time = now.time()
        
        return (
            self.is_active and
            self.is_active_on_day(current_day) and
            self.start_time <= current_time <= self.end_time
        )
    
    @classmethod
    def get_current_active_schedule(cls):
        """Obtener el horario activo actual (si existe)"""
        now = timezone.now()
        current_day = now.weekday()
        current_time = now.time()
        
        # Buscar horarios activos para el día y hora actual
        schedules = cls.objects.filter(
            is_active=True,
            start_time__lte=current_time,
            end_time__gte=current_time
        )
        
        for schedule in schedules:
            if schedule.is_active_on_day(current_day):
                return schedule
        
        return None
    
    def save(self, *args, **kwargs):
        """Override save para ejecutar validaciones"""
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        days_display = self.get_active_days_display()
        return f"{self.name} - {days_display}: {self.start_time}-{self.end_time} ({self.target_temperature}°C)"


class HeatingSettings(models.Model):
    """Configuración general del sistema de calefacción"""
    
    name = models.CharField(
        max_length=100, 
        default="Configuración General", 
        help_text="Nombre descriptivo"
    )
    
    # Temperatura mínima cuando no hay horarios activos
    minimum_temperature = models.FloatField(
        default=16.0,
        validators=[MinValueValidator(5), MaxValueValidator(25)],
        help_text="Temperatura mínima cuando no hay horarios activos (°C)"
    )
    
    # Histéresis para evitar fluctuaciones
    hysteresis = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.1), MaxValueValidator(2.0)],
        help_text="Histéresis en °C para evitar encendido/apagado frecuente"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración de Calefacción"
        verbose_name_plural = "Configuraciones de Calefacción"
    
    @classmethod
    def get_settings(cls):
        """Obtener la configuración activa"""
        settings = cls.objects.filter(is_active=True).first()
        if not settings:
            # Crear configuración por defecto si no existe
            settings = cls.objects.create(
                name="Configuración por defecto",
                minimum_temperature=16.0,
                hysteresis=0.5,
                is_active=True
            )
        return settings
    
    def __str__(self):
        return f"{self.name} - Temp. mín: {self.minimum_temperature}°C"


class HeatingControl(models.Model):
    """Modelo para el estado del control de calefacción"""
    
    STATUS_CHOICES = (
        ('off', 'Apagado'),
        ('on', 'Encendido'),
        ('auto', 'Automático'),
        ('manual', 'Manual'),
        ('manual_on', 'Manual Encendido'),
        ('manual_off', 'Manual Apagado'),
        ('manual_temp', 'Manual Temperatura'),
    )
    
    controller_id = models.CharField(max_length=50, unique=True, default='main_heating')
    name = models.CharField(max_length=100, default='Calefacción Principal')
    is_heating = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='auto')
    current_temperature = models.FloatField(null=True, blank=True)
    target_temperature = models.FloatField(null=True, blank=True)
    manual_override_until = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def is_manual_override_active(self):
        """Verificar si hay override manual activo"""
        if not self.manual_override_until:
            return False
        
        return timezone.now() < self.manual_override_until
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"


class HeatingLog(models.Model):
    """Modelo para registrar eventos de calefacción"""
    
    ACTION_CHOICES = (
        ('turn_on', 'Encender'),
        ('turn_off', 'Apagar'),
        ('temperature_change', 'Cambio de temperatura'),
        ('manual_override', 'Override manual'),
        ('schedule_change', 'Cambio de horario'),
        ('system_start', 'Inicio del sistema'),
        ('system_stop', 'Parada del sistema'),
        ('error', 'Error'),
    )
    
    controller_id = models.CharField(max_length=50, default='main_heating')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    temperature = models.FloatField(null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
