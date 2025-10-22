#!/bin/bash

# Script para configurar cronjobs usando scripts independientes (sin Django)

PROJECT_DIR="/home/manu/personalcode/home_control_adv"
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

echo "🕒 Configurando cronjobs INDEPENDIENTES para Control de Calefacción..."

# Verificar que existen los archivos necesarios
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Error: No se encuentra Python en $PYTHON_PATH"
    echo "   Asegúrate de que el entorno virtual esté configurado"
    exit 1
fi

if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "❌ Error: No se encuentra directorio de scripts en $SCRIPTS_DIR"
    exit 1
fi

# Verificar scripts
REQUIRED_SCRIPTS=("mqtt_client.py" "heating_evaluator.py" "cleanup.py" "sensor_check.py")
for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ ! -f "$SCRIPTS_DIR/$script" ]; then
        echo "❌ Error: No se encuentra script $script"
        exit 1
    fi
done

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
echo "# === Sistema de Control de Calefacción (Scripts Independientes) ===" >> "$TEMP_CRON"
echo "# Generado automáticamente - No editar manualmente" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 1. Evaluar horarios de calefacción cada minuto
echo "# Evalúa horarios de calefacción cada minuto (independiente)" >> "$TEMP_CRON"
echo "* * * * * cd $SCRIPTS_DIR && $PYTHON_PATH heating_evaluator.py >> $LOGS_DIR/heating_standalone.log 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 2. Limpiar datos antiguos diariamente a las 2:00 AM
echo "# Limpia datos antiguos diariamente a las 2:00 AM (independiente)" >> "$TEMP_CRON"
echo "0 2 * * * cd $SCRIPTS_DIR && $PYTHON_PATH cleanup.py --vacuum >> $LOGS_DIR/cleanup_standalone.log 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 3. Verificar estado de sensores cada 5 minutos
echo "# Verifica estado de sensores cada 5 minutos (independiente)" >> "$TEMP_CRON"
echo "*/5 * * * * cd $SCRIPTS_DIR && $PYTHON_PATH sensor_check.py >> $LOGS_DIR/sensor_check_standalone.log 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 4. Mantener cliente MQTT corriendo (cada 2 minutos)
echo "# Mantiene cliente MQTT corriendo (independiente)" >> "$TEMP_CRON"
echo "*/2 * * * * pgrep -f 'mqtt_client.py' > /dev/null || (cd $SCRIPTS_DIR && nohup $PYTHON_PATH mqtt_client.py >> $LOGS_DIR/mqtt_standalone.log 2>&1 &)" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 5. Limpieza semanal más agresiva de logs de calefacción
echo "# Limpia logs de calefacción antiguos semanalmente" >> "$TEMP_CRON"
echo "0 3 * * 0 cd $SCRIPTS_DIR && $PYTHON_PATH cleanup.py --log-days=30 --vacuum >> $LOGS_DIR/cleanup_weekly.log 2>&1" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# 6. Rotación de logs del sistema
echo "# Rotación de logs los domingos a las 4:00 AM" >> "$TEMP_CRON"
echo "0 4 * * 0 cd $LOGS_DIR && for log in *.log; do [ -f \"\$log\" ] && [ \$(stat -c%s \"\$log\") -gt 1048576 ] && mv \"\$log\" \"\$log.old\" && touch \"\$log\"; done" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

echo "📁 Contenido del crontab que se instalará:"
echo "----------------------------------------"
cat "$TEMP_CRON"
echo "----------------------------------------"
echo ""

# Preguntar confirmación
read -p "¿Deseas instalar estos cronjobs INDEPENDIENTES? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Instalar el nuevo crontab
    crontab "$TEMP_CRON"
    
    if [ $? -eq 0 ]; then
        echo "✅ Cronjobs independientes instalados correctamente!"
        echo ""
        echo "📋 Cronjobs activos:"
        crontab -l | grep -A 20 "Control de Calefacción"
        echo ""
        echo "📁 Los logs se guardarán en: $LOGS_DIR"
        echo ""
        echo "🔧 Scripts independientes configurados:"
        echo "  🔥 Evaluador de calefacción: $SCRIPTS_DIR/heating_evaluator.py"
        echo "  📡 Cliente MQTT:             $SCRIPTS_DIR/mqtt_client.py"
        echo "  🧹 Limpiador de datos:       $SCRIPTS_DIR/cleanup.py"
        echo "  🔍 Verificador de sensores:  $SCRIPTS_DIR/sensor_check.py"
        echo ""
        echo "📊 Comandos de monitoreo:"
        echo "  Ver logs calefacción:        tail -f $LOGS_DIR/heating_standalone.log"
        echo "  Ver logs MQTT:              tail -f $LOGS_DIR/mqtt_standalone.log"
        echo "  Ver logs limpieza:          tail -f $LOGS_DIR/cleanup_standalone.log"
        echo "  Ver logs sensores:          tail -f $LOGS_DIR/sensor_check_standalone.log"
        echo "  Todos los logs:             tail -f $LOGS_DIR/*_standalone.log"
        echo ""
        echo "🧪 Probar scripts manualmente:"
        echo "  Evaluar calefacción:        cd $SCRIPTS_DIR && $PYTHON_PATH heating_evaluator.py --verbose"
        echo "  Verificar sensores:         cd $SCRIPTS_DIR && $PYTHON_PATH sensor_check.py --verbose --summary"
        echo "  Limpiar datos (dry-run):    cd $SCRIPTS_DIR && $PYTHON_PATH cleanup.py --dry-run --verbose"
        echo "  Cliente MQTT:               cd $SCRIPTS_DIR && $PYTHON_PATH mqtt_client.py"
        echo ""
        echo "🚀 Para iniciar manualmente el cliente MQTT:"
        echo "  cd $SCRIPTS_DIR && nohup $PYTHON_PATH mqtt_client.py > $LOGS_DIR/mqtt_manual.log 2>&1 &"
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
echo "🎉 Ventajas de los scripts independientes:"
echo "   ✅ No dependen de Django (más rápidos y ligeros)"
echo "   ✅ Acceso directo a la base de datos SQLite"
echo "   ✅ Logs separados para cada función"
echo "   ✅ Fáciles de debuggear y probar individualmente"
echo "   ✅ Menor consumo de memoria y CPU"
echo "   ✅ Pueden funcionar aunque Django esté apagado"
echo ""
echo "ℹ️  Nota: Los cronjobs comenzarán a ejecutarse automáticamente."
echo "   El cliente MQTT se iniciará en los próximos 2 minutos."
echo "   Django puede funcionar independientemente en el puerto 8000."