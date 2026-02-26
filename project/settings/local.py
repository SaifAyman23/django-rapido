"""Local development settings"""
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Allow all origins in development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
]

# Debug toolbar
INSTALLED_APPS = ["debug_toolbar", *INSTALLED_APPS]
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
INTERNAL_IPS = ["127.0.0.1"]

# Disable SSL in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Logging
import logging
logging.getLogger("django.db.backends").setLevel(logging.DEBUG)