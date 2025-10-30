from django.contrib import admin
from .models import HeatingSchedule, HeatingControl, HeatingLog, HeatingSettings


@admin.register(HeatingSchedule)
class HeatingScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_active_days_display', 'start_time', 'end_time', 'target_temperature', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    ordering = ('start_time',)
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'is_active')
        }),
        ('Días de la Semana', {
            'fields': (
                ('monday', 'tuesday', 'wednesday', 'thursday'),
                ('friday', 'saturday', 'sunday')
            )
        }),
        ('Horario y Temperatura', {
            'fields': ('start_time', 'end_time', 'target_temperature')
        }),
    )


@admin.register(HeatingControl)
class HeatingControlAdmin(admin.ModelAdmin):
    list_display = ('name', 'current_temperature', 'target_temperature', 'is_heating', 'status', 'last_updated')
    list_filter = ('is_heating', 'status')
    readonly_fields = ('last_updated',)


@admin.register(HeatingLog)
class HeatingLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'controller_id', 'temperature', 'reason')
    list_filter = ('action', 'controller_id', 'timestamp')
    search_fields = ('reason',)
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)


@admin.register(HeatingSettings)
class HeatingSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'minimum_temperature', 'hysteresis', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Configuración General', {
            'fields': ('name', 'is_active')
        }),
        ('Temperaturas', {
            'fields': ('minimum_temperature', 'hysteresis'),
            'description': 'Configuración de temperaturas del sistema'
        }),
    )