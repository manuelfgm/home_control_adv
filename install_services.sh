#!/bin/bash

# ==============================================
# INSTALACIÓN DE SERVICIOS SYSTEMD
# ==============================================

set -e

echo "🔧 Instalando servicios systemd para Home Control..."

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que se ejecuta como root
if [[ $EUID -ne 0 ]]; then
    print_error "Este script debe ejecutarse como root"
    echo "Usa: sudo $0"
    exit 1
fi

PROJECT_DIR="/home/pi/home_control"
SERVICE_USER="pi"

# 1. Crear directorio de logs si no existe
print_status "Configurando directorios de logs..."
mkdir -p /var/log/home_control
chown "$SERVICE_USER:$SERVICE_USER" /var/log/home_control
chmod 755 /var/log/home_control

# 2. Copiar archivos de servicio
print_status "Instalando servicios systemd..."

# Copiar servicios
cp home-control-django.service /etc/systemd/system/
cp home-control-mqtt-bridge.service /etc/systemd/system/

# Establecer permisos correctos
chmod 644 /etc/systemd/system/home-control-*.service

# 3. Recargar systemd
print_status "Recargando configuración systemd..."
systemctl daemon-reload

# 4. Habilitar servicios
print_status "Habilitando servicios..."
systemctl enable home-control-django.service
systemctl enable home-control-mqtt-bridge.service

# 5. Verificar configuración de Django
print_status "Verificando configuración Django..."
if [ ! -f "$PROJECT_DIR/backend/manage.py" ]; then
    print_warning "⚠️  manage.py no encontrado en $PROJECT_DIR/backend/"
    print_warning "Asegúrate de copiar el código Django antes de iniciar servicios"
fi

if [ ! -f "$PROJECT_DIR/.env" ]; then
    print_warning "⚠️  Archivo .env no encontrado"
    print_warning "Copia y configura el archivo .env antes de iniciar servicios"
fi

if [ ! -f "$PROJECT_DIR/mqtt_bridge.py" ]; then
    print_warning "⚠️  mqtt_bridge.py no encontrado"
    print_warning "Copia el script mqtt_bridge.py antes de iniciar servicios"
fi

# 6. Preparar base de datos (si existe manage.py)
if [ -f "$PROJECT_DIR/backend/manage.py" ]; then
    print_status "Preparando base de datos..."
    sudo -u "$SERVICE_USER" bash << EOF
        cd "$PROJECT_DIR"
        source venv/bin/activate
        cd backend
        python manage.py collectstatic --noinput || true
        python manage.py migrate || true
EOF
fi

# 7. Configurar logrotate
print_status "Configurando rotación de logs..."
cat > /etc/logrotate.d/home-control << 'LOGROTATE'
/var/log/home_control/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    su pi pi
}
LOGROTATE

# 8. Mostrar estado
print_status "Verificando servicios instalados..."
systemctl list-unit-files | grep home-control

echo ""
echo "========================================="
echo "🎉 SERVICIOS INSTALADOS"
echo "========================================="
echo ""
echo "Servicios disponibles:"
echo "  • home-control-django.service"
echo "  • home-control-mqtt-bridge.service"
echo ""
echo "Para iniciar los servicios:"
echo "  sudo systemctl start home-control-django"
echo "  sudo systemctl start home-control-mqtt-bridge"
echo ""
echo "Para verificar estado:"
echo "  sudo systemctl status home-control-django"
echo "  sudo systemctl status home-control-mqtt-bridge"
echo ""
echo "Para ver logs:"
echo "  sudo journalctl -u home-control-django -f"
echo "  sudo journalctl -u home-control-mqtt-bridge -f"
echo "  tail -f /var/log/home_control/*.log"
echo ""
echo "Para parar servicios:"
echo "  sudo systemctl stop home-control-django"
echo "  sudo systemctl stop home-control-mqtt-bridge"
echo ""
echo "📁 Logs en: /var/log/home_control/"
echo "⚙️  Configuración en: $PROJECT_DIR/.env"
echo ""

# 9. Preguntar si iniciar servicios
read -p "¿Quieres iniciar los servicios ahora? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Iniciando servicios..."
    
    systemctl start home-control-django
    sleep 5
    systemctl start home-control-mqtt-bridge
    
    print_status "Verificando estado..."
    systemctl status home-control-django --no-pager -l
    systemctl status home-control-mqtt-bridge --no-pager -l
    
    echo ""
    echo "🌐 Dashboard disponible en: http://$(hostname -I | awk '{print $1}'):8000/"
else
    print_warning "Servicios instalados pero no iniciados"
    print_warning "Inicia manualmente cuando estés listo"
fi