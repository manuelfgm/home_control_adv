#!/usr/bin/env python3
"""
Script de limpieza de datos independiente.
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
LOG_FILE = PROJECT_ROOT / "logs" / "cleanup_standalone.log"

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

class DataCleaner:
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
    
    def cleanup_sensor_readings(self, days_to_keep=365, dry_run=False):
        """Limpia lecturas de sensores antiguas"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()
            
            cursor = self.db_connection.cursor()
            
            # Contar registros a eliminar
            cursor.execute("""
                SELECT COUNT(*) as count FROM sensors_sensorreading 
                WHERE timestamp < ?
            """, (cutoff_str,))
            
            count = cursor.fetchone()['count']
            
            if count == 0:
                logger.info(f"No hay registros anteriores a {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} para eliminar")
                return 0
            
            if dry_run:
                logger.info(f"DRY-RUN: Se eliminarían {count} registros anteriores a {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Mostrar estadísticas por sensor
                cursor.execute("""
                    SELECT sensor_id, sensor_type, COUNT(*) as count 
                    FROM sensors_sensorreading 
                    WHERE timestamp < ?
                    GROUP BY sensor_id, sensor_type
                """, (cutoff_str,))
                
                stats = cursor.fetchall()
                logger.info("Desglose por sensor:")
                for stat in stats:
                    logger.info(f"  {stat['sensor_id']} ({stat['sensor_type']}): {stat['count']} registros")
                
                return count
            else:
                logger.info(f"Eliminando {count} registros antiguos...")
                
                cursor.execute("""
                    DELETE FROM sensors_sensorreading 
                    WHERE timestamp < ?
                """, (cutoff_str,))
                
                deleted_count = cursor.rowcount
                self.db_connection.commit()
                
                logger.info(f"✅ Eliminados {deleted_count} registros correctamente")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error durante la limpieza: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            raise
    
    def cleanup_heating_logs(self, days_to_keep=90, dry_run=False):
        """Limpia logs de calefacción antiguos"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()
            
            cursor = self.db_connection.cursor()
            
            # Contar registros a eliminar
            cursor.execute("""
                SELECT COUNT(*) as count FROM heating_heatinglog 
                WHERE timestamp < ?
            """, (cutoff_str,))
            
            count = cursor.fetchone()['count']
            
            if count == 0:
                logger.info(f"No hay logs de calefacción anteriores a {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} para eliminar")
                return 0
            
            if dry_run:
                logger.info(f"DRY-RUN: Se eliminarían {count} logs de calefacción anteriores a {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
                return count
            else:
                logger.info(f"Eliminando {count} logs de calefacción antiguos...")
                
                cursor.execute("""
                    DELETE FROM heating_heatinglog 
                    WHERE timestamp < ?
                """, (cutoff_str,))
                
                deleted_count = cursor.rowcount
                self.db_connection.commit()
                
                logger.info(f"✅ Eliminados {deleted_count} logs de calefacción correctamente")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error durante la limpieza de logs: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            raise
    
    def get_database_stats(self):
        """Obtiene estadísticas de la base de datos"""
        try:
            cursor = self.db_connection.cursor()
            
            # Estadísticas de lecturas de sensores
            cursor.execute("SELECT COUNT(*) as count FROM sensors_sensorreading")
            total_readings = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT timestamp FROM sensors_sensorreading 
                ORDER BY timestamp ASC LIMIT 1
            """)
            oldest_reading = cursor.fetchone()
            
            cursor.execute("""
                SELECT timestamp FROM sensors_sensorreading 
                ORDER BY timestamp DESC LIMIT 1
            """)
            newest_reading = cursor.fetchone()
            
            # Estadísticas de logs de calefacción
            cursor.execute("SELECT COUNT(*) as count FROM heating_heatinglog")
            total_logs = cursor.fetchone()['count']
            
            stats = {
                'total_readings': total_readings,
                'total_logs': total_logs,
                'oldest_reading': oldest_reading['timestamp'] if oldest_reading else None,
                'newest_reading': newest_reading['timestamp'] if newest_reading else None,
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def vacuum_database(self):
        """Optimiza la base de datos después de la limpieza"""
        try:
            logger.info("Optimizando base de datos...")
            self.db_connection.execute("VACUUM")
            logger.info("✅ Base de datos optimizada")
        except Exception as e:
            logger.error(f"Error optimizando base de datos: {e}")
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        if self.db_connection:
            self.db_connection.close()

def parse_arguments():
    """Parsea argumentos de línea de comandos"""
    args = {
        'days': 365,
        'log_days': 90,
        'dry_run': False,
        'verbose': False,
        'vacuum': False
    }
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--days' and i + 1 < len(sys.argv):
            args['days'] = int(sys.argv[i + 1])
            i += 1
        elif arg == '--log-days' and i + 1 < len(sys.argv):
            args['log_days'] = int(sys.argv[i + 1])
            i += 1
        elif arg == '--dry-run':
            args['dry_run'] = True
        elif arg == '--verbose':
            args['verbose'] = True
        elif arg == '--vacuum':
            args['vacuum'] = True
        elif arg == '--help':
            print("""
Uso: python cleanup.py [opciones]

Opciones:
  --days DIAS           Días de datos de sensores a conservar (por defecto: 365)
  --log-days DIAS       Días de logs de calefacción a conservar (por defecto: 90)
  --dry-run             Muestra qué se eliminaría sin eliminar realmente
  --verbose             Muestra información detallada
  --vacuum              Optimiza la base de datos después de la limpieza
  --help                Muestra esta ayuda
            """)
            sys.exit(0)
        i += 1
    
    return args

def main():
    """Función principal"""
    args = parse_arguments()
    
    if args['verbose']:
        print(f"🧹 Iniciando limpieza de datos...")
        print(f"   Conservar datos de sensores: {args['days']} días")
        print(f"   Conservar logs de calefacción: {args['log_days']} días")
        print(f"   Modo dry-run: {'Sí' if args['dry_run'] else 'No'}")
    
    # Verificar base de datos
    if not DB_FILE.exists():
        logger.error(f"Base de datos no encontrada: {DB_FILE}")
        sys.exit(1)
    
    # Ejecutar limpieza
    cleaner = DataCleaner()
    try:
        cleaner.connect_db()
        
        # Estadísticas iniciales
        if args['verbose']:
            initial_stats = cleaner.get_database_stats()
            print(f"\n📊 Estadísticas iniciales:")
            print(f"   Total lecturas de sensores: {initial_stats.get('total_readings', 0)}")
            print(f"   Total logs de calefacción: {initial_stats.get('total_logs', 0)}")
            if initial_stats.get('oldest_reading'):
                print(f"   Registro más antiguo: {initial_stats['oldest_reading']}")
            if initial_stats.get('newest_reading'):
                print(f"   Registro más reciente: {initial_stats['newest_reading']}")
        
        # Limpiar datos de sensores
        deleted_readings = cleaner.cleanup_sensor_readings(args['days'], args['dry_run'])
        
        # Limpiar logs de calefacción
        deleted_logs = cleaner.cleanup_heating_logs(args['log_days'], args['dry_run'])
        
        # Optimizar base de datos si se eliminó algo
        if not args['dry_run'] and (deleted_readings > 0 or deleted_logs > 0) and args['vacuum']:
            cleaner.vacuum_database()
        
        # Estadísticas finales
        if args['verbose'] and not args['dry_run']:
            final_stats = cleaner.get_database_stats()
            print(f"\n📊 Estadísticas finales:")
            print(f"   Total lecturas de sensores: {final_stats.get('total_readings', 0)}")
            print(f"   Total logs de calefacción: {final_stats.get('total_logs', 0)}")
            
            # Calcular espacio aproximado ahorrado
            total_deleted = deleted_readings + deleted_logs
            if total_deleted > 0:
                saved_bytes = total_deleted * 100  # Estimación: ~100 bytes por registro
                if saved_bytes > 1024 * 1024:
                    saved_mb = saved_bytes / (1024 * 1024)
                    print(f"   Espacio aproximado liberado: {saved_mb:.2f} MB")
                elif saved_bytes > 1024:
                    saved_kb = saved_bytes / 1024
                    print(f"   Espacio aproximado liberado: {saved_kb:.2f} KB")
                else:
                    print(f"   Espacio aproximado liberado: {saved_bytes} bytes")
        
        if args['verbose']:
            print("✅ Limpieza completada")
        
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        sys.exit(1)
    finally:
        cleaner.close()

if __name__ == "__main__":
    main()