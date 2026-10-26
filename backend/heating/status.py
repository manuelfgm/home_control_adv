from django.utils import timezone

from actuators.models import ActuatorStatus
from sensors.models import SensorReading

from .models import HeatingSchedule


def build_heating_status_message(actuator_status: ActuatorStatus | None = None) -> str:
    if actuator_status is None:
        actuator_status = ActuatorStatus.objects.order_by('-created_at', '-pk').first()

    reading = SensorReading.objects.filter(
        temperature__isnull=False,
        sensor_error=False,
    ).order_by('-created_at').first()
    active_schedule = HeatingSchedule.get_current_active_schedule()
    target_temperature = (
        active_schedule.target_temperature
        if active_schedule
        else HeatingSchedule.get_current_target_temperature()
    )

    boiler_state = (
        'Sin reporte'
        if actuator_status is None
        else 'Encendida' if actuator_status.is_heating else 'Apagada'
    )
    current_temperature = f'{reading.temperature:g} °C' if reading else 'Sin datos'
    humidity = (
        f'{reading.humidity:g} %'
        if reading and reading.humidity is not None
        else 'Sin datos'
    )
    program = active_schedule.name if active_schedule else 'Ninguno (temperatura por defecto)'

    lines = [
        'Estado de calefaccion:',
        f'Caldera: {boiler_state}',
        f'Temperatura: {current_temperature}',
        f'Humedad: {humidity}',
        f'Temperatura objetivo: {target_temperature:g} °C',
        f'Programa activo: {program}',
    ]
    if actuator_status:
        if actuator_status.temperature is not None:
            lines.append(
                f'Temperatura devuelta por actuador (comando): '
                f'{actuator_status.temperature:g} °C'
            )
        reported_at = timezone.localtime(actuator_status.created_at).strftime(
            '%d/%m/%Y %H:%M:%S %Z'
        )
        lines.append(f'Ultimo reporte: {reported_at}')
    else:
        lines.append('Ultimo reporte: Sin datos')

    return '\n'.join(lines)