from django.apps import AppConfig


class HeatingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'heating'

    def ready(self):
        import heating.signals  # noqa: F401  — registra los signal handlers
