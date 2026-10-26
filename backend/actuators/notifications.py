import logging

import requests
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


def notify_heating_change(actuator_status):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_ids = settings.TELEGRAM_CHAT_ID_WHITELIST
    if not token or not chat_ids:
        return

    state = 'encendida' if actuator_status.is_heating else 'apagada'
    received_at = timezone.localtime(actuator_status.created_at)
    message = (
        f'Calefaccion {state}\n'
        f'Actuador: {actuator_status.actuator_id}\n'
    )
    if actuator_status.temperature is not None:
        # El actuador no mide: devuelve la temperatura que recibio en el comando.
        message += f'Temperatura recibida: {actuator_status.temperature:g} °C\n'
    message += f'Fecha: {received_at:%d/%m/%Y %H:%M:%S %Z}'
    for chat_id in dict.fromkeys(chat_ids):
        try:
            response = requests.post(
                f'https://api.telegram.org/bot{token}/sendMessage',
                json={'chat_id': chat_id, 'text': message},
                timeout=(3, 5),
            )
            response.raise_for_status()
            if response.json().get('ok') is not True:
                logger.warning('Telegram rechazo el aviso de calefaccion.')
        except (requests.RequestException, ValueError):
            logger.warning('No se pudo enviar el aviso de calefaccion a Telegram.')