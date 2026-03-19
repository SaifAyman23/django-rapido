import os
from pathlib import Path
from .unfold_config import *
from dotenv import load_dotenv
from datetime import timedelta

# Determine which environment we're in
ENVIRONMENT = os.getenv('DJANGO_ENVIRONMENT', 'local')

# Load environment variables
load_dotenv('.env')

if ENVIRONMENT == 'production':
    load_dotenv('.env.production', override=True)
else:
    load_dotenv('.env.local', override=True)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECRET_KEY - keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-token")

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
    
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third-party
    'corsheaders',
    "rest_framework",
    "rest_framework_simplejwt",
    # Required only if using token blacklisting:
    'rest_framework_simplejwt.token_blacklist',
    "django_filters",
    "drf_spectacular",
    "channels",
    "django_celery_beat",
    "django_celery_results",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",  # For static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    'django.middleware.locale.LocaleMiddleware',
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

"""
Database configuration.
PostgreSQL setup with connection pooling.
"""

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DB_NAME", "project_db"),
        "USER": os.getenv("DB_USER", "project_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password123"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
        }
    }
}

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }


# Testing configuration
TESTING = os.getenv("TESTING", "False") == "True"
if TESTING:
    DATABASES["default"]["NAME"] = os.getenv("TEST_DATABASE_NAME", "project_test_db")


# Legacy login credentials (consider removing if not needed)
LOGIN_USERNAME = os.getenv("LOGIN_USERNAME", "s@gmail.com")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "1")

# URL Configuration
ROOT_URLCONF = "project.urls"
WSGI_APPLICATION = "project.wsgi.application"

# Custom user model
AUTH_USER_MODEL = "common.CustomUser"

# Default auto field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# https://docs.djangoproject.com/en/5.1/ref/settings/#date-input-formats
DATE_INPUT_FORMATS = [
    "%d.%m.%Y",  # Custom input
    "%Y-%m-%d",  # '2006-10-25'
    "%m/%d/%Y",  # '10/25/2006'
    "%m/%d/%y",  # '10/25/06'
    "%b %d %Y",  # 'Oct 25 2006'
    "%b %d, %Y",  # 'Oct 25, 2006'
    "%d %b %Y",  # '25 Oct 2006'
    "%d %b, %Y",  # '25 Oct, 2006'
    "%B %d %Y",  # 'October 25 2006'
    "%B %d, %Y",  # 'October 25, 2006'
    "%d %B %Y",  # '25 October 2006'
    "%d %B, %Y",  # '25 October, 2006'
]

# https://docs.djangoproject.com/en/5.1/ref/settings/#datetime-input-formats
DATETIME_INPUT_FORMATS = [
    "%d.%m.%Y %H:%M:%S",  # Custom input
    "%Y-%m-%d %H:%M:%S",  # '2006-10-25 14:30:59'
    "%Y-%m-%d %H:%M:%S.%f",  # '2006-10-25 14:30:59.000200'
    "%Y-%m-%d %H:%M",  # '2006-10-25 14:30'
    "%m/%d/%Y %H:%M:%S",  # '10/25/2006 14:30:59'
    "%m/%d/%Y %H:%M:%S.%f",  # '10/25/2006 14:30:59.000200'
    "%m/%d/%Y %H:%M",  # '10/25/2006 14:30'
    "%m/%d/%y %H:%M:%S",  # '10/25/06 14:30:59'
    "%m/%d/%y %H:%M:%S.%f",  # '10/25/06 14:30:59.000200'
    "%m/%d/%y %H:%M",  # '10/25/06 14:30'
]


# Internationalization
LANGUAGE_CODE = "en"
LANGUAGES = [
    ('en', 'English'),
    ('ar', 'العربية'),
]
# Enable internationalization
I18N = True
USE_I18N = True
USE_L10N = True  # Localized formatting (numbers, dates, etc.)

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

TIME_ZONE = "UTC"
USE_TZ = True

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
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
                'dashboard.context_processors.dashboard_context',
            ],
        },
    },
]

# Static & Media files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Email Configuration
# EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

"""
Redis caching configuration.
Session storage and general caching.
"""

# Redis Caching (5.4.0)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("CACHE_URL", "redis://:redis_password@localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                # "timeout": 20,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        }
    }
}

# Use Redis for session storage
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

"""
Celery configuration for async task processing.
Redis as message broker and result backend.
"""
 
# Celery Configuration (Compatible with celery 5.4.0, redis 4.6.0)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://:redis_password@localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://:redis_password@localhost:6379/0")
 
# Serialization
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
 
# Timezone
CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE", "UTC")
CELERY_ENABLE_UTC = True
 
# Task execution and tracking
CELERY_TASK_TRACK_STARTED = True  # FIXED: Removed duplicate definition
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "1800"))  # 30 minutes
CELERY_RESULT_EXPIRES = 3600  # 1 hour
 
# Broker settings
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_HEARTBEAT = 120  # RECOMMENDED: Changed from 0 to 120 (default)
 
