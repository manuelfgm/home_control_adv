import logging
import re

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from actuators.models import ActuatorStatus
from .models import HeatingSchedule, HeatingSettings


logger = logging.getLogger(__name__)
SCHEDULE_CALLBACK = re.compile(r'^schedule:(select|set):(\d+)(?::([01]))?$')


class TelegramHeatingBot:
    def __init__(self, token, allowed_user_ids):
        self.token = token
        self.allowed_user_ids = {str(user_id) for user_id in allowed_user_ids}

    def _request(self, method, payload, timeout=(5, 35)):
        try:
            response = requests.post(
                f'https://api.telegram.org/bot{self.token}/{method}',
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            result = response.json()
            if result.get('ok') is True:
                return result
            logger.warning('Telegram rechazo la operacion %s.', method)
        except (requests.RequestException, ValueError):
            logger.warning('Fallo la operacion %s de Telegram.', method)
        return None

    def get_updates(self, offset):
        result = self._request(
            'getUpdates',
            {
                'offset': offset,
                'timeout': 25,
                'allowed_updates': ['message', 'callback_query'],
            },
        )
        return result.get('result', []) if result else None

    def handle_update(self, update):
        message = update.get('message')
        if message:
            self._handle_message(message)
            return

        callback = update.get('callback_query')
        if callback:
            self._handle_callback(callback)

    def _is_authorized_private_chat(self, user, chat):
        return (
            user is not None
            and chat is not None
            and str(user.get('id')) in self.allowed_user_ids
            and chat.get('type') == 'private'
            and str(chat.get('id')) == str(user.get('id'))
        )

    def _handle_message(self, message):
        user = message.get('from')
        chat = message.get('chat')
        if not self._is_authorized_private_chat(user, chat):
            return

        text = message.get('text', '').strip()
        command = text.split(maxsplit=1)[0].split('@', 1)[0].lower() if text else ''
        if command in ('/start', '/programas'):
            self._send_program_list(chat['id'])
        elif command == '/ayuda':
            self._send_message(
                chat['id'],
                'Usa /programas para consultar y activar o desactivar horarios.',
            )

    def _handle_callback(self, callback):
        message = callback.get('message') or {}
        user = callback.get('from')
        chat = message.get('chat')
        if not self._is_authorized_private_chat(user, chat):
            self._answer_callback(callback['id'], 'Usuario no autorizado.', show_alert=True)
            return

        data = callback.get('data', '')
        if data == 'schedule:list':
            self._edit_program_list(message)
            self._answer_callback(callback['id'])
            return

        match = SCHEDULE_CALLBACK.fullmatch(data)
        if not match:
            self._answer_callback(callback['id'], 'Accion no valida.', show_alert=True)
            return

        action, schedule_id, desired_state = match.groups()
        try:
            if action == 'select':
                schedule = HeatingSchedule.objects.get(pk=schedule_id)
                answer = None
            else:
                schedule, changed, error = self._set_schedule_state(
                    schedule_id,
                    desired_state == '1',
                )
                answer = (
                    error[:197] + '...'
                    if error and len(error) > 200
                    else error or (
                        'Horario actualizado.' if changed
                        else 'El horario ya tenia ese estado.'
                    )
                )
        except HeatingSchedule.DoesNotExist:
            self._answer_callback(callback['id'], 'Ese horario ya no existe.', show_alert=True)
            self._edit_program_list(message)
            return

        self._edit_schedule_detail(message, schedule)
        self._answer_callback(callback['id'], answer or '')

    @staticmethod
    def _set_schedule_state(schedule_id, is_active):
        try:
            with transaction.atomic():
                schedule = HeatingSchedule.objects.select_for_update().get(pk=schedule_id)
                if schedule.is_active == is_active:
                    return schedule, False, None
                schedule.is_active = is_active
                schedule.save(update_fields=['is_active', 'updated_at'])
                return schedule, True, None
        except HeatingSchedule.DoesNotExist:
            raise
        except ValidationError as error:
            return HeatingSchedule.objects.get(pk=schedule_id), False, str(error)

    def _program_list(self):
        schedules = HeatingSchedule.objects.order_by('-is_active', 'start_time', 'pk')
        rows = []
        for schedule in schedules:
            status = 'ACTIVADO' if schedule.is_active else 'DESACTIVADO'
            rows.append([{
                'text': f'{"🟢" if schedule.is_active else "⚪"} {schedule.name} · {status}',
                'callback_data': f'schedule:select:{schedule.pk}',
            }])
        return rows

    def _send_program_list(self, chat_id):
        rows = self._program_list()
        text = 'Programas de calefaccion:\nSelecciona un horario.'
        if not rows:
            text = 'No hay programas de calefaccion dados de alta.'
        self._send_message(chat_id, text, {'inline_keyboard': rows} if rows else None)

    def _edit_program_list(self, message):
        rows = self._program_list()
        text = 'Programas de calefaccion:\nSelecciona un horario.'
        if not rows:
            text = 'No hay programas de calefaccion dados de alta.'
        self._edit_message(
            message,
            text,
            {'inline_keyboard': rows} if rows else {'inline_keyboard': []},
        )

    def _edit_schedule_detail(self, message, schedule):
        status = 'ACTIVADO' if schedule.is_active else 'DESACTIVADO'
        current_schedule = 'Si' if schedule.is_active_now() else 'No'
        settings = HeatingSettings.get_current_settings()
        system_status = 'activado' if settings and settings.is_active else 'desactivado'
        actuator = ActuatorStatus.objects.filter(actuator_id='boiler').order_by(
            '-created_at', '-pk'
        ).first()
        if actuator:
            boiler_status = 'encendida' if actuator.is_heating else 'apagada'
            reported_at = timezone.localtime(actuator.created_at).strftime('%d/%m %H:%M')
            boiler_line = f'Caldera (ultimo reporte): {boiler_status} · {reported_at}'
        else:
            boiler_line = 'Caldera: sin estado recibido'

        text = (
            f'{schedule.name}\n'
            f'Estado del programa: {status}\n'
            f'En su franja ahora: {current_schedule}\n'
            f'Horario: {schedule.start_time:%H:%M}-{schedule.end_time:%H:%M} '
            f'({schedule.get_weekdays_display()})\n'
            f'Temperatura objetivo: {schedule.target_temperature:g} °C\n'
            f'Sistema de calefaccion: {system_status}\n'
            f'{boiler_line}\n\n'
            'Activar un programa lo habilita para su horario; no fuerza el encendido inmediato.'
        )
        action_text = 'Desactivar programa' if schedule.is_active else 'Activar programa'
        desired_state = 0 if schedule.is_active else 1
        keyboard = {
            'inline_keyboard': [
                [{
                    'text': action_text,
                    'callback_data': f'schedule:set:{schedule.pk}:{desired_state}',
                }],
                [{'text': 'Volver a programas', 'callback_data': 'schedule:list'}],
            ]
        }
        self._edit_message(message, text, keyboard)

    def _send_message(self, chat_id, text, reply_markup=None):
        payload = {'chat_id': chat_id, 'text': text}
        if reply_markup is not None:
            payload['reply_markup'] = reply_markup
        self._request('sendMessage', payload, timeout=(3, 5))

    def _edit_message(self, message, text, reply_markup):
        self._request(
            'editMessageText',
            {
                'chat_id': message['chat']['id'],
                'message_id': message['message_id'],
                'text': text,
                'reply_markup': reply_markup,
            },
            timeout=(3, 5),
        )

    def _answer_callback(self, callback_id, text=None, show_alert=False):
        payload = {'callback_query_id': callback_id}
        if text:
            payload['text'] = text
        if show_alert:
            payload['show_alert'] = True
        self._request('answerCallbackQuery', payload, timeout=(3, 5))