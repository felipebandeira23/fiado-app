from django.apps import AppConfig


class FaturasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.faturas'
    verbose_name = 'Faturas'

    def ready(self):
        import apps.faturas.signals  # noqa: F401
