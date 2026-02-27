"""
Production settings with security hardening.
"""
import os
from .base import *

DEBUG = False

# Security headers
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# CORS - must be explicitly set in production
CORS_TRUSTED_ORIGINS = os.getenv("CORS_TRUSTED_ORIGINS", "").split(",")

# Allowed hosts - must be explicitly set in production
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# Use proper email backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Logging - less verbose in production
LOGGING['root']['level'] = 'WARNING'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['celery']['level'] = 'WARNING'