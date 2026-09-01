"""Base Django settings — shared across all environments.

Configures database, auth, middleware, REST, JWT, Celery, and caching.
Environment-specific overrides live in local.py and production.py.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

from .unfold_config import *

# Determine which environment we're in
ENVIRONMENT = os.getenv("DJANGO_ENVIRONMENT", "local")

# Load environment variables
load_dotenv(".env")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─────────────────────────────────────────────────────────────────
# Testing configuration
# REUSE: Explicit TESTING env wins; fallback to sys.argv detection.
# Prevents prod silently running in SQLite/eager-Celery mode.
# ─────────────────────────────────────────────────────────────────
TESTING = os.getenv("TESTING", "False").lower() == "true" or "test" in sys.argv

if TESTING:
    os.environ["TESTING"] = "True"

# Run Celery tasks synchronously during tests
if TESTING:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# SECRET_KEY — fail fast if missing in non-test env
# REUSE: never ship a hardcoded fallback in production
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if TESTING:
        SECRET_KEY = "testing-only-insecure-secret-key"
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set in the environment or .env - no fallback is allowed."
        )

# Debug mode (overridden by environment-specific settings)
DEBUG = os.getenv("DEBUG", "True") == "True"

# Allowed hosts (overridden by environment-specific settings)
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    # Unfold admin (before django.contrib.admin)
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.inlines",
    # Local apps
    "accounts",
    "common",
    "notifications",  # REUSE: FCM + in-app inbox (generic)
    "compliance",  # REUSE: FAQ + legal docs (translatable)
    "contacts",  # REUSE: contact form + singleton business info
    # Third-party — must be before django.contrib.admin for modeltranslation
    # REUSE: modeltranslation enables en/ar fields; markdownx enables Markdown admin
    "modeltranslation",
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "markdownx",
    # Social Authentication (opt-in — uncomment providers you need)
    # REUSE: allauth for Google/Facebook OAuth; adapter handles duplicate SocialApp bug
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    # "allauth.socialaccount.providers.google",
    # "allauth.socialaccount.providers.facebook",
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    # "allauth.account.auth_backends.AuthenticationBackend",  # REUSE: enable when using social login
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # Live logs — in-memory SSE ring buffer (exact replica from ras-elbar-go)
    "dashboard.live_logs.LiveLogsMiddleware",
    # Custom middleware — enable selectively
    "common.middleware.RequestLoggingMiddleware",
    "common.middleware.PerformanceMonitoringMiddleware",
    "common.middleware.SecurityHeadersMiddleware",
    "common.middleware.RequestEnhancementMiddleware",
]

# ─────────────────────────────────────────────────────────────────
# Database — PostgreSQL in prod, SQLite in tests
# REUSE: CONN_MAX_AGE 600 + connect_timeout; TESTING switches to sqlite
# ─────────────────────────────────────────────────────────────────
if not TESTING:
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
            "NAME": os.getenv("DB_NAME", "project_db"),
            "USER": os.getenv("DB_USER", "project_user"),
            "PASSWORD": os.getenv("DB_PASSWORD", "password123"),
            "HOST": os.getenv("DB_HOST", "db"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 600,
            "OPTIONS": {
                "connect_timeout": 10,
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Login form presets (for dashboard LoginForm auto-fill)
LOGIN_USERNAME = os.getenv("LOGIN_USERNAME", "")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "")

# URL Configuration
ROOT_URLCONF = "project.urls"
WSGI_APPLICATION = "project.wsgi.application"
ASGI_APPLICATION = "project.asgi.application"

# Custom user model
AUTH_USER_MODEL = "common.CustomUser"

# Default auto field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# https://docs.djangoproject.com/en/5.1/ref/settings/#date-input-formats
DATE_INPUT_FORMATS = [
    "%d.%m.%Y",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%b %d %Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%d %b, %Y",
    "%B %d %Y",
    "%B %d, %Y",
    "%d %B %Y",
    "%d %B, %Y",
]

# https://docs.djangoproject.com/en/5.1/ref/settings/#datetime-input-formats
DATETIME_INPUT_FORMATS = [
    "%d.%m.%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S.%f",
    "%m/%d/%Y %H:%M",
    "%m/%d/%y %H:%M:%S",
    "%m/%d/%y %H:%M:%S.%f",
    "%m/%d/%y %H:%M",
]


# Internationalization
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("ar", "العربية"),
]
USE_I18N = True
USE_L10N = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]

MODELTRANSLATION_DEFAULT_LANGUAGE = "en"
MODELTRANSLATION_LANGUAGES = ("en", "ar")
MODELTRANSLATION_FALLBACK_LANGUAGES = ("en", "ar")
MODELTRANSLATION_PREFER_ADMIN_LANGUAGE = True

TIME_ZONE = "UTC"
USE_TZ = True

# REUSE: Business local time for hours-gated features (e.g. is_ordering_open)
BUSINESS_TIME_ZONE = os.getenv("BUSINESS_TIME_ZONE", "Africa/Cairo")

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "dashboard/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dashboard.context_processors.dashboard_context",
                "dashboard.context_processors.unfold_colors",
            ],
        },
    },
]

# ─────────────────────────────────────────────────────────────────
# allauth — provider verification only
# REUSE: uncomment providers + adapter when enabling social login
# ─────────────────────────────────────────────────────────────────
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_STORE_TOKENS = True
# SOCIALACCOUNT_ADAPTER = "accounts.auth.adapters.SocialAccountAdapter"  # REUSE: enable with social login
# SOCIALACCOUNT_PROVIDERS = {
#     "google": {
#         "SCOPE": ["openid", "profile", "email"],
#         "APP": {"client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID"), "secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")},
#     },
#     "facebook": {
#         "SCOPE": ["email", "public_profile"],
#         "VERSION": "v21.0",
#         "APP": {"client_id": os.getenv("FACEBOOK_OAUTH_CLIENT_ID"), "secret": os.getenv("FACEBOOK_OAUTH_CLIENT_SECRET")},
#     },
# }

# Static & Media files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Email Configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

# ─────────────────────────────────────────────────────────────────
# Upload limits — REUSE: allow Excel/CSV base64 imports via Celery
# ─────────────────────────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB

"""
Redis caching configuration.
"""
if not TESTING:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("CACHE_URL", "redis://:redis_password@redis:6379/1"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {"max_connections": 50},
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
            },
        }
    }

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

"""
Celery configuration
"""
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://:redis_password@redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://:redis_password@redis:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE", "UTC")
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "1800"))
CELERY_RESULT_EXPIRES = 3600
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_HEARTBEAT = 120
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

FLOWER_USER = os.getenv("FLOWER_USER", "admin")
FLOWER_PASSWORD = os.getenv("FLOWER_PASSWORD", "admin123")

# Celery Beat — example schedule (uncomment per app)
# REUSE: register periodic tasks here, e.g. scan_stale_orders
CELERY_BEAT_SCHEDULE = {
    # "scan-stale-objects": {
    #     "task": "myapp.tasks.scan_stale_objects",
    #     "schedule": 60,
    # },
}

"""
JWT / REST / Spectacular
"""
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth": "30/minute",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DATE_FORMAT": "%Y-%m-%d",
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "TIME_FORMAT": "%H:%M:%S",
    "DATE_INPUT_FORMATS": DATE_INPUT_FORMATS,
    "DATETIME_INPUT_FORMATS": DATETIME_INPUT_FORMATS,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
    # REUSE: dedicated JWT key falls back to SECRET_KEY — never commit JWT_SECRET_KEY
    "SIGNING_KEY": os.getenv("JWT_SECRET_KEY") or SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
}

SPECTACULAR_SETTINGS = {
    "TITLE": os.getenv("API_TITLE", "Django Rapido API"),
    "DESCRIPTION": os.getenv("API_DESCRIPTION", "Modern Django REST API starter template"),
    "VERSION": os.getenv("API_VERSION", "2.0.0"),
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "SERVERS": [
        {"url": "http://localhost:8000", "description": "Local development"},
        {"url": "https://api.example.com", "description": "Production"},
    ],
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    # REUSE: stable names for choice enums sharing field names (status/type)
    "ENUM_NAME_OVERRIDES": {
        "UserStatusEnum": "common.models.CustomUser.Status",
        "OrderStatusEnum": "orders.models.OrderStatus",
        "LocationTypeEnum": "addresses.models.LocationType",
        "OTPTypeEnum": "accounts.models.OTPRecord.OTPType",
    },
    "AUTHENTICATION_FLOWS": {"bearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}},
    "COMPONENTS": {
        "securitySchemes": {"Bearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}},
        "schemas": {
            "Token": {
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "description": "Authentication token",
                        "example": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
                    }
                },
            }
        },
    },
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True, "tryItOutEnabled": True},
}

"""
Security — CORS, SSL, CSRF
"""
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://localhost:5173"
).split(",")
CORS_ALLOWED_HEADERS = (
    os.getenv("CORS_ALLOWED_HEADERS", "*").split(",")
    if os.getenv("CORS_ALLOWED_HEADERS")
    else ["*"]
)
CORS_TRUSTED_ORIGINS = (
    os.getenv("CORS_TRUSTED_ORIGINS", "").split(",") if os.getenv("CORS_TRUSTED_ORIGINS") else []
)

# REUSE: force off during tests so test client runs over plain HTTP
SECURE_SSL_REDIRECT = False if TESTING else os.getenv("SECURE_SSL_REDIRECT", "False") == "True"
SESSION_COOKIE_SECURE = False if TESTING else os.getenv("SESSION_COOKIE_SECURE", "False") == "True"
CSRF_COOKIE_SECURE = False if TESTING else os.getenv("CSRF_COOKIE_SECURE", "False") == "True"
SECURE_HSTS_SECONDS = 0 if TESTING else int(os.getenv("SECURE_HSTS_SECONDS", "0"))

SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
}

# Admin User Configuration
DJANGO_SUPERUSER_USERNAME = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
DJANGO_SUPERUSER_EMAIL = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
DJANGO_SUPERUSER_PASSWORD = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin123")

LOGIN_USERNAME = os.getenv("LOGIN_USERNAME", "")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "")

"""
Logging
"""
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {asctime} {message}", "style": "{"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "verbose"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

# Docker helpers
DOCKER_ENVIRONMENT = os.getenv("DOCKER_ENVIRONMENT", "local")

# Firebase — REUSE: uncomment if using FCM push
# GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
#     "GOOGLE_APPLICATION_CREDENTIALS",
#     os.path.join(BASE_DIR, "firebase-adminsdk.json"),
# )

ASGI_APPLICATION = "project.asgi.application"
