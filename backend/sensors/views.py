from django.shortcuts import render
from django.utils import timezone
from django.db.models import Avg, Min, Max
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta
from .models import SensorReading, SensorStatus
from .serializers import (
    SensorReadingSerializer, 
    SensorStatusSerializer, 
    TemperatureStatsSerializer,
    SensorDataSerializer
)


class SensorReadingViewSet(viewsets.ModelViewSet):
    """ViewSet para lecturas de sensores"""
    queryset = SensorReading.objects.all()
    serializer_class = SensorReadingSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros opcionales
        sensor_id = self.request.query_params.get('sensor_id')
        sensor_type = self.request.query_params.get('sensor_type')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if sensor_id:
            queryset = queryset.filter(sensor_id=sensor_id)
        
        if sensor_type:
            queryset = queryset.filter(sensor_type=sensor_type)
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Obtiene las últimas lecturas de cada sensor"""
        sensors = SensorStatus.objects.filter(is_active=True)
        data = {}
        
        for sensor in sensors:
            latest_temp = SensorReading.objects.filter(
                sensor_id=sensor.sensor_id,
                sensor_type='temperature'
            ).order_by('-timestamp').first()
            
            latest_humidity = SensorReading.objects.filter(
                sensor_id=sensor.sensor_id,
                sensor_type='humidity'
            ).order_by('-timestamp').first()
            
            data[sensor.sensor_id] = {
                'temperature': SensorReadingSerializer(latest_temp).data if latest_temp else None,
                'humidity': SensorReadingSerializer(latest_humidity).data if latest_humidity else None,
                'status': SensorStatusSerializer(sensor).data
            }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtiene estadísticas de temperatura"""
        hours = int(request.query_params.get('hours', 24))
        sensor_id = request.query_params.get('sensor_id', 'room_sensor')
        
        since = timezone.now() - timedelta(hours=hours)
        
        readings = SensorReading.objects.filter(
            sensor_id=sensor_id,
            sensor_type='temperature',
            timestamp__gte=since
        )
        
        if not readings.exists():
            return Response({'error': 'No hay datos disponibles'}, status=404)
        
        stats = readings.aggregate(
            min_temp=Min('value'),
            max_temp=Max('value'),
            avg_temp=Avg('value')
        )
        
        latest = readings.order_by('-timestamp').first()
        
        data = {
            'min_temp': stats['min_temp'],
            'max_temp': stats['max_temp'],
            'avg_temp': round(stats['avg_temp'], 2) if stats['avg_temp'] else None,
            'current_temp': latest.value if latest else None,
            'timestamp': latest.timestamp if latest else None
        }
        
        serializer = TemperatureStatsSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def receive_data(self, request):
        """Endpoint para recibir datos de sensores"""
        serializer = SensorDataSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            sensor_id = data.get('sensor_id', 'room_sensor')
            
            # Actualizar estado del sensor
            sensor_status, created = SensorStatus.objects.get_or_create(
                sensor_id=sensor_id,
                defaults={
                    'name': f'Sensor {sensor_id}',
                    'location': 'Room',
                    'is_active': True
                }
            )
            sensor_status.last_seen = timezone.now()
            sensor_status.save()
            
            # Guardar lecturas
            if 'temp' in data:
                SensorReading.objects.create(
                    sensor_id=sensor_id,
                    sensor_type='temperature',
                    value=data['temp'],
                    unit='°C',
                    timestamp=data.get('timestamp', timezone.now())
                )
            
            if 'hum' in data:
                SensorReading.objects.create(
                    sensor_id=sensor_id,
                    sensor_type='humidity',
                    value=data['hum'],
                    unit='%',
                    timestamp=data.get('timestamp', timezone.now())
                )
            
            return Response({'status': 'success'}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SensorStatusViewSet(viewsets.ModelViewSet):
    """ViewSet para estado de sensores"""
    queryset = SensorStatus.objects.all()
    serializer_class = SensorStatusSerializer
