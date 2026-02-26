"""Production settings with security hardening"""
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

# CORS
CORS_TRUSTED_ORIGINS = os.getenv("CORS_TRUSTED_ORIGINS", "").split(",")

# Allowed hosts from environment
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")