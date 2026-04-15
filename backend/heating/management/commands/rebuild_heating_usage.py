import datetime
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from actuators.models import ActuatorStatus
from heating.models import HeatingDailyUsage, HeatingMonthlyUsage


def _accumulate_period(daily_totals, monthly_totals, start_utc, end_utc):
    """
    Acumula un período de calefacción activa en los diccionarios en memoria,
    distribuyendo el tiempo entre los días/meses afectados si cruza la medianoche.
    No hace ninguna query a la DB.
    """
    if end_utc <= start_utc:
        return

    start_local = timezone.localtime(start_utc)
    end_local = timezone.localtime(end_utc)

    current = start_local
    while current.date() <= end_local.date():
        if current.date() == end_local.date():
            period_end = end_local
        else:
            next_midnight = datetime.datetime.combine(
                current.date() + datetime.timedelta(days=1),
                datetime.time.min,
            )
            period_end = timezone.localtime(timezone.make_aware(next_midnight))

        hours = (period_end - current).total_seconds() / 3600.0
        if hours > 0:
            day = current.date()
            daily_totals[day] += hours
            monthly_totals[(day.year, day.month)] += hours

        current = period_end


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

        total = ActuatorStatus.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No hay registros de ActuatorStatus.'))
            return

        self.stdout.write(f'Cargando {total} registros de ActuatorStatus en memoria...')
        statuses = list(
            ActuatorStatus.objects
            .order_by('created_at')
            .values('created_at', 'is_heating')
        )

        # Acumular todo en memoria — sin queries a la DB en este bucle
        self.stdout.write('Calculando períodos de calefacción...')
        daily_totals = defaultdict(float)    # {date: horas}
        monthly_totals = defaultdict(float)  # {(año, mes): horas}

        for i in range(1, len(statuses)):
            prev = statuses[i - 1]
            curr = statuses[i]
            if prev['is_heating']:
                _accumulate_period(daily_totals, monthly_totals,
                                   prev['created_at'], curr['created_at'])

        self.stdout.write(
            f'Cálculo completado: {len(daily_totals)} días, '
            f'{len(monthly_totals)} meses con calefacción activa.'
        )

        # Una sola transacción con dos bulk_create — mínimo impacto en la DB
        self.stdout.write('Guardando en la base de datos...')
        with transaction.atomic():
            HeatingDailyUsage.objects.all().delete()
            HeatingMonthlyUsage.objects.all().delete()

            HeatingDailyUsage.objects.bulk_create([
                HeatingDailyUsage(date=day, total_hours=round(hours, 4))
                for day, hours in sorted(daily_totals.items())
            ])

            HeatingMonthlyUsage.objects.bulk_create([
                HeatingMonthlyUsage(year=yr, month=mo, total_hours=round(hours, 4))
                for (yr, mo), hours in sorted(monthly_totals.items())
            ])

        self.stdout.write(
            self.style.SUCCESS(
                f'Listo. {HeatingDailyUsage.objects.count()} registros diarios y '
                f'{HeatingMonthlyUsage.objects.count()} registros mensuales creados.'
            )
        )
