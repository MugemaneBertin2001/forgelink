"""Celery configuration for ForgeLink."""

import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.core.settings")

app = Celery("forgelink")

# Load config from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Define task queues
app.conf.task_queues = {
    "default": {
        "exchange": "default",
        "routing_key": "default",
    },
    "telemetry": {
        "exchange": "telemetry",
        "routing_key": "telemetry",
    },
    "alerts": {
        "exchange": "alerts",
        "routing_key": "alerts",
    },
    "ai": {
        "exchange": "ai",
        "routing_key": "ai",
    },
    "simulation": {
        "exchange": "simulation",
        "routing_key": "simulation",
    },
}

# Route tasks to appropriate queues
app.conf.task_routes = {
    "apps.telemetry.tasks.*": {"queue": "telemetry"},
    "apps.alerts.tasks.*": {"queue": "alerts"},
    "apps.ai.tasks.*": {"queue": "ai"},
    "apps.simulator.tasks.*": {"queue": "simulation"},
}

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Telemetry aggregation tasks
    "aggregate-telemetry-1m": {
        "task": "apps.telemetry.tasks.aggregate_telemetry_1m",
        "schedule": crontab(minute="*"),  # Every minute
        "options": {"queue": "telemetry"},
    },
    "aggregate-telemetry-1h": {
        "task": "apps.telemetry.tasks.aggregate_telemetry_1h",
        "schedule": crontab(minute=5),  # 5 minutes past every hour
        "options": {"queue": "telemetry"},
    },
    "aggregate-telemetry-1d": {
        "task": "apps.telemetry.tasks.aggregate_telemetry_1d",
        "schedule": crontab(hour=0, minute=15),  # 00:15 UTC daily
        "options": {"queue": "telemetry"},
    },
    # Data quality monitoring
    "check-data-quality": {
        "task": "apps.telemetry.tasks.check_data_quality",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
        "options": {"queue": "telemetry"},
    },
    # Anomaly detection
    "detect-anomalies-melt-shop": {
        "task": "apps.telemetry.tasks.detect_anomalies_batch",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
        "args": ("melt-shop",),
        "options": {"queue": "telemetry"},
    },
    "detect-anomalies-continuous-casting": {
        "task": "apps.telemetry.tasks.detect_anomalies_batch",
        "schedule": crontab(minute="*/15"),
        "args": ("continuous-casting",),
        "options": {"queue": "telemetry"},
    },
    "detect-anomalies-rolling-mill": {
        "task": "apps.telemetry.tasks.detect_anomalies_batch",
        "schedule": crontab(minute="*/15"),
        "args": ("rolling-mill",),
        "options": {"queue": "telemetry"},
    },
    "detect-anomalies-finishing": {
        "task": "apps.telemetry.tasks.detect_anomalies_batch",
        "schedule": crontab(minute="*/15"),
        "args": ("finishing",),
        "options": {"queue": "telemetry"},
    },
    # Data retention cleanup
    "cleanup-old-telemetry": {
        "task": "apps.telemetry.tasks.cleanup_old_telemetry",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC daily
        "options": {"queue": "telemetry"},
    },
    # Area summaries for dashboards
    "compute-area-summary-melt-shop": {
        "task": "apps.telemetry.tasks.compute_area_summary",
        "schedule": crontab(minute="*/2"),  # Every 2 minutes
        "args": ("melt-shop",),
        "options": {"queue": "telemetry"},
    },
    "compute-area-summary-continuous-casting": {
        "task": "apps.telemetry.tasks.compute_area_summary",
        "schedule": crontab(minute="*/2"),
        "args": ("continuous-casting",),
        "options": {"queue": "telemetry"},
    },
    "compute-area-summary-rolling-mill": {
        "task": "apps.telemetry.tasks.compute_area_summary",
        "schedule": crontab(minute="*/2"),
        "args": ("rolling-mill",),
        "options": {"queue": "telemetry"},
    },
    "compute-area-summary-finishing": {
        "task": "apps.telemetry.tasks.compute_area_summary",
        "schedule": crontab(minute="*/2"),
        "args": ("finishing",),
        "options": {"queue": "telemetry"},
    },
}


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f"Request: {self.request!r}")
