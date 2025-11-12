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
    list_display = ['name', 'get_day_display', 'start_time', 'end_time', 'target_temperature', 'is_active']
    list_filter = ['day_of_week', 'is_active', 'settings']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['day_of_week', 'start_time']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'settings', 'is_active')
        }),
        ('Horario', {
            'fields': ('day_of_week', 'start_time', 'end_time')
        }),
        ('Temperatura', {
            'fields': ('target_temperature',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_day_display(self, obj):
        return obj.get_day_of_week_display()
    get_day_display.short_description = 'Día'


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
