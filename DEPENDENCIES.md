# 📦 Dependencias del Proyecto

Este archivo documenta todas las dependencias instaladas y su propósito.

## 🚀 Instalación Rápida

```bash
# 1. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar todas las dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Edita .env con tus configuraciones

# 4. Configurar Django
cd backend
python manage.py migrate
python manage.py createsuperuser

# 5. Ejecutar el sistema
python manage.py runserver &          # Django backend
cd .. && python mqtt_bridge.py        # MQTT Bridge
```

## 📋 Dependencias Principales

### Django Framework
- **Django==5.2.8** - Framework web principal
- **djangorestframework==3.16.1** - API REST
- **asgiref==3.10.0** - Soporte ASGI
- **sqlparse==0.5.3** - Parser SQL para Django

### MQTT Bridge
- **paho-mqtt==2.1.0** - Cliente MQTT para ESP8266/ESP32
- **requests==2.32.5** - Cliente HTTP para enviar datos a Django
- **python-dotenv==1.2.1** - Cargar variables de entorno desde .env

### HTTP Dependencies
- **certifi==2025.11.12** - Certificados SSL/TLS
- **charset-normalizer==3.4.4** - Detección de encoding
- **idna==3.11** - Soporte dominios internacionales
- **urllib3==2.5.0** - Cliente HTTP low-level

## 🔧 Funcionalidades por Dependencia

| Dependencia | Usado por | Propósito |
|-------------|-----------|-----------|
| Django | Backend | Framework web principal |
| djangorestframework | Backend | API REST para sensores/actuadores |
| paho-mqtt | mqtt_bridge.py | Comunicación con dispositivos ESP |
| requests | mqtt_bridge.py | Enviar datos de MQTT a Django |
| python-dotenv | mqtt_bridge.py | Configuración desde .env |

## 🧪 Verificación de Instalación

```bash
# Verificar Django
cd backend && python manage.py check

# Verificar MQTT Bridge
python -c "import mqtt_bridge; print('✅ MQTT Bridge OK')"

# Verificar todas las importaciones
python -c "
import django
import rest_framework
import paho.mqtt.client
import requests
import dotenv
print('✅ Todas las dependencias instaladas correctamente')
"
```

## 🔄 Actualización de Dependencias

```bash
# Ver dependencias desactualizadas
pip list --outdated

# Actualizar todas las dependencias
pip install --upgrade -r requirements.txt

# Regenerar requirements.txt después de cambios
pip freeze > requirements.txt
```

## 🐳 Docker (Opcional)

Si prefieres usar Docker, las dependencias se instalan automáticamente:

```bash
docker-compose up --build
```

## ❓ Problemas Comunes

### Error: ModuleNotFoundError
```bash
# Asegúrate de activar el entorno virtual
source .venv/bin/activate
pip install -r requirements.txt
```

### Error: paho-mqtt connection failed
```bash
# Verifica la configuración MQTT en .env
MQTT_HOST=tu-ip-mqtt
MQTT_PORT=1883
```

### Error: Django database
```bash
# Ejecuta las migraciones
cd backend
python manage.py migrate
```