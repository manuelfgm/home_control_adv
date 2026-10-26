#!/bin/bash
# Script de inicio para Home Control Backend
# /home/manu/code/home_control_adv/start_backend.sh

set -e

# Procesar argumentos de línea de comandos
FORCE_RESTART=false
SKIP_GUNICORN=false
MQTT_ONLY=false
START_TELEGRAM=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE_RESTART=true
            shift
            ;;
        --mqtt-only|-m)
            MQTT_ONLY=true
            SKIP_GUNICORN=true
            START_TELEGRAM=false
            shift
            ;;
        --help|-h)
            echo "🏠 Home Control Backend - Script de Inicio"
            echo ""
            echo "Uso: $0 [opciones]"
            echo ""
            echo "Opciones:"
            echo "  -f, --force     Forzar reinicio (matar procesos existentes)"
            echo "  -m, --mqtt-only Solo iniciar MQTT Bridge"
            echo "  -h, --help      Mostrar esta ayuda"
            echo ""
            echo "Ejemplos:"
            echo "  $0              # Inicio normal (interactivo si hay conflictos)"
            echo "  $0 --force      # Reinicio forzado"
            echo "  $0 --mqtt-only  # Solo MQTT Bridge"
            exit 0
            ;;
        *)
            echo "❌ Opción desconocida: $1"
            echo "Usa --help para ver las opciones disponibles"
            exit 1
            ;;
    esac
done

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

echo "� Verificando servicios existentes..."

# Verificar si ya hay servicios funcionando
EXISTING_GUNICORN=$(pgrep -f "gunicorn.*home_control" | head -1)
EXISTING_MQTT=$(pgrep -f "mqtt_bridge.py" | head -1)
EXISTING_TELEGRAM=$(pgrep -f '[m]anage.py telegram_bot' | head -1)
PORT_8000_USED=$(netstat -tln 2>/dev/null | grep ":8000 " | wc -l)

# Manejar servicios existentes
if [ ! -z "$EXISTING_GUNICORN" ] || [ "$PORT_8000_USED" -gt 0 ] || [ ! -z "$EXISTING_MQTT" ] || [ ! -z "$EXISTING_TELEGRAM" ]; then
    echo "⚠️  Detectados servicios ya funcionando:"
    if [ ! -z "$EXISTING_GUNICORN" ]; then
        echo "   - Gunicorn ya está ejecutándose (PID: $EXISTING_GUNICORN)"
    fi
    if [ "$PORT_8000_USED" -gt 0 ]; then
        echo "   - Puerto 8000 ya está en uso"
    fi
    if [ ! -z "$EXISTING_MQTT" ]; then
        echo "   - MQTT Bridge ya está ejecutándose (PID: $EXISTING_MQTT)"
    fi
    if [ ! -z "$EXISTING_TELEGRAM" ]; then
        echo "   - Bot Telegram ya está ejecutándose (PID: $EXISTING_TELEGRAM)"
    fi
    
    if [ "$FORCE_RESTART" = "true" ]; then
        echo "🛑 Forzando reinicio (--force)..."
        if [ ! -z "$EXISTING_GUNICORN" ]; then
            kill $EXISTING_GUNICORN 2>/dev/null
            echo "   ✅ Gunicorn detenido"
        fi
        if [ ! -z "$EXISTING_MQTT" ]; then
            kill $EXISTING_MQTT 2>/dev/null
            echo "   ✅ MQTT Bridge detenido"
        fi
        if [ ! -z "$EXISTING_TELEGRAM" ]; then
            kill $EXISTING_TELEGRAM 2>/dev/null
            echo "   ✅ Bot Telegram detenido"
        fi
        echo "⏳ Esperando que se liberen los puertos..."
        sleep 3
    elif [ "$MQTT_ONLY" = "true" ]; then
        echo "⏭️ Solo MQTT Bridge (--mqtt-only)..."
        if [ ! -z "$EXISTING_MQTT" ]; then
            kill $EXISTING_MQTT 2>/dev/null
            echo "   ✅ MQTT Bridge anterior detenido"
            sleep 2
        fi
        if [ ! -z "$EXISTING_TELEGRAM" ]; then
            kill $EXISTING_TELEGRAM 2>/dev/null
            echo "   ✅ Bot Telegram anterior detenido"
            sleep 2
        fi
        SKIP_GUNICORN=true
        START_TELEGRAM=false
    else
        echo ""
        echo "🤔 ¿Qué quieres hacer?"
        echo "1) Detener servicios existentes y reiniciar"
        echo "2) Salir (dejar servicios funcionando)" 
        echo "3) Continuar sin Gunicorn (solo MQTT)"
        echo ""
        read -p "Selecciona una opción (1-3): " CHOICE
        
        case $CHOICE in
            1)
                echo "🛑 Deteniendo servicios existentes..."
                if [ ! -z "$EXISTING_GUNICORN" ]; then
                    kill $EXISTING_GUNICORN 2>/dev/null
                    echo "   ✅ Gunicorn detenido"
                fi
                if [ ! -z "$EXISTING_MQTT" ]; then
                    kill $EXISTING_MQTT 2>/dev/null
                    echo "   ✅ MQTT Bridge detenido"
                fi
                if [ ! -z "$EXISTING_TELEGRAM" ]; then
                    kill $EXISTING_TELEGRAM 2>/dev/null
                    echo "   ✅ Bot Telegram detenido"
                fi
                echo "⏳ Esperando que se liberen los puertos..."
                sleep 3
                ;;
            2)
                echo "👋 Saliendo - servicios siguen funcionando"
                exit 0
                ;;
            3)
                echo "⏭️ Continuando solo con MQTT Bridge..."
                if [ ! -z "$EXISTING_MQTT" ]; then
                    kill $EXISTING_MQTT 2>/dev/null
                    echo "   ✅ MQTT Bridge anterior detenido"
                    sleep 2
                fi
                SKIP_GUNICORN=true
                START_TELEGRAM=false
                ;;
            *)
                echo "❌ Opción inválida, saliendo..."
                exit 1
                ;;
        esac
    fi
