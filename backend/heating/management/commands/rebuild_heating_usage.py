import datetime
import time
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from actuators.models import ActuatorStatus
from heating.models import HeatingDailyUsage, HeatingMonthlyUsage

REPORT_EVERY = 10_000  # Mostrar progreso cada N pares


def _accumulate_period(daily_totals, monthly_totals, start_local, end_local):
    """
    Acumula un período de calefacción en los diccionarios en memoria.
    Recibe datetimes YA convertidos a hora local — no hace ninguna query ni
    conversión de timezone.
    """
    if end_local <= start_local:
        return

    current = start_local
    while current.date() <= end_local.date():
        if current.date() == end_local.date():
            period_end = end_local
        else:
            period_end = current.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + datetime.timedelta(days=1)

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

        # --- Carga con conversión de timezone de una sola vez ---
        self.stdout.write(f'Cargando {total:,} registros y convirtiendo a hora local...')
        local_tz = timezone.get_current_timezone()
        t0_load = time.time()

        statuses = [
            (s['created_at'].astimezone(local_tz), s['is_heating'])
            for s in ActuatorStatus.objects
            .order_by('created_at')
            .values('created_at', 'is_heating')
            .iterator(chunk_size=5_000)
        ]

        load_secs = time.time() - t0_load
        self.stdout.write(f'  Cargados en {load_secs:.1f}s')

        # --- Bucle de cálculo con progreso ---
        self.stdout.write(f'Calculando períodos ({total - 1:,} pares)...')
        daily_totals = defaultdict(float)
        monthly_totals = defaultdict(float)

        t0_calc = time.time()
        pairs_total = len(statuses) - 1

        for i in range(1, len(statuses)):
            prev_local, prev_heating = statuses[i - 1]
            curr_local, _           = statuses[i]

            if prev_heating:
                _accumulate_period(daily_totals, monthly_totals, prev_local, curr_local)

            if i % REPORT_EVERY == 0:
                elapsed = time.time() - t0_calc
                rate = i / elapsed if elapsed > 0 else 0
                eta = (pairs_total - i) / rate if rate > 0 else 0
                pct = i / pairs_total * 100
                self.stdout.write(
                    f'  {i:>{len(str(pairs_total))}}/{pairs_total:,}  '
                    f'({pct:.1f}%)  '
                    f'{elapsed:.0f}s transcurridos  '
                    f'ETA: {eta:.0f}s'
                )

        calc_secs = time.time() - t0_calc
        self.stdout.write(
            f'Cálculo completado en {calc_secs:.1f}s: '
            f'{len(daily_totals)} días, {len(monthly_totals)} meses con calefacción activa.'
        )

        # --- Escritura en DB: borrar + bulk_create en una transacción ---
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
