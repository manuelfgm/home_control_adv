#!/bin/bash

# Script para configurar cronjobs para el sistema de control de calefacción

PROJECT_DIR="/home/manu/personalcode/home_control_adv"
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
MANAGE_PY="$PROJECT_DIR/backend/manage.py"

echo "🕒 Configurando cronjobs para Control de Calefacción..."

# Verificar que existen los archivos necesarios
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Error: No se encuentra Python en $PYTHON_PATH"
    echo "   Asegúrate de que el entorno virtual esté configurado"
    exit 1
fi

if [ ! -f "$MANAGE_PY" ]; then
    echo "❌ Error: No se encuentra manage.py en $MANAGE_PY"
    exit 1
fi

# Crear directorio de logs si no existe
LOGS_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOGS_DIR"

# Backup del crontab actual
echo "📋 Creando backup del crontab actual..."
crontab -l > "$PROJECT_DIR/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || echo "No hay crontab previo"

# Crear archivo temporal con los nuevos cronjobs
TEMP_CRON=$(mktemp)

# Mantener cronjobs existentes (que no sean del proyecto)
crontab -l 2>/dev/null | grep -v "home_control_adv" > "$TEMP_CRON"

# Agregar header
echo "" >> "$TEMP_CRON"
echo "# === Sistema de Control de Calefacción ===" >> "$TEMP_CRON"
echo "# Generado automáticamente - No editar manualmente" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 1. Evaluar horarios de calefacción cada minuto
echo "# Evalúa horarios de calefacción cada minuto" >> "$TEMP_CRON"
echo "* * * * * cd $PROJECT_DIR/backend && $PYTHON_PATH $MANAGE_PY evaluate_heating >> $LOGS_DIR/heating_cron.log 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 2. Limpiar datos antiguos diariamente a las 2:00 AM
echo "# Limpia datos antiguos diariamente a las 2:00 AM" >> "$TEMP_CRON"
echo "0 2 * * * cd $PROJECT_DIR/backend && $PYTHON_PATH $MANAGE_PY cleanup_old_data >> $LOGS_DIR/cleanup_cron.log 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 3. Verificar estado de sensores cada 5 minutos
echo "# Verifica estado de sensores cada 5 minutos" >> "$TEMP_CRON"
echo "*/5 * * * * cd $PROJECT_DIR/backend && $PYTHON_PATH $MANAGE_PY shell -c \"from sensors.models import SensorStatus; from django.utils import timezone; SensorStatus.objects.filter(last_seen__lt=timezone.now() - timezone.timedelta(hours=1)).update(is_active=False)\" >> $LOGS_DIR/sensors_check_cron.log 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 4. Reiniciar cliente MQTT si se cae (cada 2 minutos)
echo "# Mantiene cliente MQTT corriendo" >> "$TEMP_CRON"
echo "*/2 * * * * pgrep -f 'start_mqtt' > /dev/null || (cd $PROJECT_DIR/backend && nohup $PYTHON_PATH $MANAGE_PY start_mqtt >> $LOGS_DIR/mqtt_cron.log 2>&1 &)" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 5. Rotación de logs semanalmente
echo "# Rotación de logs los domingos a las 3:00 AM" >> "$TEMP_CRON"
echo "0 3 * * 0 cd $LOGS_DIR && for log in *.log; do [ -f \"\$log\" ] && mv \"\$log\" \"\$log.old\" && touch \"\$log\"; done" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

echo "📁 Contenido del crontab que se instalará:"
echo "----------------------------------------"
cat "$TEMP_CRON"
echo "----------------------------------------"
echo ""

# Preguntar confirmación
read -p "¿Deseas instalar estos cronjobs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Instalar el nuevo crontab
    crontab "$TEMP_CRON"
    
    if [ $? -eq 0 ]; then
        echo "✅ Cronjobs instalados correctamente!"
        echo ""
        echo "📋 Cronjobs activos:"
        crontab -l | grep -A 20 "Control de Calefacción"
        echo ""
        echo "📁 Los logs se guardarán en: $LOGS_DIR"
        echo ""
        echo "🔧 Comandos útiles:"
        echo "  Ver cronjobs:           crontab -l"
        echo "  Editar cronjobs:        crontab -e"
        echo "  Ver logs heating:       tail -f $LOGS_DIR/heating_cron.log"
        echo "  Ver logs MQTT:          tail -f $LOGS_DIR/mqtt_cron.log"
        echo "  Ver logs cleanup:       tail -f $LOGS_DIR/cleanup_cron.log"
        echo ""
        echo "🚀 Para iniciar el cliente MQTT manualmente:"
        echo "  cd $PROJECT_DIR/backend && $PYTHON_PATH $MANAGE_PY start_mqtt"
    else
        echo "❌ Error instalando cronjobs"
        exit 1
    fi
else
    echo "❌ Instalación cancelada"
fi

# Limpiar archivo temporal
rm "$TEMP_CRON"

echo ""
echo "ℹ️  Nota: Los cronjobs comenzarán a ejecutarse automáticamente."
echo "   El cliente MQTT se iniciará en los próximos 2 minutos."
echo "   Puedes iniciarlo manualmente si no quieres esperar."