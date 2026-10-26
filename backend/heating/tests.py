from unittest.mock import patch

from django.test import TestCase, override_settings

from actuators.models import ActuatorStatus
from .models import HeatingSchedule
from .telegram_bot import TelegramHeatingBot


@override_settings(TELEGRAM_CHAT_ID_WHITELIST=['12345'])
class TelegramHeatingBotTests(TestCase):
	def setUp(self):
		self.bot = TelegramHeatingBot('test-token', ['12345'])
		self.chat = {'id': 12345, 'type': 'private'}
		self.message = {'chat': self.chat, 'message_id': 87}
		self.schedule = HeatingSchedule.objects.create(
			name='Mañanas',
			weekdays='0,1,2,3,4',
			start_time='07:00',
			end_time='09:00',
			target_temperature=20,
			is_active=False,
		)

	def update(self, text='/programas', user_id=12345, chat=None):
		self.bot.handle_update({
			'message': {
				'from': {'id': user_id},
				'chat': chat or self.chat,
				'text': text,
			}
		})

	def callback(self, data, user_id=12345):
		self.bot.handle_update({
			'callback_query': {
				'id': 'callback-1',
				'from': {'id': user_id},
				'message': self.message,
				'data': data,
			}
		})

	@patch('heating.telegram_bot.requests.post')
	def test_programs_command_lists_database_schedules_and_states(self, post):
		post.return_value.json.return_value = {'ok': True}
		self.schedule.is_active = True
		self.schedule.save()

		self.update('/programas@calefaccion_bot')

		payload = post.call_args.kwargs['json']
		self.assertEqual(payload['text'], 'Programas de calefaccion:\nSelecciona un horario.')
		self.assertEqual(payload['reply_markup']['inline_keyboard'][0][0]['text'], '🟢 Mañanas · ACTIVADO')

	@patch('heating.telegram_bot.requests.post')
	def test_programs_command_ignores_unlisted_user(self, post):
		self.update(user_id=999)
		post.assert_not_called()

	@patch('heating.telegram_bot.requests.post')
	def test_programs_command_only_works_in_private_chat(self, post):
		self.update(chat={'id': -100, 'type': 'group'})
		post.assert_not_called()

	@patch('heating.telegram_bot.requests.post')
	def test_status_command_returns_sensor_and_active_program(self, post):
		post.return_value.json.return_value = {'ok': True}
		reading = type('Reading', (), {'temperature': 19.5, 'humidity': 48.2})()
		active_schedule = type(
			'Schedule',
			(),
			{'name': 'Mañanas', 'target_temperature': 20.0},
		)()
		with (
			patch('heating.telegram_bot.SensorReading.objects.filter') as readings,
			patch(
				'heating.telegram_bot.HeatingSchedule.get_current_active_schedule',
				return_value=active_schedule,
			),
		):
			readings.return_value.order_by.return_value.first.return_value = reading
			self.update('/estado')

		self.assertEqual(
			post.call_args.kwargs['json']['text'],
			'Estado de calefaccion:\n'
			'Temperatura: 19.5 °C\n'
			'Humedad: 48.2 %\n'
			'Temperatura objetivo: 20 °C\n'
			'Programa activo: Mañanas',
		)

	@patch('heating.telegram_bot.requests.post')
	def test_status_command_without_reading_reports_default_target(self, post):
		post.return_value.json.return_value = {'ok': True}
		with (
			patch('heating.telegram_bot.SensorReading.objects.filter') as readings,
			patch(
				'heating.telegram_bot.HeatingSchedule.get_current_active_schedule',
				return_value=None,
			),
			patch(
				'heating.telegram_bot.HeatingSchedule.get_current_target_temperature',
				return_value=16.0,
			),
		):
			readings.return_value.order_by.return_value.first.return_value = None
			self.update('/estado')

		self.assertEqual(
			post.call_args.kwargs['json']['text'],
			'Estado de calefaccion:\n'
			'Temperatura: Sin datos\n'
			'Humedad: Sin datos\n'
			'Temperatura objetivo: 16 °C\n'
			'Programa activo: Ninguno (temperatura por defecto)',
		)

	@patch('heating.telegram_bot.requests.post')
	def test_select_schedule_shows_current_status_and_activate_button(self, post):
		post.return_value.json.return_value = {'ok': True}

		self.callback(f'schedule:select:{self.schedule.pk}')

		edit_payload = post.call_args_list[0].kwargs['json']
		self.assertIn('Estado del programa: DESACTIVADO', edit_payload['text'])
		self.assertEqual(
			edit_payload['reply_markup']['inline_keyboard'][0][0],
			{
				'text': 'Activar programa',
				'callback_data': f'schedule:set:{self.schedule.pk}:1',
			},
		)

	@patch('heating.telegram_bot.requests.post')
	def test_activate_callback_enables_schedule(self, post):
		post.return_value.json.return_value = {'ok': True}

		self.callback(f'schedule:set:{self.schedule.pk}:1')

		self.schedule.refresh_from_db()
		self.assertTrue(self.schedule.is_active)

	@patch('heating.telegram_bot.requests.post')
	def test_deactivate_callback_disables_schedule(self, post):
		post.return_value.json.return_value = {'ok': True}
		self.schedule.is_active = True
		self.schedule.save()

		self.callback(f'schedule:set:{self.schedule.pk}:0')

		self.schedule.refresh_from_db()
		self.assertFalse(self.schedule.is_active)

	@patch('heating.telegram_bot.requests.post')
	def test_replayed_activate_callback_does_not_toggle_schedule_off(self, post):
		post.return_value.json.return_value = {'ok': True}
		self.callback(f'schedule:set:{self.schedule.pk}:1')
		self.callback(f'schedule:set:{self.schedule.pk}:1')

		self.schedule.refresh_from_db()
		self.assertTrue(self.schedule.is_active)

	@patch('heating.telegram_bot.requests.post')
	def test_activate_overlapping_schedule_keeps_it_disabled(self, post):
		post.return_value.json.return_value = {'ok': True}
		self.schedule.is_active = True
		self.schedule.save()
		conflict = HeatingSchedule.objects.create(
			name='Mañanas ampliado',
			weekdays='0,1,2,3,4',
			start_time='08:00',
			end_time='10:00',
			target_temperature=21,
			is_active=False,
		)

		self.callback(f'schedule:set:{conflict.pk}:1')

		conflict.refresh_from_db()
		self.assertFalse(conflict.is_active)
		answer_payload = post.call_args_list[-1].kwargs['json']
		self.assertIn('se solapa', answer_payload['text'])

	@patch('heating.telegram_bot.requests.post')
	def test_schedule_detail_shows_last_reported_boiler_state(self, post):
		post.return_value.json.return_value = {'ok': True}
		ActuatorStatus.objects.create(actuator_id='boiler', is_heating=True)

		self.callback(f'schedule:select:{self.schedule.pk}')

		self.assertIn('Caldera (ultimo reporte): encendida', post.call_args_list[0].kwargs['json']['text'])

	@patch('heating.telegram_bot.requests.post')
	def test_callback_from_unlisted_user_does_not_change_schedule(self, post):
		post.return_value.json.return_value = {'ok': True}
		self.callback(f'schedule:set:{self.schedule.pk}:1', user_id=999)

		self.schedule.refresh_from_db()
		self.assertFalse(self.schedule.is_active)
		self.assertEqual(post.call_args.kwargs['json']['show_alert'], True)