# Event monitoring (CRITICAL for Flower)
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_WORKER_SEND_TASK_EVENTS = True
 
# Additional recommended settings for stability
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Fetch one task at a time
CELERY_TASK_ACKS_LATE = True  # Acknowledge after task completion
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Requeue tasks if worker dies
 
# Flower (Celery Monitoring)
FLOWER_USER = os.getenv("FLOWER_USER", "admin")
FLOWER_PASSWORD = os.getenv("FLOWER_PASSWORD", "admin123")
 
"""
============================================================================================
JWT authentication configuration.
REST Framework and SimpleJWT settings.
API documentation configuration (DRF Spectacular).
============================================================================================
"""

# REST Framework (DRF 3.16)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
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
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    'DATE_FORMAT': '%d.%m.%Y',  # Output format for dates
    'DATETIME_FORMAT': '%d.%m.%Y %H:%M:%S',  # Output format for datetimes
    'TIME_FORMAT': '%H:%M:%S',
    'DATE_INPUT_FORMATS': DATE_INPUT_FORMATS,  # Input formats
    'DATETIME_INPUT_FORMATS': DATETIME_INPUT_FORMATS,
}

# JWT Configuration (5.4.0)
# Import SECRET_KEY from base (it's already loaded)

SIMPLE_JWT = {
    # Token lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),

    # Rotation & blacklisting
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    "UPDATE_LAST_LOGIN": True,

    # Signing
    "ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),   
    "SIGNING_KEY": os.getenv("JWT_SECRET_KEY", SECRET_KEY),         # use SECRET_KEY or a separate strong key
    "VERIFYING_KEY": None,                                          # for asymmetric algos (RS256, ES256)

    # Header config
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',

    # User identification
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # Token classes
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    # JTI (unique token ID)
    'JTI_CLAIM': 'jti',

    # Sliding tokens (optional alternative to access/refresh pair)
    # 'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    # 'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    # 'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),

    # Serializers
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
    'TOKEN_REFRESH_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenRefreshSerializer',
    'TOKEN_VERIFY_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenVerifySerializer',
    'TOKEN_BLACKLIST_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenBlacklistSerializer',
}



# DRF Spectacular (API Docs)
SPECTACULAR_SETTINGS = {
    "TITLE": os.getenv("API_TITLE", "Project API"),
    "DESCRIPTION": os.getenv("API_DESCRIPTION", "Modern Django REST API with latest technologies"),
    "VERSION": os.getenv("API_VERSION", "1.0.0"),
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "SERVERS": [
        {"url": "http://localhost:8000", "description": "Local development"},
        {"url": "https://api.example.com", "description": "Production"},
    ],
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "AUTHENTICATION_FLOWS": {
        "bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    },
    "COMPONENTS": {
        "securitySchemes": {
            "Bearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        },
        # Added schemas for token responses (this doesn't conflict)
        "schemas": {
            "Token": {
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "description": "Authentication token",
                        "example": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
                    }
                }
            }
        }
    },
    # Added Swagger UI customization (this is fine)
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "tryItOutEnabled": True,
    },
}


"""
Security settings - CORS, SSL, CSRF, etc.
Base security settings (overridden by environment-specific settings).
"""

# CORS Configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
CORS_TRUSTED_ORIGINS = os.getenv("CORS_TRUSTED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

# Security Settings (defaults - overridden in production.py)
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False") == "True"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False") == "True"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False") == "True"
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))

SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
}

# CSRF_FAILURE_VIEW = "common.views.csrf_failure"

# Admin User Configuration (for initial setup)
DJANGO_SUPERUSER_USERNAME = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
DJANGO_SUPERUSER_EMAIL = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
DJANGO_SUPERUSER_PASSWORD = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin123")


"""
Logging configuration.
Console and file handlers with rotation.
"""

# Create logs directory
LOG_DIR = BASE_DIR / "logs"
try:
    LOG_DIR.mkdir(exist_ok=True, parents=True)
except PermissionError:
    # Fallback to /tmp if we can't create the log directory
    LOG_DIR = Path('/tmp/logs')
    LOG_DIR.mkdir(exist_ok=True, parents=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}



"""
Django Channels configuration for WebSockets.
"""

ASGI_APPLICATION = "project.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://:redis_password@localhost:6379/0")],
        },
    },
}


"""
Optional third-party service configurations.
AWS, Sentry, etc.
"""

# ===========================
# AWS Configuration (Optional)
# ===========================
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", None)
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")

# If AWS credentials are provided, configure S3 storage
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
    # Uncomment and configure as needed
    # DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    # STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    pass

# ===========================
# Sentry (Error Tracking)
# ===========================
SENTRY_DSN = os.getenv("SENTRY_DSN", None)
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True
    )

# ===========================
# Docker Configuration
# ===========================
DOCKER_ENVIRONMENT = os.getenv("DOCKER_ENVIRONMENT", "local")

