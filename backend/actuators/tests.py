from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from .models import ActuatorStatus
from .notifications import notify_heating_change
from .views import ActuatorStatusViewSet


class HeatingChangeTests(TestCase):
	def setUp(self):
		self.factory = APIRequestFactory()
		self.view = ActuatorStatusViewSet.as_view({'post': 'create'})

	def send_status(self, is_heating, actuator_id='boiler'):
		request = self.factory.post(
			'/actuators/api/status/',
			{'actuator_id': actuator_id, 'is_heating': is_heating},
			format='json',
		)
		with self.captureOnCommitCallbacks(execute=True):
			return self.view(request)

	@patch('actuators.views.notify_heating_change')
	def test_create_first_status_does_not_notify(self, notify):
		for state in (False, True):
			with self.subTest(state=state):
				self.send_status(state, actuator_id=f'boiler-{state}')
		notify.assert_not_called()

	@patch('actuators.views.notify_heating_change')
	def test_create_repeated_status_does_not_notify(self, notify):
		for state in (False, True):
			with self.subTest(state=state):
				actuator_id = f'boiler-{state}'
				ActuatorStatus.objects.create(actuator_id=actuator_id, is_heating=state)
				self.send_status(state, actuator_id=actuator_id)
		notify.assert_not_called()

	@patch('actuators.views.notify_heating_change')
	def test_create_changed_status_notifies_once(self, notify):
		for state in (False, True):
			with self.subTest(state=state):
				notify.reset_mock()
				ActuatorStatus.objects.all().delete()
				ActuatorStatus.objects.create(actuator_id='boiler', is_heating=not state)
				self.send_status(state)
				notify.assert_called_once_with(ActuatorStatus.objects.first())

	@patch('actuators.views.notify_heating_change')
	def test_create_other_actuator_does_not_notify(self, notify):
		ActuatorStatus.objects.create(actuator_id='other', is_heating=True)
		self.send_status(False)
		notify.assert_not_called()

	@patch('actuators.views.notify_heating_change')
	def test_create_changed_status_waits_for_commit(self, notify):
		ActuatorStatus.objects.create(actuator_id='boiler', is_heating=False)
		request = self.factory.post(
			'/', {'actuator_id': 'boiler', 'is_heating': True}, format='json'
		)
		self.view(request)
		notify.assert_not_called()

	@patch('actuators.views.notify_heating_change')
	def test_create_invalid_status_does_not_notify(self, notify):
		request = self.factory.post('/', {'is_heating': 'invalid'}, format='json')
		response = self.view(request)
		self.assertEqual((response.status_code, notify.call_count), (400, 0))

	@override_settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_CHAT_ID_WHITELIST=['123'])
	@patch('actuators.notifications.requests.post', side_effect=requests.Timeout)
	def test_create_telegram_failure_still_saves_status(self, post):
		ActuatorStatus.objects.create(actuator_id='boiler', is_heating=False)
		with self.assertLogs('actuators.notifications', level='WARNING'):
			response = self.send_status(True)
		self.assertEqual(
			(response.status_code, ActuatorStatus.objects.first().is_heating),
			(201, True),
		)


@override_settings(
	TELEGRAM_BOT_TOKEN='test-token',
	TELEGRAM_CHAT_ID_WHITELIST=['123', '-456', '123'],
)
class TelegramNotificationTests(TestCase):
	def setUp(self):
		self.status = ActuatorStatus(actuator_id='boiler', is_heating=True)

	@patch('actuators.notifications.requests.post')
	def test_notify_whitelist_sends_only_to_unique_chats(self, post):
		post.return_value.json.return_value = {'ok': True}
		notify_heating_change(self.status)
		self.assertEqual(
			[call.kwargs['json']['chat_id'] for call in post.call_args_list],
			['123', '-456'],
		)

	@override_settings(TELEGRAM_CHAT_ID_WHITELIST=['123'])
	@patch('actuators.notifications.requests.post')
	def test_notify_change_uses_official_api_and_state(self, post):
		post.return_value.json.return_value = {'ok': True}
		received_at = timezone.localtime(self.status.created_at)
		for state, text in ((True, 'encendida'), (False, 'apagada')):
			with self.subTest(state=state):
				self.status.is_heating = state
				notify_heating_change(self.status)
				self.assertEqual(
					(post.call_args.args, post.call_args.kwargs),
					(('https://api.telegram.org/bottest-token/sendMessage',), {
						'json': {
							'chat_id': '123',
							'text': (
								f'Estado de calefaccion:\n'
								f'Caldera: {"Encendida" if state else "Apagada"}\n'
								f'Temperatura: Sin datos\n'
								f'Humedad: Sin datos\n'
								f'Temperatura objetivo: 16 °C\n'
								f'Programa activo: Ninguno (temperatura por defecto)\n'
								f'Ultimo reporte: '
								f'{received_at:%d/%m/%Y %H:%M:%S %Z}'
							),
						},
						'timeout': (3, 5),
					}),
				)

	@override_settings(TELEGRAM_CHAT_ID_WHITELIST=['123'])
	@patch('actuators.notifications.requests.post')
	def test_notify_includes_temperature_received_by_actuator(self, post):
		post.return_value.json.return_value = {'ok': True}
		self.status.temperature = 21.5
		notify_heating_change(self.status)
		self.assertIn(
			'Temperatura devuelta por actuador (comando): 21.5 °C\n',
			post.call_args.kwargs['json']['text'],
		)

	@override_settings(TELEGRAM_CHAT_ID_WHITELIST=['123'])
	@patch('actuators.notifications.requests.post')
	def test_notify_without_temperature_omits_line(self, post):
		post.return_value.json.return_value = {'ok': True}
		self.status.temperature = None
		notify_heating_change(self.status)
		self.assertNotIn(
			'Temperatura devuelta por actuador',
			post.call_args.kwargs['json']['text'],
		)

	@override_settings(TELEGRAM_BOT_TOKEN='')
	@patch('actuators.notifications.requests.post')
	def test_notify_missing_token_does_not_send(self, post):
		notify_heating_change(self.status)
		post.assert_not_called()

	@override_settings(TELEGRAM_CHAT_ID_WHITELIST=[])
	@patch('actuators.notifications.requests.post')
	def test_notify_empty_whitelist_does_not_send(self, post):
		notify_heating_change(self.status)
		post.assert_not_called()

	@patch('actuators.notifications.requests.post')
	def test_notify_failed_recipient_continues_without_leaking_token(self, post):
		for failure in (
			requests.Timeout('test-token'),
			requests.HTTPError('test-token'),
			ValueError('test-token'),
		):
			with self.subTest(failure=type(failure).__name__):
				post.reset_mock()
				post.side_effect = [failure, Mock(json=Mock(return_value={'ok': True}))]
				with self.assertLogs('actuators.notifications', level='WARNING') as logs:
					notify_heating_change(self.status)
				self.assertEqual((post.call_count, 'test-token' in str(logs.output)), (2, False))

	@patch('actuators.notifications.requests.post')
	def test_notify_api_rejection_logs_warning(self, post):
		post.return_value.json.return_value = {'ok': False}
		with self.assertLogs('actuators.notifications', level='WARNING') as logs:
			notify_heating_change(self.status)
		self.assertEqual(len(logs.output), 2)
