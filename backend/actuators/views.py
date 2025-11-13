from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import ActuatorStatus, ActuatorReadings
from .serializers import ActuatorStatusSerializer, ActuatorReadingsSerializer


class ActuatorStatusViewSet(viewsets.ModelViewSet):
    """
    ViewSet para estado de actuadores.
    Endpoints:
    - GET /actuators/api/status/ - Listar todos los estados
    - POST /actuators/api/status/ - Crear nuevo estado (usado por mqtt_bridge)
    - GET /actuators/api/status/{id}/ - Detalle de un estado
    """
    queryset = ActuatorStatus.objects.all()
    serializer_class = ActuatorStatusSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Crear nuevo estado de actuador.
        Acepta JSON crudo desde mqtt_bridge y crea log de calefacción.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Crear el estado del actuador
        actuator_status = serializer.save()
        
        # Crear log de calefacción automáticamente
        self._create_heating_log(actuator_status)
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    
    def _create_heating_log(self, actuator_status):
        """Crear log de calefacción basado en el estado del actuador"""
        try:
            # Importar aquí para evitar imports circulares
            from heating.models import HeatingLog, HeatingSchedule
            
            # Obtener temperatura objetivo actual
            target_temp = HeatingSchedule.get_current_target_temperature()
            
            # Crear log
            HeatingLog.objects.create(
                is_heating=actuator_status.is_heating,
                current_temperature=actuator_status.temperature,
                target_temperature=target_temp,
                action_reason='actuator_update',
                actuator_id=actuator_status.actuator_id,
                wifi_signal=actuator_status.wifi_signal,
                free_heap=actuator_status.free_heap,
                source='mqtt_bridge'
            )
        except Exception as e:
            # Log error pero no fallar la creación del actuator status
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creando heating log: {e}")
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Obtener el estado actual de todos los actuadores.
        GET /actuators/api/status/current/
        """
        current_status = {}
        actuators = ActuatorStatus.objects.values_list('actuator_id', flat=True).distinct()
        
        for actuator_id in actuators:
            latest = ActuatorStatus.objects.filter(
                actuator_id=actuator_id
            ).first()
            if latest:
                current_status[actuator_id] = ActuatorStatusSerializer(latest).data
        
        return Response(current_status)
    
    @action(detail=False, methods=['get'])
    def by_actuator(self, request):
        """
        Filtrar estados por actuator_id.
        GET /actuators/api/status/by_actuator/?actuator_id=boiler
        """
        actuator_id = request.query_params.get('actuator_id')
        if not actuator_id:
            return Response(
                {'error': 'actuator_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        statuses = ActuatorStatus.objects.filter(actuator_id=actuator_id)
        serializer = self.get_serializer(statuses, many=True)
        return Response(serializer.data)


class ActuatorReadingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet para lecturas continuas de actuadores (NO dispara control automático)
    Endpoints:
    - GET /actuators/api/readings/ - Listar todas las lecturas
    - POST /actuators/api/readings/ - Crear nueva lectura (usado por mqtt_bridge)
    - GET /actuators/api/readings/{id}/ - Detalle de una lectura
    """
    queryset = ActuatorReadings.objects.all()
    serializer_class = ActuatorReadingsSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Crear nueva lectura de actuador (sin disparar control automático).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Crear la lectura del actuador (NO dispara control automático)
        reading = serializer.save()
        
        return Response(
            ActuatorReadingsSerializer(reading).data, 
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Obtener última lectura de cada actuador.
        GET /actuators/api/readings/latest/
        """
        # Obtener lista de actuadores únicos
        actuator_ids = ActuatorReadings.objects.values_list('actuator_id', flat=True).distinct()
        
        latest_readings = {}
        for actuator_id in actuator_ids:
            latest = ActuatorReadings.objects.filter(actuator_id=actuator_id).first()
            if latest:
                latest_readings[actuator_id] = ActuatorReadingsSerializer(latest).data
        
        return Response(latest_readings)
    
    @action(detail=False, methods=['get'])
    def by_actuator(self, request):
        """
        Filtrar lecturas por actuator_id.
        GET /actuators/api/readings/by_actuator/?actuator_id=boiler
        """
        actuator_id = request.query_params.get('actuator_id')
        if not actuator_id:
            return Response(
                {'error': 'actuator_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        readings = ActuatorReadings.objects.filter(actuator_id=actuator_id)
        serializer = self.get_serializer(readings, many=True)
        return Response(serializer.data)
