"""
Security settings - CORS, SSL, CSRF, etc.
Base security settings (overridden by environment-specific settings).
"""
import os

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