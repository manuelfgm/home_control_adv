# Settings package initialization
from .base import *

# Determinar qué configuración usar basado en la variable de entorno
import os

env = os.getenv('DJANGO_SETTINGS_MODULE', 'home_control.settings.development')

if 'production' in env:
    from .production import *
elif 'docker' in env:
    from .docker import *
else:
    from .development import *