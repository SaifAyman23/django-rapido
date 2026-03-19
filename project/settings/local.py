"""
Local development settings.
"""
import os
from .base import *

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Use console email backend in development
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable security features in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# CORS for local development
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8000").split(",")
CORS_TRUSTED_ORIGINS = os.getenv("CORS_TRUSTED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8000").split(",")

# TODO: Remove these settings in production
# Execute tasks locally (synchronously) instead of sending them to the broker
CELERY_TASK_ALWAYS_EAGER = True
# If an eager task raises an exception, propagate it to the view
CELERY_TASK_EAGER_PROPAGATES = True

# Enable Django Debug Toolbar (if installed)
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1', 'localhost']
except ImportError:
    pass
