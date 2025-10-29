from django.contrib import admin
from .models import HeatingSchedule, HeatingControl, HeatingLog, TemperatureThreshold, TemperatureProfile


@admin.register(HeatingSchedule)
class HeatingScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_active_days_display', 'start_time', 'end_time', 'target_temperature', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    ordering = ('start_time',)


@admin.register(HeatingControl)
class HeatingControlAdmin(admin.ModelAdmin):
    list_display = ('name', 'current_temperature', 'target_temperature', 'is_heating', 'status', 'last_updated')
    list_filter = ('is_heating', 'status')
    readonly_fields = ('last_updated',)


@admin.register(HeatingLog)
class HeatingLogAdmin(admin.ModelAdmin):
    list_display = ('controller_id', 'action', 'temperature', 'reason', 'timestamp')
    list_filter = ('action', 'controller_id', 'timestamp')
    search_fields = ('reason',)
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp',)


@admin.register(TemperatureThreshold)
class TemperatureThresholdAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_temperature', 'max_temperature', 'hysteresis', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(TemperatureProfile)
class TemperatureProfileAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'profile_type', 'min_temperature', 'default_comfort_temperature', 
        'night_temperature', 'is_active', 'is_default'
    )
    list_filter = ('profile_type', 'is_active', 'is_default', 'auto_activate_weekdays', 'auto_activate_weekends')
    search_fields = ('name',)
    ordering = ('name',)
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'profile_type')
        }),
        ('Temperaturas', {
            'fields': ('min_temperature', 'default_comfort_temperature', 'night_temperature')
        }),
        ('Horarios Nocturnos', {
            'fields': ('night_start_time', 'night_end_time')
        }),
        ('Activación Automática', {
            'fields': ('auto_activate_weekdays', 'auto_activate_weekends')
        }),
        ('Estado', {
            'fields': ('is_active', 'is_default')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Personalizar guardado para manejar perfil por defecto"""
        # Si se marca como predeterminado, desmarcar otros
        if obj.is_default:
            TemperatureProfile.objects.filter(is_default=True).update(is_default=False)
        
        super().save_model(request, obj, form, change)
