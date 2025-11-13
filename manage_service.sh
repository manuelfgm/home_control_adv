#!/bin/bash
# Script de gestión del servicio Home Control Backend
# /home/manu/personalcode/home_control_adv/manage_service.sh

SERVICE_NAME="home-control-backend"
SERVICE_FILE="/home/manu/personalcode/home_control_adv/${SERVICE_NAME}.service"
SYSTEM_SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

case "$1" in
    install)
        echo "🔧 Instalando servicio systemd..."
        
        # Copiar archivo de servicio
        sudo cp "$SERVICE_FILE" "$SYSTEM_SERVICE_PATH"
        
        # Recargar systemd
        sudo systemctl daemon-reload
        
        # Habilitar servicio para inicio automático
        sudo systemctl enable "$SERVICE_NAME"
        
        echo "✅ Servicio instalado y habilitado para inicio automático"
        echo "📋 Comandos útiles:"
        echo "   sudo systemctl start $SERVICE_NAME     # Iniciar"
        echo "   sudo systemctl stop $SERVICE_NAME      # Detener"
        echo "   sudo systemctl restart $SERVICE_NAME   # Reiniciar"
        echo "   sudo systemctl status $SERVICE_NAME    # Ver estado"
        echo "   journalctl -u $SERVICE_NAME -f         # Ver logs en tiempo real"
        ;;
        
    start)
        echo "🚀 Iniciando servicio..."
        sudo systemctl start "$SERVICE_NAME"
        sudo systemctl status "$SERVICE_NAME" --no-pager
        ;;
        
    stop)
        echo "🛑 Deteniendo servicio..."
        sudo systemctl stop "$SERVICE_NAME"
        ;;
        
    restart)
        echo "🔄 Reiniciando servicio..."
        sudo systemctl restart "$SERVICE_NAME"
        sudo systemctl status "$SERVICE_NAME" --no-pager
        ;;
        
    status)
        sudo systemctl status "$SERVICE_NAME" --no-pager
        ;;
        
    logs)
        echo "📋 Logs del servicio (Ctrl+C para salir):"
        journalctl -u "$SERVICE_NAME" -f
        ;;
        
    logs-tail)
        echo "📋 Últimos logs del servicio:"
        journalctl -u "$SERVICE_NAME" --no-pager -n 50
        ;;
        
    uninstall)
        echo "🗑️ Desinstalando servicio..."
        sudo systemctl stop "$SERVICE_NAME" || true
        sudo systemctl disable "$SERVICE_NAME" || true
        sudo rm -f "$SYSTEM_SERVICE_PATH"
        sudo systemctl daemon-reload
        echo "✅ Servicio desinstalado"
        ;;
        
    test)
        echo "🧪 Probando configuración..."
        /home/manu/personalcode/home_control_adv/start_backend.sh --check-only || true
        ;;
        
    *)
        echo "🏠 Home Control Backend - Gestión de Servicio"
        echo ""
        echo "Uso: $0 {install|start|stop|restart|status|logs|logs-tail|uninstall|test}"
        echo ""
        echo "Comandos:"
        echo "  install    - Instalar servicio systemd"
        echo "  start      - Iniciar servicio"
        echo "  stop       - Detener servicio"
        echo "  restart    - Reiniciar servicio"
        echo "  status     - Ver estado del servicio"
        echo "  logs       - Ver logs en tiempo real"
        echo "  logs-tail  - Ver últimos logs"
        echo "  uninstall  - Desinstalar servicio"
        echo "  test       - Probar configuración"
        echo ""
        echo "Ejemplo:"
        echo "  $0 install    # Instalar por primera vez"
        echo "  $0 start      # Iniciar el servicio"
        echo "  $0 logs       # Ver logs en tiempo real"
        exit 1
        ;;
esac