fi

echo "🚀 Iniciando servicios..."

# Función para limpiar procesos al salir
cleanup() {
    echo "🛑 Deteniendo servicios..."
    if [ ! -z "$GUNICORN_PID" ]; then
        kill "$GUNICORN_PID" 2>/dev/null || true
        wait "$GUNICORN_PID" 2>/dev/null || true
    fi
    if [ ! -z "$MQTT_PID" ]; then
        kill "$MQTT_PID" 2>/dev/null || true
        wait "$MQTT_PID" 2>/dev/null || true
    fi
    if [ ! -z "$TELEGRAM_PID" ]; then
        kill "$TELEGRAM_PID" 2>/dev/null || true
        wait "$TELEGRAM_PID" 2>/dev/null || true
    fi
}

# Capturar señales para limpieza
trap 'cleanup; exit 0' SIGTERM SIGINT

# Iniciar Gunicorn solo si no se debe omitir
if [ "$SKIP_GUNICORN" != "true" ]; then
    echo "🚀 Iniciando Gunicorn..."
    
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
else
    echo "⏭️ Saltando inicio de Gunicorn (ya está funcionando)"
    GUNICORN_PID=""
    sleep 2
fi

echo "🌐 Iniciando MQTT Bridge..."

# Iniciar MQTT Bridge
cd "$PROJECT_DIR"
python mqtt_bridge.py &
MQTT_PID=$!

echo "✅ MQTT Bridge iniciado (PID: $MQTT_PID)"

# Iniciar el bot interactivo si está configurado.
TELEGRAM_PID=""
if [ "$START_TELEGRAM" = "true" ]; then
    if python "$DJANGO_DIR/manage.py" shell -c "from django.conf import settings; import sys; sys.exit(0 if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID_WHITELIST else 1)" >/dev/null 2>&1; then
        echo "📨 Iniciando bot de Telegram..."
        python "$DJANGO_DIR/manage.py" telegram_bot &
        TELEGRAM_PID=$!
        echo "✅ Bot de Telegram iniciado (PID: $TELEGRAM_PID)"
    else
        echo "⚠️ Bot de Telegram omitido: configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID_WHITELIST"
    fi
fi

# Verificar que los procesos iniciados están funcionando
if [ "$SKIP_GUNICORN" != "true" ] && ! kill -0 "$GUNICORN_PID" 2>/dev/null; then
    echo "❌ Error: Gunicorn no está funcionando"
    cleanup
    exit 1
fi

if ! kill -0 "$MQTT_PID" 2>/dev/null; then
    echo "❌ Error: MQTT Bridge no está funcionando"
    cleanup
    exit 1
fi

if [ -n "$TELEGRAM_PID" ] && ! kill -0 "$TELEGRAM_PID" 2>/dev/null; then
    echo "❌ Error: El bot de Telegram no está funcionando"
    cleanup
    exit 1
fi

echo "🎉 Todos los servicios iniciados correctamente:"
if [ "$SKIP_GUNICORN" != "true" ]; then
    echo "   - Django Backend (Gunicorn): PID $GUNICORN_PID"
fi
echo "   - MQTT Bridge: PID $MQTT_PID"
if [ -n "$TELEGRAM_PID" ]; then
    echo "   - Telegram Bot: PID $TELEGRAM_PID"
fi
echo "   - Presiona Ctrl+C para detener todos los servicios"

# Mantener el script ejecutándose y monitorear los procesos
while true; do
    # Verificar que Gunicorn sigue funcionando
    if [ "$SKIP_GUNICORN" != "true" ] && ! kill -0 "$GUNICORN_PID" 2>/dev/null; then
        echo "❌ Gunicorn se detuvo inesperadamente"
        cleanup
        exit 1
    fi
    
    # Verificar que MQTT Bridge sigue funcionando
    if ! kill -0 "$MQTT_PID" 2>/dev/null; then
        echo "❌ MQTT Bridge se detuvo inesperadamente"
        cleanup
        exit 1
    fi

    if [ -n "$TELEGRAM_PID" ] && ! kill -0 "$TELEGRAM_PID" 2>/dev/null; then
        echo "❌ El bot de Telegram se detuvo inesperadamente"
        cleanup
        exit 1
    fi
    
    sleep 5
done