#!/bin/bash

# ==============================================
# INSTALACIÓN HOME CONTROL EN RASPBERRY PI
# ==============================================

set -e

echo "🍓 Instalando Home Control Advanced en Raspberry Pi..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
PROJECT_DIR="/home/pi/home_control"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_USER="pi"

# Función para imprimir mensajes
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que se ejecuta como root para instalaciones del sistema
if [[ $EUID -eq 0 ]]; then
    print_warning "Este script se está ejecutando como root"
else
    print_error "Este script debe ejecutarse como root para instalar dependencias del sistema"
    echo "Usa: sudo $0"
    exit 1
fi

# 1. Actualizar sistema
print_status "Actualizando sistema..."
apt update && apt upgrade -y

# 2. Instalar dependencias del sistema
print_status "Instalando dependencias del sistema..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    mosquitto \
    mosquitto-clients \
    git \
    sqlite3 \
    nginx \
    supervisor \
    curl \
    htop \
    vim

# 3. Configurar Mosquitto
print_status "Configurando Mosquitto MQTT..."
systemctl stop mosquitto

# Crear directorios necesarios
mkdir -p /var/log/mosquitto
chown mosquitto:mosquitto /var/log/mosquitto
chmod 755 /var/log/mosquitto

# Copiar configuración si existe
if [ -f "$PROJECT_DIR/mosquitto_local.conf" ]; then
    cp "$PROJECT_DIR/mosquitto_local.conf" /etc/mosquitto/conf.d/home_control.conf
else
    print_warning "Archivo de configuración Mosquitto no encontrado, usando configuración por defecto"
fi

# Habilitar y arrancar Mosquitto
systemctl enable mosquitto
systemctl start mosquitto

# 4. Crear usuario y directorio del proyecto (si no existe)
if ! id "$SERVICE_USER" &>/dev/null; then
    print_status "Creando usuario $SERVICE_USER..."
    useradd -m -s /bin/bash "$SERVICE_USER"
    usermod -aG sudo "$SERVICE_USER"
fi

# 5. Configurar proyecto Django
print_status "Configurando proyecto Django..."
sudo -u "$SERVICE_USER" bash << EOF
set -e

# Crear directorio del proyecto
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Crear entorno virtual
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Actualizar pip
pip install --upgrade pip

# Crear requirements.txt si no existe
if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt << 'REQS'
Django==4.2.7
djangorestframework==3.14.0
django-cors-headers==4.3.1
whitenoise==6.6.0
python-dotenv==1.0.0
paho-mqtt==1.6.1
requests==2.31.0
gunicorn==21.2.0
REQS
fi

# Instalar dependencias Python
pip install -r requirements.txt

# Crear estructura básica si no existe
if [ ! -f "manage.py" ]; then
    echo "⚠️  Proyecto Django no encontrado. Crear manualmente o copiar desde repositorio."
fi

EOF

# 6. Configurar variables de entorno
print_status "Configurando variables de entorno..."
sudo -u "$SERVICE_USER" bash << 'EOF'
cat > "$PROJECT_DIR/.env" << 'ENVFILE'
# Configuración para Raspberry Pi
DJANGO_SETTINGS_MODULE=home_control.settings.raspberry_pi
DEBUG=False
SECRET_KEY=change-this-in-production-make-it-very-long-and-random
ALLOWED_HOSTS=localhost,127.0.0.1,raspberrypi.local,192.168.1.*

# MQTT Configuration
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_CLIENT_ID=rpi_home_control

# Django API Key para MQTT bridge
DJANGO_API_KEY=your-secure-api-key-here

# URLs
DJANGO_URL=http://localhost:8000

# Logs
LOG_LEVEL=INFO
ENVFILE
EOF

# 7. Crear logs directory
print_status "Configurando directorios de logs..."
mkdir -p /var/log/home_control
chown "$SERVICE_USER:$SERVICE_USER" /var/log/home_control
chmod 755 /var/log/home_control

# 8. Verificar instalación
print_status "Verificando instalación..."

# Verificar Mosquitto
if systemctl is-active --quiet mosquitto; then
    print_status "✅ Mosquitto está funcionando"
else
    print_error "❌ Mosquitto no está funcionando"
fi

# Verificar Python
if sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" --version; then
    print_status "✅ Python está funcionando"
else
    print_error "❌ Python no está funcionando"
fi

# 9. Instrucciones finales
print_status "Instalación completada!"
echo ""
echo "========================================="
echo "🎉 INSTALACIÓN COMPLETADA"
echo "========================================="
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Copiar código del proyecto Django a: $PROJECT_DIR/backend/"
echo "2. Configurar la base de datos:"
echo "   sudo -u $SERVICE_USER bash"
echo "   cd $PROJECT_DIR"
echo "   source venv/bin/activate"
echo "   python backend/manage.py migrate"
echo "   python backend/manage.py createsuperuser"
echo ""
echo "3. Copiar y configurar mqtt_bridge.py:"
echo "   cp mqtt_bridge.py $PROJECT_DIR/"
echo ""
echo "4. Crear servicios systemd:"
echo "   sudo ./install_services.sh"
echo ""
echo "5. Verificar servicios:"
echo "   sudo systemctl status mosquitto"
echo "   mosquitto_pub -h localhost -t test -m 'Hello World'"
echo "   mosquitto_sub -h localhost -t test"
echo ""
echo "📱 URLs de acceso:"
echo "   Dashboard: http://$(hostname -I | awk '{print $1}'):8000/"
echo "   Admin: http://$(hostname -I | awk '{print $1}'):8000/admin/"
echo ""
echo "🔧 Configuración en: $PROJECT_DIR/.env"
echo "📋 Logs en: /var/log/home_control/"
echo ""