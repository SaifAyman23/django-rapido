"""Local development settings — relaxed security, eager Celery, debug toolbar."""

import os

from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Disable security features in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 0

# CORS for local development — only override if env var is set
# REUSE: conditional override respects .env without hardcoding
_cors_env = os.getenv("CORS_ALLOWED_ORIGINS")
if _cors_env is not None:
    CORS_ALLOWED_ORIGINS = _cors_env.split(",")
_cors_trusted_env = os.getenv("CORS_TRUSTED_ORIGINS")
if _cors_trusted_env is not None:
    CORS_TRUSTED_ORIGINS = _cors_trusted_env.split(",")

# Execute tasks synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Enable Django Debug Toolbar (if installed)
try:
    INSTALLED_APPS += ["debug_toolbar"]
    # MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
except ImportError:
    pass
