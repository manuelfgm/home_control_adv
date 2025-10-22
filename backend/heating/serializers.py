from rest_framework import serializers
from .models import HeatingSchedule, HeatingControl, HeatingLog, TemperatureThreshold


class HeatingScheduleSerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = HeatingSchedule
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


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