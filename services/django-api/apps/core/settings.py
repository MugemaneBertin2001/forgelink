"""
ForgeLink Django Settings

Steel Factory IoT Platform - Django Integration Hub
"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-based settings using Pydantic."""

    # Django
    secret_key: str = "django-insecure-change-me-in-production"
    debug: bool = True
    allowed_hosts: str = "localhost,127.0.0.1"
    csrf_trusted_origins: str = "http://localhost:8000"

    # PostgreSQL
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "forgelink"
    db_user: str = "forgelink"
    db_password: str = "forgelink_dev_password"

    # TDengine
    tdengine_host: str = "localhost"
    tdengine_port: int = 6041
    tdengine_user: str = "root"
    tdengine_password: str = "taosdata"
    tdengine_database: str = "forgelink_telemetry"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_django_db: int = 0
    redis_celery_db: int = 2

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group_id: str = "forgelink"

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "forgelink"
    rabbitmq_password: str = "forgelink_rabbitmq_dev"

    # IDP
    idp_jwks_url: str = "http://localhost:8080/auth/jwks"

    # Observability
    jaeger_endpoint: str = "http://localhost:14268/api/traces"

    # Factory
    factory_timezone: str = "Africa/Kigali"

    # Telemetry batching
    telemetry_batch_size: int = 500
    telemetry_batch_timeout_ms: int = 1000

    class Config:
        env_prefix = "DJANGO_"
        env_file = ".env"
        extra = "ignore"


# Load settings from environment
env = Settings()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = env.secret_key
DEBUG = env.debug
ALLOWED_HOSTS = [h.strip() for h in env.allowed_hosts.split(",")]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env.csrf_trusted_origins.split(",")]

# Application definition
INSTALLED_APPS = [
    # Unfold admin (must be before django.contrib.admin)
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "corsheaders",
    "django_filters",
    "graphene_django",
    "django_celery_beat",
    "django_celery_results",
    "django_prometheus",

    # ForgeLink apps
    "apps.core",
    "apps.assets",
    "apps.telemetry",
    "apps.alerts",
    "apps.ai",
    "apps.audit",
    "apps.api",
    "apps.simulator",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # ForgeLink middleware
    "apps.core.middleware.JWTAuthenticationMiddleware",
    "apps.core.middleware.RateLimitMiddleware",
    "apps.core.middleware.AuditMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "apps.core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "apps.core.wsgi.application"
ASGI_APPLICATION = "apps.core.asgi.application"

# Database (PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.db_name,
        "USER": env.db_user,
        "PASSWORD": env.db_password,
        "HOST": env.db_host,
        "PORT": env.db_port,
        "OPTIONS": {
            "options": "-c search_path=forgelink,public"
        },
    }
}

# TDengine configuration (used by telemetry app)
TDENGINE = {
    "HOST": env.tdengine_host,
    "PORT": env.tdengine_port,
    "USER": env.tdengine_user,
    "PASSWORD": env.tdengine_password,
    "DATABASE": env.tdengine_database,
}

# Cache (Redis)
redis_password_part = f":{env.redis_password}@" if env.redis_password else ""
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{redis_password_part}{env.redis_host}:{env.redis_port}/{env.redis_django_db}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Session (Redis)
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = env.factory_timezone
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# Default primary key
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
]
CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# GraphQL
GRAPHENE = {
    "SCHEMA": "apps.api.schema.schema",
    "MIDDLEWARE": [
        "graphql_jwt.middleware.JSONWebTokenMiddleware",
    ],
}

# Celery
CELERY_BROKER_URL = f"redis://{redis_password_part}{env.redis_host}:{env.redis_port}/{env.redis_celery_db}"
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = env.factory_timezone
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Kafka
KAFKA = {
    "BOOTSTRAP_SERVERS": env.kafka_bootstrap_servers,
    "CONSUMER_GROUP_ID": env.kafka_consumer_group_id,
}
KAFKA_BOOTSTRAP_SERVERS = env.kafka_bootstrap_servers

# RabbitMQ
RABBITMQ = {
    "HOST": env.rabbitmq_host,
    "PORT": env.rabbitmq_port,
    "USER": env.rabbitmq_user,
    "PASSWORD": env.rabbitmq_password,
}

# IDP (JWT validation)
IDP = {
    "JWKS_URL": env.idp_jwks_url,
    "JWKS_CACHE_TTL": 3600,  # 1 hour
}

# Telemetry batching
TELEMETRY = {
    "BATCH_SIZE": env.telemetry_batch_size,
    "BATCH_TIMEOUT_MS": env.telemetry_batch_timeout_ms,
}

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": "structlog.processors.JSONRenderer()",
        },
        "console": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console" if DEBUG else "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# Unfold Admin
UNFOLD = {
    "SITE_TITLE": "ForgeLink",
    "SITE_HEADER": "ForgeLink Steel Factory",
    "SITE_SUBHEADER": "Industrial IoT Platform",
    "SITE_SYMBOL": "factory",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
}

# Socket.IO
SOCKETIO = {
    "CORS_ALLOWED_ORIGINS": CORS_ALLOWED_ORIGINS + ["*"],  # Flutter app
    "ASYNC_MODE": "asgi",
    "PING_TIMEOUT": 60,
    "PING_INTERVAL": 25,
}
