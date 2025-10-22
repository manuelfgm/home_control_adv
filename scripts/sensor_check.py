#!/usr/bin/env python3
"""
Script de verificación de estado de sensores independiente.
No depende de Django, se conecta directamente a la base de datos.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Configurar paths
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / "backend" / ".env"
DB_FILE = PROJECT_ROOT / "backend" / "db.sqlite3"
LOG_FILE = PROJECT_ROOT / "logs" / "sensor_check_standalone.log"

# Crear directorio de logs si no existe
LOG_FILE.parent.mkdir(exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler() if '--verbose' in sys.argv else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv(ENV_FILE)

class SensorChecker:
    def __init__(self):
        self.db_connection = None
        
    def connect_db(self):
        """Conecta a la base de datos SQLite"""
        try:
            self.db_connection = sqlite3.connect(DB_FILE)
            self.db_connection.row_factory = sqlite3.Row
            logger.info("Conectado a la base de datos")
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            raise
    
    def check_sensor_status(self, offline_threshold_hours=1):
        """Verifica el estado de los sensores y marca como offline los que no han reportado"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=offline_threshold_hours)
            cutoff_str = cutoff_time.isoformat()
            
            cursor = self.db_connection.cursor()
            
            # Buscar sensores que no han reportado en el tiempo límite
            cursor.execute("""
                SELECT sensor_id, name, last_seen, is_active 
                FROM sensors_sensorstatus 
                WHERE last_seen < ? AND is_active = 1
            """, (cutoff_str,))
            
            offline_sensors = cursor.fetchall()
            
            if offline_sensors:
                logger.warning(f"Encontrados {len(offline_sensors)} sensores offline")
                
                # Marcar como inactivos
                offline_ids = [sensor['sensor_id'] for sensor in offline_sensors]
                placeholders = ','.join(['?'] * len(offline_ids))
                
                cursor.execute(f"""
                    UPDATE sensors_sensorstatus 
                    SET is_active = 0 
                    WHERE sensor_id IN ({placeholders})
                """, offline_ids)
                
                updated_count = cursor.rowcount
                self.db_connection.commit()
                
                logger.info(f"Marcados {updated_count} sensores como offline")
                
                # Detallar sensores offline
                for sensor in offline_sensors:
                    last_seen = datetime.fromisoformat(sensor['last_seen'])
                    hours_offline = (datetime.now() - last_seen).total_seconds() / 3600
                    logger.warning(f"Sensor offline: {sensor['name']} ({sensor['sensor_id']}) - Última actividad: hace {hours_offline:.1f} horas")
                
                return updated_count
            else:
                logger.info("Todos los sensores están online")
                return 0
                
        except Exception as e:
            logger.error(f"Error verificando estado de sensores: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            raise
    
    def reactivate_online_sensors(self):
        """Reactiva sensores que han vuelto a reportar"""
        try:
            # Buscar sensores inactivos que han reportado recientemente
            recent_time = datetime.now() - timedelta(minutes=10)
            recent_str = recent_time.isoformat()
            
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                SELECT DISTINCT s.sensor_id, s.name 
                FROM sensors_sensorstatus s
                INNER JOIN sensors_sensorreading r ON s.sensor_id = r.sensor_id
                WHERE s.is_active = 0 AND r.timestamp > ?
            """, (recent_str,))
            
            reactivated_sensors = cursor.fetchall()
            
            if reactivated_sensors:
                logger.info(f"Reactivando {len(reactivated_sensors)} sensores que han vuelto online")
                
                # Reactivar sensores
                sensor_ids = [sensor['sensor_id'] for sensor in reactivated_sensors]
                placeholders = ','.join(['?'] * len(sensor_ids))
                
                cursor.execute(f"""
                    UPDATE sensors_sensorstatus 
                    SET is_active = 1, last_seen = ? 
                    WHERE sensor_id IN ({placeholders})
                """, [datetime.now().isoformat()] + sensor_ids)
                
                updated_count = cursor.rowcount
                self.db_connection.commit()
                
                logger.info(f"Reactivados {updated_count} sensores")
                
                # Detallar sensores reactivados
                for sensor in reactivated_sensors:
                    logger.info(f"Sensor reactivado: {sensor['name']} ({sensor['sensor_id']})")
                
                return updated_count
            else:
                logger.info("No hay sensores para reactivar")
                return 0
                
        except Exception as e:
            logger.error(f"Error reactivando sensores: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            raise
    
    def get_sensor_summary(self):
        """Obtiene un resumen del estado de todos los sensores"""
        try:
            cursor = self.db_connection.cursor()
            
            # Contar sensores por estado
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive
                FROM sensors_sensorstatus
            """)
            
            counts = cursor.fetchone()
            
            # Obtener detalle de todos los sensores
            cursor.execute("""
                SELECT sensor_id, name, location, is_active, last_seen
                FROM sensors_sensorstatus
                ORDER BY is_active DESC, last_seen DESC
            """)
            
            sensors = cursor.fetchall()
            
            summary = {
                'total': counts['total'],
                'active': counts['active'],
                'inactive': counts['inactive'],
                'sensors': [dict(sensor) for sensor in sensors]
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen de sensores: {e}")
            return {}
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        if self.db_connection:
            self.db_connection.close()

def parse_arguments():
    """Parsea argumentos de línea de comandos"""
    args = {
        'threshold_hours': 1,
        'verbose': False,
        'summary': False
    }
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--threshold' and i + 1 < len(sys.argv):
            args['threshold_hours'] = float(sys.argv[i + 1])
            i += 1
        elif arg == '--verbose':
            args['verbose'] = True
        elif arg == '--summary':
            args['summary'] = True
        elif arg == '--help':
            print("""
Uso: python sensor_check.py [opciones]

Opciones:
  --threshold HORAS     Horas sin actividad para considerar sensor offline (por defecto: 1)
  --verbose             Muestra información detallada
  --summary             Muestra resumen de todos los sensores
  --help                Muestra esta ayuda
            """)
            sys.exit(0)
        i += 1
    
    return args

def main():
    """Función principal"""
    args = parse_arguments()
    
    if args['verbose']:
        print(f"🔍 Verificando estado de sensores...")
        print(f"   Umbral offline: {args['threshold_hours']} horas")
    
    # Verificar base de datos
    if not DB_FILE.exists():
        logger.error(f"Base de datos no encontrada: {DB_FILE}")
        sys.exit(1)
    
    # Verificar sensores
    checker = SensorChecker()
    try:
        checker.connect_db()
        
        # Reactivar sensores que han vuelto online
        reactivated = checker.reactivate_online_sensors()
        
        # Verificar sensores offline
        offline_count = checker.check_sensor_status(args['threshold_hours'])
        
        # Mostrar resumen si se solicita
        if args['summary'] or args['verbose']:
            summary = checker.get_sensor_summary()
            
            if args['verbose']:
                print(f"\n📊 Resumen de sensores:")
                print(f"   Total: {summary.get('total', 0)}")
                print(f"   Activos: {summary.get('active', 0)}")
                print(f"   Inactivos: {summary.get('inactive', 0)}")
                
                if summary.get('sensors'):
                    print(f"\n📋 Detalle de sensores:")
                    for sensor in summary['sensors']:
                        status = "🟢 Online" if sensor['is_active'] else "🔴 Offline"
                        last_seen = "Nunca" if not sensor['last_seen'] else sensor['last_seen']
                        print(f"   {sensor['name']} ({sensor['sensor_id']}) - {status} - Última actividad: {last_seen}")
        
        if reactivated > 0:
            logger.info(f"✅ {reactivated} sensores reactivados")
        
        if offline_count > 0:
            logger.warning(f"⚠️  {offline_count} sensores marcados como offline")
        else:
            logger.info("✅ Todos los sensores están funcionando correctamente")
        
        if args['verbose']:
            print("✅ Verificación completada")
        
    except Exception as e:
        logger.error(f"Error en verificación: {e}")
        sys.exit(1)
    finally:
        checker.close()

if __name__ == "__main__":
    main()