from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "ForgeLink Core"

    def ready(self):
        # Registers the JWTAuthentication scheme with drf-spectacular so
        # the generated OpenAPI doc documents the Bearer flow instead of
        # leaving every endpoint unauthenticated.
        from apps.core import schema  # noqa: F401
