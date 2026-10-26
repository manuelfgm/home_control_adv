import logging

import requests
from django.conf import settings

from heating.status import build_heating_status_message


logger = logging.getLogger(__name__)


def notify_heating_change(actuator_status):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_ids = settings.TELEGRAM_CHAT_ID_WHITELIST
    if not token or not chat_ids:
        return

    message = build_heating_status_message(actuator_status)
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