from django.contrib import admin
from .models import HeatingSettings, HeatingSchedule, HeatingLog


@admin.register(HeatingSettings)
class HeatingSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'default_temperature', 'hysteresis', 'is_active', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'is_active')
        }),
        ('Configuración de Temperatura', {
            'fields': ('default_temperature', 'hysteresis')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HeatingSchedule)
class HeatingScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_weekdays_display', 'start_time', 'end_time', 'target_temperature', 'is_active']
    list_filter = ['is_active', 'settings']
    search_fields = ['name', 'weekdays']
    readonly_fields = ['created_at', 'updated_at', 'weekdays_display_admin']
    ordering = ['start_time']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'settings', 'is_active')
        }),
        ('Días de la Semana', {
            'fields': ('weekdays', 'weekdays_display_admin'),
            'description': 'Días separados por comas: 0=Lunes, 1=Martes, ..., 6=Domingo. Ejemplos: "0,1,2,3,4" (laborables), "5,6" (fines de semana)'
        }),
        ('Horario', {
            'fields': ('start_time', 'end_time')
        }),
        ('Temperatura', {
            'fields': ('target_temperature',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def weekdays_display_admin(self, obj):
        """Mostrar días de forma legible en el admin"""
        return obj.get_weekdays_display()
    weekdays_display_admin.short_description = 'Días (legible)'


@admin.register(HeatingLog)
class HeatingLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'is_heating', 'current_temperature', 'target_temperature', 'action_reason', 'source']
    list_filter = ['is_heating', 'action_reason', 'source', 'timestamp']
    search_fields = ['action_reason', 'actuator_id']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Estado', {
            'fields': ('timestamp', 'is_heating', 'action_reason')
        }),
        ('Temperaturas', {
            'fields': ('current_temperature', 'target_temperature')
        }),
        ('Información del Actuador', {
            'fields': ('actuator_id', 'wifi_signal', 'free_heap', 'source'),
            'classes': ('collapse',)
        }),
    )
