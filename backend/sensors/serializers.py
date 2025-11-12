from rest_framework import serializers
from .models import SensorReading


class SensorReadingSerializer(serializers.ModelSerializer):
    """
    Serializer para lecturas de sensores.
    Acepta JSON crudo desde mqtt_bridge y crea objetos SensorReading.
    """
    
    class Meta:
        model = SensorReading
        fields = [
            'id',
            'sensor_id',
            'temperature',
            'humidity',
            'timestamp',
            'wifi_signal',
            'free_heap',
            'sensor_error',
            'source',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        """
        Crear nueva lectura de sensor.
        Si no viene source, establecer por defecto.
        """
        if 'source' not in validated_data:
            validated_data['source'] = 'mqtt_bridge'
        
        return SensorReading.objects.create(**validated_data)