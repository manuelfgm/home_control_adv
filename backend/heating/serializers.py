from rest_framework import serializers
from .models import HeatingSchedule, HeatingControl, HeatingLog, TemperatureThreshold, TemperatureProfile


class HeatingScheduleSerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    active_days = serializers.SerializerMethodField()
    active_days_display = serializers.SerializerMethodField()
    
    class Meta:
        model = HeatingSchedule
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_active_days(self, obj):
        return obj.get_active_days()
    
    def get_active_days_display(self, obj):
        return obj.get_active_days_display()
    
    def validate(self, data):
        """Validación personalizada para horarios"""
        # Verificar que al menos un día esté seleccionado
        days_selected = any([
            data.get('monday', False), data.get('tuesday', False), 
            data.get('wednesday', False), data.get('thursday', False),
            data.get('friday', False), data.get('saturday', False), 
            data.get('sunday', False)
        ])
        
        if not days_selected and data.get('day_of_week') is None:
            raise serializers.ValidationError("Debe seleccionar al menos un día de la semana")
        
        # Verificar que la hora de fin sea después de la hora de inicio
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("La hora de fin debe ser posterior a la hora de inicio")
        
        return data


class HeatingControlSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_manual_override_active = serializers.SerializerMethodField()
    
    class Meta:
        model = HeatingControl
        fields = '__all__'
        read_only_fields = ('last_updated',)
    
    def get_is_manual_override_active(self, obj):
        return obj.is_manual_override_active()


class HeatingLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = HeatingLog
        fields = '__all__'
        read_only_fields = ('timestamp',)


class TemperatureThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemperatureThreshold
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TemperatureProfileSerializer(serializers.ModelSerializer):
    profile_type_display = serializers.CharField(source='get_profile_type_display', read_only=True)
    is_night_time_now = serializers.SerializerMethodField()
    current_target_temperature = serializers.SerializerMethodField()
    
    class Meta:
        model = TemperatureProfile
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_is_night_time_now(self, obj):
        """Verificar si actualmente es horario nocturno"""
        return obj.is_night_time()
    
    def get_current_target_temperature(self, obj):
        """Obtener temperatura objetivo actual"""
        return obj.get_target_temperature()
    
    def validate(self, data):
        """Validación personalizada"""
        min_temp = data.get('min_temperature', 0)
        comfort_temp = data.get('default_comfort_temperature', 20)
        night_temp = data.get('night_temperature', 17)
        
        if min_temp >= comfort_temp:
            raise serializers.ValidationError({
                'min_temperature': 'La temperatura mínima debe ser menor que la de confort'
            })
        
        if night_temp < min_temp:
            raise serializers.ValidationError({
                'night_temperature': 'La temperatura nocturna no puede ser menor que la mínima'
            })
        
        return data


class ManualOverrideSerializer(serializers.Serializer):
    """Serializer para control manual de calefacción"""
    turn_on = serializers.BooleanField()
    duration_hours = serializers.IntegerField(required=False, min_value=1, max_value=24)


class HeatingStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de calefacción"""
    total_runtime_hours = serializers.FloatField()
    total_cycles = serializers.IntegerField()
    avg_cycle_duration = serializers.FloatField()
    efficiency_percent = serializers.FloatField()
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()


class ProfileActivationSerializer(serializers.Serializer):
    """Serializer para activar/desactivar perfiles"""
    profile_id = serializers.IntegerField()
    activate = serializers.BooleanField(default=True)