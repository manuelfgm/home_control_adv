from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from sensors.models import SensorReading
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Limpia datos de sensores antiguos para mantener la base de datos eficiente'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Número de días de datos a conservar (por defecto: 365)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se eliminaría sin eliminar realmente'
        )
    
    def handle(self, *args, **options):
        days_to_keep = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Contar registros a eliminar
        old_readings = SensorReading.objects.filter(timestamp__lt=cutoff_date)
        count = old_readings.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'No hay registros anteriores a {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")} para eliminar'
                )
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY-RUN: Se eliminarían {count} registros anteriores a {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}'
                )
            )
            
            # Mostrar estadísticas por sensor
            from django.db.models import Count
            stats = old_readings.values('sensor_id', 'sensor_type').annotate(count=Count('id'))
            
            self.stdout.write('\nDesglose por sensor:')
            for stat in stats:
                self.stdout.write(f"  {stat['sensor_id']} ({stat['sensor_type']}): {stat['count']} registros")
        else:
            self.stdout.write(f'Eliminando {count} registros antiguos...')
            
            try:
                deleted_count, deleted_details = old_readings.delete()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Eliminados {deleted_count} registros correctamente'
                    )
                )
                
                # Log para seguimiento
                logger.info(f'Cleanup completado: {deleted_count} registros eliminados')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error durante la limpieza: {e}')
                )
                logger.error(f'Error en cleanup: {e}')
        
        # Mostrar estadísticas actuales
        total_readings = SensorReading.objects.count()
        oldest_reading = SensorReading.objects.order_by('timestamp').first()
        newest_reading = SensorReading.objects.order_by('-timestamp').first()
        
        self.stdout.write('\n📊 Estadísticas actuales:')
        self.stdout.write(f'  Total de registros: {total_readings}')
        
        if oldest_reading:
            self.stdout.write(f'  Registro más antiguo: {oldest_reading.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
        if newest_reading:
            self.stdout.write(f'  Registro más reciente: {newest_reading.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Calcular espacio aproximado ahorrado
        if not dry_run and count > 0:
            # Estimación: ~100 bytes por registro
            saved_bytes = count * 100
            if saved_bytes > 1024 * 1024:
                saved_mb = saved_bytes / (1024 * 1024)
                self.stdout.write(f'  Espacio aproximado liberado: {saved_mb:.2f} MB')
            elif saved_bytes > 1024:
                saved_kb = saved_bytes / 1024
                self.stdout.write(f'  Espacio aproximado liberado: {saved_kb:.2f} KB')
            else:
                self.stdout.write(f'  Espacio aproximado liberado: {saved_bytes} bytes')