from rest_framework import serializers
from .models import HeatingSettings, HeatingSchedule, HeatingLog


class HeatingSettingsSerializer(serializers.ModelSerializer):
    """Serializer para configuración de calefacción"""
    
    class Meta:
        model = HeatingSettings
        fields = [
            'id', 'name', 'default_temperature', 'hysteresis', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class HeatingScheduleSerializer(serializers.ModelSerializer):
    """Serializer para horarios de calefacción"""
    
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    is_active_now = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = HeatingSchedule
        fields = [
            'id', 'name', 'day_of_week', 'day_name', 'start_time', 'end_time',
            'target_temperature', 'is_active', 'is_active_now', 'settings',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'day_name', 'is_active_now', 'created_at', 'updated_at']


class HeatingLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de calefacción"""
    
    class Meta:
        model = HeatingLog
        fields = [
            'id', 'timestamp', 'is_heating', 'current_temperature', 'target_temperature',
            'action_reason', 'actuator_id', 'wifi_signal', 'free_heap', 'source'
        ]
        read_only_fields = ['id', 'timestamp']


class CurrentStatusSerializer(serializers.Serializer):
    """Serializer para el estado actual del sistema"""
    
    current_temperature = serializers.FloatField(required=False)
    target_temperature = serializers.FloatField()
    is_heating = serializers.BooleanField(required=False)
    active_schedule = HeatingScheduleSerializer(required=False, allow_null=True)
    default_temperature = serializers.FloatField()
    system_active = serializers.BooleanField()
    
    def to_representation(self, instance):
        """Genera representación del estado actual"""
        # Obtener configuración actual
        settings = HeatingSettings.get_current_settings()
        
        # Obtener horario activo
        active_schedule = HeatingSchedule.get_current_active_schedule()
        
        # Obtener temperatura objetivo
        target_temp = HeatingSchedule.get_current_target_temperature()
        
        # Obtener último log para temperatura actual
        latest_log = HeatingLog.objects.first()
        
        return {
            'current_temperature': latest_log.current_temperature if latest_log else None,
            'target_temperature': target_temp,
            'is_heating': latest_log.is_heating if latest_log else False,
            'active_schedule': HeatingScheduleSerializer(active_schedule).data if active_schedule else None,
            'default_temperature': settings.default_temperature if settings else 18.0,
            'system_active': settings.is_active if settings else False,
            'last_update': latest_log.timestamp if latest_log else None
        }