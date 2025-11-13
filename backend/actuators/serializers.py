from rest_framework import serializers
from .models import ActuatorStatus


class ActuatorStatusSerializer(serializers.ModelSerializer):
    """
    Serializer para estado de actuadores.
    Acepta JSON crudo desde mqtt_bridge y crea objetos ActuatorStatus.
    """
    
    class Meta:
        model = ActuatorStatus
        fields = [
            'id',
            'actuator_id',
            'is_heating',
            'timestamp',
            'wifi_signal',
            'free_heap',
            'temperature',
            'source',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        """
        Crear nuevo estado de actuador.
        Si no viene source, establecer por defecto.
        """
        if 'source' not in validated_data:
            validated_data['source'] = 'mqtt_bridge'
        
        return ActuatorStatus.objects.create(**validated_data)