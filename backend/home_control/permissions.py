from rest_framework.permissions import BasePermission
from django.conf import settings
import os


class IsAuthenticatedOrMQTTScript(BasePermission):
    """
    Permiso personalizado que permite acceso a usuarios autenticados
    o a scripts MQTT con una clave especial.
    """
    
    def has_permission(self, request, view):
        # Si el usuario está autenticado, permitir acceso
        if request.user and request.user.is_authenticated:
            return True
            
        # Si es un script MQTT con la clave correcta, permitir acceso
        mqtt_key = request.META.get('HTTP_X_MQTT_KEY') or request.GET.get('mqtt_key')
        expected_key = os.getenv('MQTT_SCRIPT_KEY', 'default_mqtt_key_change_me')
        
        if mqtt_key and mqtt_key == expected_key:
            return True
            
        return False


class IsAuthenticatedOrReadOnlyMQTT(BasePermission):
    """
    Permiso que permite lectura a scripts MQTT y escritura solo a usuarios autenticados.
    """
    
    def has_permission(self, request, view):
        # Si el usuario está autenticado, permitir todo
        if request.user and request.user.is_authenticated:
            return True
            
        # Para métodos de lectura, verificar clave MQTT
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            mqtt_key = request.META.get('HTTP_X_MQTT_KEY') or request.GET.get('mqtt_key')
            expected_key = os.getenv('MQTT_SCRIPT_KEY', 'default_mqtt_key_change_me')
            
            if mqtt_key and mqtt_key == expected_key:
                return True
                
        return False