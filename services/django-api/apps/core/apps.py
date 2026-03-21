from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "ForgeLink Core"

    def ready(self):
        # Import signals if needed
        pass
