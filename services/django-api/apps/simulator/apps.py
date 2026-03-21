"""Simulator app configuration."""

from django.apps import AppConfig


class SimulatorConfig(AppConfig):
    """Configuration for the steel plant simulator app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.simulator"
    verbose_name = "Steel Plant Simulator"

    def ready(self):
        """Import signals when app is ready."""
        pass
