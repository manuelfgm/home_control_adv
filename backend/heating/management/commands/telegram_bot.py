import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from heating.telegram_bot import TelegramHeatingBot


class Command(BaseCommand):
    help = 'Ejecuta el bot de Telegram para consultar y gestionar horarios de calefaccion.'

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        allowed_user_ids = settings.TELEGRAM_CHAT_ID_WHITELIST
        if not token:
            raise CommandError('Configura TELEGRAM_BOT_TOKEN en el archivo .env.')
        if not allowed_user_ids:
            raise CommandError('Configura TELEGRAM_CHAT_ID_WHITELIST con IDs autorizados.')

        bot = TelegramHeatingBot(token, allowed_user_ids)
        offset = None
        self.stdout.write(self.style.SUCCESS('Bot de horarios Telegram iniciado.'))

        try:
            while True:
                updates = bot.get_updates(offset)
                if updates is None:
                    time.sleep(5)
                    continue
                for update in updates:
                    offset = update['update_id'] + 1
                    try:
                        bot.handle_update(update)
                    except (KeyError, TypeError, ValueError):
                        self.stderr.write('Actualizacion de Telegram ignorada por formato invalido.')
        except KeyboardInterrupt:
            self.stdout.write('Bot de horarios Telegram detenido.')