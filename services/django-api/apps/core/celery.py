"""Celery configuration for ForgeLink."""
import os

from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')

app = Celery('forgelink')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Define task queues
app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'telemetry': {
        'exchange': 'telemetry',
        'routing_key': 'telemetry',
    },
    'alerts': {
        'exchange': 'alerts',
        'routing_key': 'alerts',
    },
    'ai': {
        'exchange': 'ai',
        'routing_key': 'ai',
    },
}

# Route tasks to appropriate queues
app.conf.task_routes = {
    'apps.telemetry.tasks.*': {'queue': 'telemetry'},
    'apps.alerts.tasks.*': {'queue': 'alerts'},
    'apps.ai.tasks.*': {'queue': 'ai'},
}


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f'Request: {self.request!r}')
