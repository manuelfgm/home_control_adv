from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from .models import SensorReading
from .serializers import SensorReadingSerializer


class SensorReadingViewSet(viewsets.ModelViewSet):
    """
    ViewSet para lecturas de sensores.
    Endpoints:
    - GET /sensors/api/readings/ - Listar todas las lecturas
    - POST /sensors/api/readings/ - Crear nueva lectura (usado por mqtt_bridge)
    - GET /sensors/api/readings/{id}/ - Detalle de una lectura
    """
    queryset = SensorReading.objects.all()
    serializer_class = SensorReadingSerializer
    permission_classes = [AllowAny]  # Permite acceso desde mqtt_bridge
    
    def create(self, request, *args, **kwargs):
        """
        Crear nueva lectura de sensor.
        Acepta JSON crudo desde mqtt_bridge.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Obtener las últimas lecturas por sensor.
        GET /sensors/api/readings/latest/
        """
        latest_readings = {}
        sensors = SensorReading.objects.values_list('sensor_id', flat=True).distinct()
        
        for sensor_id in sensors:
            latest = SensorReading.objects.filter(
                sensor_id=sensor_id
            ).first()
            if latest:
                latest_readings[sensor_id] = SensorReadingSerializer(latest).data
        
        return Response(latest_readings)
    
    @action(detail=False, methods=['get'])
    def by_sensor(self, request):
        """
        Filtrar lecturas por sensor_id.
        GET /sensors/api/readings/by_sensor/?sensor_id=livingroom
        """
        sensor_id = request.query_params.get('sensor_id')
        if not sensor_id:
            return Response(
                {'error': 'sensor_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        readings = SensorReading.objects.filter(sensor_id=sensor_id)
        serializer = self.get_serializer(readings, many=True)
        return Response(serializer.data)
