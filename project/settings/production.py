"""Production settings with TLS, HSTS, and security hardening."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

# REUSE: do not harden when running tests over plain HTTP
if not TESTING:
    DEBUG = False

    # Behind nginx TLS termination — trust X-Forwarded-Proto
    # REUSE: required for SECURE_SSL_REDIRECT behind reverse proxy
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # REUSE: ramp HSTS 0 → 300 → 86400 → 31536000 after confirming TLS
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"

    # Must be explicitly set in production — fail fast if empty
    _allowed = os.getenv("ALLOWED_HOSTS", "")
    if not _allowed:
        raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production .env")
    ALLOWED_HOSTS = _allowed.split(",")

    _cors_trusted = os.getenv("CORS_TRUSTED_ORIGINS", "")
    if _cors_trusted:
        CORS_TRUSTED_ORIGINS = _cors_trusted.split(",")
        CORS_ALLOWED_ORIGINS = _cors_trusted.split(",")

# Use proper email backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Logging - less verbose in production
LOGGING["root"]["level"] = "WARNING"
LOGGING["loggers"]["django"]["level"] = "WARNING"
LOGGING["loggers"]["celery"]["level"] = "WARNING"
