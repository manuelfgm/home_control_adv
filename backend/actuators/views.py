from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.db import transaction
from .models import ActuatorStatus
from .notifications import notify_heating_change
from .serializers import ActuatorStatusSerializer


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
    permission_classes = [AllowAny]  # Permite acceso desde mqtt_bridge
    
    def create(self, request, *args, **kwargs):
        """
        Crear nuevo estado de actuador.
        Acepta JSON crudo desde mqtt_bridge.
        Los HeatingLog se crean solo desde sensor readings, no desde actuator updates.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            previous_status = ActuatorStatus.objects.filter(
                actuator_id=serializer.validated_data['actuator_id']
            ).order_by('-created_at', '-pk').first()
            actuator_status = serializer.save()
            if (
                previous_status is not None
                and previous_status.is_heating != actuator_status.is_heating
            ):
                transaction.on_commit(lambda: notify_heating_change(actuator_status))
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    

    
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
