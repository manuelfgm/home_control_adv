from rest_framework import serializers
from .models import SensorReading, SensorStatus


class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = '__all__'
        read_only_fields = ('timestamp',)


class SensorStatusSerializer(serializers.ModelSerializer):
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = SensorStatus
        fields = '__all__'
        read_only_fields = ('last_seen',)
    
    def get_is_online(self, obj):
        return obj.is_online()


class TemperatureStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de temperatura"""
    min_temp = serializers.FloatField()
    max_temp = serializers.FloatField()
    avg_temp = serializers.FloatField()
    current_temp = serializers.FloatField()
    timestamp = serializers.DateTimeField()


class SensorDataSerializer(serializers.Serializer):
    """Serializer para recibir datos de sensores via API"""
    sensor_id = serializers.CharField(max_length=50, default='room_sensor')
    temp = serializers.FloatField(required=False)
    hum = serializers.FloatField(required=False)
    timestamp = serializers.DateTimeField(required=False)