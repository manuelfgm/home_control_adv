#!/bin/bash
# Script de inicio para Home Control Backend
# /home/manu/code/home_control_adv/start_backend.sh

set -e

# Variables de configuración
PROJECT_DIR="/home/manu/code/home_control_adv"
VENV_DIR="$PROJECT_DIR/.venv"
DJANGO_DIR="$PROJECT_DIR/backend"
USER="manu"

# Activar entorno virtual
source "$VENV_DIR/bin/activate"

# Cambiar al directorio del proyecto Django
cd "$DJANGO_DIR"

# Aplicar migraciones si es necesario
echo "🔄 Aplicando migraciones..."
python manage.py migrate --noinput

# Recolectar archivos estáticos en producción (opcional para API)
echo "📂 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear || echo "⚠️ Collectstatic falló, continuando..."

# Verificar configuración
echo "🔍 Verificando configuración..."
python manage.py check

echo "🚀 Iniciando Gunicorn..."

# Función para limpiar procesos al salir
cleanup() {
    echo "🛑 Deteniendo servicios..."
    if [ ! -z "$GUNICORN_PID" ]; then
        kill $GUNICORN_PID 2>/dev/null
    fi
    if [ ! -z "$MQTT_PID" ]; then
        kill $MQTT_PID 2>/dev/null
    fi
    exit 0
}

# Capturar señales para limpieza
trap cleanup SIGTERM SIGINT

# Iniciar Gunicorn en background
gunicorn \
    --config "$PROJECT_DIR/gunicorn.conf.py" \
    --chdir "$DJANGO_DIR" \
    home_control.wsgi:application &
GUNICORN_PID=$!

echo "✅ Gunicorn iniciado (PID: $GUNICORN_PID)"

# Esperar 10 segundos para que Django esté completamente listo
echo "⏳ Esperando 10 segundos para que Django esté listo..."
sleep 10

# Verificar que Gunicorn sigue funcionando
if ! kill -0 $GUNICORN_PID 2>/dev/null; then
    echo "❌ Error: Gunicorn falló al iniciar"
    exit 1
fi

echo "🌐 Iniciando MQTT Bridge..."

# Iniciar MQTT Bridge
cd "$PROJECT_DIR"
python mqtt_bridge.py &
MQTT_PID=$!

echo "✅ MQTT Bridge iniciado (PID: $MQTT_PID)"

# Verificar que ambos procesos están funcionando
if ! kill -0 $GUNICORN_PID 2>/dev/null; then
    echo "❌ Error: Gunicorn no está funcionando"
    cleanup
    exit 1
fi

if ! kill -0 $MQTT_PID 2>/dev/null; then
    echo "❌ Error: MQTT Bridge no está funcionando"
    cleanup
    exit 1
fi

echo "🎉 Todos los servicios iniciados correctamente:"
echo "   - Django Backend (Gunicorn): PID $GUNICORN_PID"
echo "   - MQTT Bridge: PID $MQTT_PID"
echo "   - Presiona Ctrl+C para detener todos los servicios"

# Mantener el script ejecutándose y monitorear los procesos
while true; do
    # Verificar que Gunicorn sigue funcionando
    if ! kill -0 $GUNICORN_PID 2>/dev/null; then
        echo "❌ Gunicorn se detuvo inesperadamente"
        cleanup
        exit 1
    fi
    
    # Verificar que MQTT Bridge sigue funcionando
    if ! kill -0 $MQTT_PID 2>/dev/null; then
        echo "❌ MQTT Bridge se detuvo inesperadamente"
        cleanup
        exit 1
    fi
    
    sleep 5
done