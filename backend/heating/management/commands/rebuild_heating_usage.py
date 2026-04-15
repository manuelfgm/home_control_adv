from django.core.management.base import BaseCommand
from django.db import transaction

from actuators.models import ActuatorStatus
from heating.models import HeatingDailyUsage, HeatingMonthlyUsage, record_heating_period


class Command(BaseCommand):
    help = (
        'Reconstruye HeatingDailyUsage y HeatingMonthlyUsage a partir del '
        'historial completo de ActuatorStatus. Borra los datos existentes antes '
        'de recalcular.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            dest='no_input',
            help='No pide confirmación antes de borrar los datos existentes.',
        )

    def handle(self, *args, **options):
        if not options['no_input']:
            confirm = input(
                'Esto borrará todos los registros de HeatingDailyUsage y '
                'HeatingMonthlyUsage y los recalculará desde cero.\n'
                '¿Continuar? [s/N] '
            )
            if confirm.strip().lower() not in ('s', 'si', 'sí', 'y', 'yes'):
                self.stdout.write(self.style.WARNING('Operación cancelada.'))
                return

        self.stdout.write('Borrando datos de uso existentes...')
        HeatingDailyUsage.objects.all().delete()
        HeatingMonthlyUsage.objects.all().delete()

        total = ActuatorStatus.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No hay registros de ActuatorStatus.'))
            return

        self.stdout.write(f'Procesando {total} registros de ActuatorStatus...')

        # Cargar sólo los campos necesarios para ahorrar memoria
        statuses = list(
            ActuatorStatus.objects
            .order_by('created_at')
            .values('created_at', 'is_heating')
        )

        processed = 0
        with transaction.atomic():
            for i in range(1, len(statuses)):
                prev = statuses[i - 1]
                curr = statuses[i]
                if prev['is_heating']:
                    record_heating_period(prev['created_at'], curr['created_at'])
                processed += 1
                if processed % 1000 == 0:
                    self.stdout.write(f'  {processed}/{total - 1} pares procesados...')

        daily_count = HeatingDailyUsage.objects.count()
        monthly_count = HeatingMonthlyUsage.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Listo. {daily_count} registros diarios y '
                f'{monthly_count} registros mensuales creados.'
            )
        )
