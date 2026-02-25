# Django Project Complete Setup Guide 🚀

A comprehensive guide for setting up a production-ready Django project with modern best practices, all necessary packages, and a complete project structure template.

---

## Table of Contents

1. [Prerequisites & Installation](#prerequisites--installation)
2. [Project Architecture Overview](#project-architecture-overview)
3. [Initial Setup](#initial-setup)
4. [Package Installation & Configuration](#package-installation--configuration)
5. [Database Setup (PostgreSQL)](#database-setup-postgresql)
6. [Project Structure](#project-structure)
7. [Core Configurations](#core-configurations)
8. [Reusable Components](#reusable-components)
9. [Complete Project Template](#complete-project-template)
10. [Deployment Guide](#deployment-guide)

---

## Prerequisites & Installation

### System Requirements

- Python 3.9+
- PostgreSQL 12+
- Docker & Docker Compose
- Git

### Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

---

## Project Architecture Overview

This guide covers building a modern Django application with:

- **REST APIs** via Django REST Framework
- **Real-time Communication** via Django Channels
- **Async Task Processing** via Celery + Beat + Redis
- **Authentication** via SimpleJWT tokens
- **API Documentation** via drf-spectacular
- **Testing** via pytest-django
- **Admin Interface** enhancement via django-unfold
- **Caching** via django-redis
- **Filtering & Pagination** via django-filters
- **Containerization** via Docker
- **Production Server** via Gunicorn + Uvicorn

---

## Initial Setup

### Step 1: Create Django Project

```bash
# Install Django
pip install django

# Create project
django-admin startproject project .

# Create initial apps
python manage.py startapp accounts
python manage.py startapp common
python manage.py startapp api
```

### Step 2: Initialize Git

```bash
git init
echo "venv/" > .gitignore
echo ".env" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".pytest_cache/" >> .gitignore
echo "db.sqlite3" >> .gitignore
```

---

## Package Installation & Configuration

### Step 1: Install All Packages

```bash
pip install --upgrade pip

# Core dependencies
pip install django==4.2.0
pip install djangorestframework==3.14.0
pip install django-filter==23.3

# JWT Authentication
pip install djangorestframework-simplejwt==5.3.0

# API Documentation
pip install drf-spectacular==0.26.5

# Admin UI Enhancement
pip install django-unfold==0.24.0

# Real-time Communication
pip install django-channels==4.0.0
pip install django-channels-redis==4.1.0

# Async Task Processing
pip install celery==5.3.4
pip install django-celery-beat==2.5.0
pip install django-celery-results==2.5.1

# Caching
pip install django-redis==5.4.0

# Database
pip install psycopg2-binary==2.9.9

# Environment variables
pip install python-dotenv==1.0.0

# Testing
pip install pytest==7.4.3
pip install pytest-django==4.7.0
pip install pytest-cov==4.1.0

# ASGI Server (for Channels)
pip install uvicorn==0.24.0

# WSGI Server (for REST APIs)
pip install gunicorn==21.2.0

# Utilities
pip install python-dateutil==2.8.2
pip install pytz==2023.3

# Generate requirements
pip freeze > requirements.txt
```

### Step 2: Create .env File

```bash
# .env (DO NOT commit to git)
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=project_db
DB_USER=project_user
DB_PASSWORD=secure_password_here
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production

# Email (Optional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# Celery
CELERY_TIMEZONE=UTC
```

---

## Database Setup (PostgreSQL)

### Step 1: Create Docker Compose File

```yaml
# docker-compose.yml
version: '3.9'

services:
  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    container_name: project_db
    environment:
      POSTGRES_DB: project_db
      POSTGRES_USER: project_user
      POSTGRES_PASSWORD: secure_password_here
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U project_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis for Caching and Celery
  redis:
    image: redis:7-alpine
    container_name: project_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Django Web Application
  web:
    build: .
    container_name: project_web
    command: >
      sh -c "python manage.py migrate &&
             python manage.py createsuperuser --no-input &&
             gunicorn project.wsgi:application --bind 0.0.0.0:8000"
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Celery Worker
  celery_worker:
    build: .
    container_name: project_celery_worker
    command: celery -A project worker --loglevel=info
    volumes:
      - .:/app
    environment:
      - DEBUG=False
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - db

  # Celery Beat (Scheduler)
  celery_beat:
    build: .
    container_name: project_celery_beat
    command: celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    environment:
      - DEBUG=False
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - db

volumes:
  postgres_data:
  redis_data:
```

### Step 2: Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create superuser (requires DJANGO_SUPERUSER_PASSWORD env var)
ENV DJANGO_SUPERUSER_USERNAME=admin
ENV DJANGO_SUPERUSER_EMAIL=admin@example.com
ENV DJANGO_SUPERUSER_PASSWORD=admin123

EXPOSE 8000

CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Step 3: Run PostgreSQL with Docker

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f web

# Stop services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Step 4: Local Database Setup (Without Docker)

```bash
# On macOS with Homebrew
brew install postgresql

# Start PostgreSQL
brew services start postgresql

# Create database and user
psql postgres
CREATE DATABASE project_db;
CREATE USER project_user WITH PASSWORD 'secure_password_here';
ALTER ROLE project_user SET client_encoding TO 'utf8';
ALTER ROLE project_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE project_user SET default_transaction_deferrable TO on;
ALTER ROLE project_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;
\q
```

---

## Project Structure

```
project/
├── project/                    # Main project config
│   ├── __init__.py
│   ├── settings/               # Modular settings
│   │   ├── __init__.py
│   │   ├── base.py             # Base settings
│   │   ├── local.py            # Local development
│   │   ├── production.py        # Production settings
│   │   └── celery.py            # Celery config
│   ├── asgi.py                 # Async Server Gateway Interface
│   ├── wsgi.py                 # Web Server Gateway Interface
│   ├── urls.py                 # Main URL router
│   └── routing.py              # WebSocket routing for Channels
│
├── accounts/                   # User management app
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── viewsets.py
│   ├── urls.py
│   ├── permissions.py
│   ├── tests.py
│   └── admin.py
│
├── common/                     # Shared utilities
│   ├── models.py               # Abstract models, mixins
│   ├── serializers.py          # Common serializers
│   ├── viewsets.py             # Base viewsets
│   ├── permissions.py          # Custom permissions
│   ├── helpers.py              # Helper functions
│   ├── decorators.py           # Decorators
│   ├── pagination.py           # Pagination classes
│   ├── filters.py              # Filter classes
│   ├── exceptions.py           # Custom exceptions
│   ├── constants.py            # Constants & enums
│   └── admin.py
│
├── api/                        # Main API app (optional)
│   ├── v1/                     # API version
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── serializers.py
│   └── tests.py
│
├── docker/                     # Docker configuration
│   ├── Dockerfile
│   ├── .dockerignore
│   └── entrypoint.sh
│
├── tests/                      # Global test configuration
│   ├── __init__.py
│   ├── conftest.py             # pytest fixtures
│   └── factories.py            # Test data factories
│
├── static/                     # Static files
│   ├── css/
│   ├── js/
│   └── images/
│
├── media/                      # User-uploaded files
│
├── .env                        # Environment variables (NOT in git)
├── .env.example                # Example env file
├── .gitignore
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Docker services
├── Dockerfile
├── manage.py
├── pytest.ini                  # pytest configuration
└── README.md
```

---

## Core Configurations

### 1. Settings Structure (Modular)

#### `project/settings/base.py`

```python
"""
Base settings for the project.
This file contains shared settings for all environments.
"""

import os
from pathlib import Path
from datetime import timedelta
import logging.config

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: Load from environment variable in production
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-temporary-key-for-dev")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
# IMPORTANT: Order matters for some apps (django-unfold must come before django.contrib.admin)
INSTALLED_APPS = [
    # Unfold Admin (must be before django.contrib.admin)
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.inlines",
    
    # Django default apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "channels",
    "django_celery_beat",
    "django_celery_results",
    
    # Local apps
    "accounts.apps.AccountsConfig",
    "common.apps.CommonConfig",
    "api.apps.ApiConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"

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

# Database configuration
# TODO: Load from environment variables for production
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

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

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files (User uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ===========================
# REST Framework Configuration
# ===========================
# TODO: Customize authentication and pagination based on project needs
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.CustomPagination",
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
}

# ===========================
# JWT Configuration
# ===========================
# TODO: Change secret key in production, adjust token lifetime as needed
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.getenv("JWT_SECRET_KEY", SECRET_KEY),
}

# ===========================
# Celery Configuration
# ===========================
# TODO: Update for production Celery setup
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE", "UTC")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# ===========================
# Redis Caching Configuration
# ===========================
# TODO: Configure cache backend for session management
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Session cache backend
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ===========================
# Channels Configuration (WebSocket Support)
# ===========================
# TODO: Configure for production with proper channel layer
ASGI_APPLICATION = "project.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/0")],
        },
    },
}

# ===========================
# Email Configuration
# ===========================
# TODO: Configure email backend for production
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")

# ===========================
# Logging Configuration
# ===========================
# TODO: Customize logging for your needs
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# ===========================
# DRF Spectacular (API Documentation)
# ===========================
# TODO: Update with your API title, description, and version
SPECTACULAR_SETTINGS = {
    "TITLE": "Project API",
    "DESCRIPTION": "API documentation for Project",
    "VERSION": "1.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
    "SERVERS": [
        {"url": "http://localhost:8000", "description": "Local development"},
        {"url": "https://api.example.com", "description": "Production"},
    ],
}

# ===========================
# Django Unfold Admin Configuration
# ===========================
# TODO: Customize admin interface as needed
UNFOLD = {
    "SITE_HEADER": "Project Admin",
    "SITE_TITLE": "Project Administration",
    "SITE_URL": "/",
    "DASHBOARD_CALLBACK": "common.admin.dashboard_callback",
    "SIDEBAR": {
        "show": True,
        "navigation": [
            {
                "title": "Users",
                "separator": False,
                "collapsible": False,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": "/admin/auth/user/",
                    },
                ],
            },
        ],
    },
}

# ===========================
# Custom Settings
# ===========================
# TODO: Add custom application settings
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
```

#### `project/settings/local.py`

```python
"""
Local development settings.
Extends base.py with development-specific configurations.
"""

from .base import *

# Override for local development
DEBUG = True
ALLOWED_HOSTS = ["*"]

# Disable HTTPS requirement locally
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Use SQLite for local development (if not using PostgreSQL)
# DATABASES["default"] = {
#     "ENGINE": "django.db.backends.sqlite3",
#     "NAME": BASE_DIR / "db.sqlite3",
# }

# Enable Django Debug Toolbar
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
INTERNAL_IPS = ["127.0.0.1"]
```

#### `project/settings/production.py`

```python
"""
Production settings.
Extends base.py with production-specific security configurations.
"""

from .base import *

# Security settings for production
# TODO: Update these values for your production domain
DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
}

# Allowed hosts for production
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# Database must be PostgreSQL in production
# Configured via environment variables

# Static files compression
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
```

#### `project/settings/celery.py`

```python
"""
Celery configuration for the project.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.base")

app = Celery("project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Celery Beat Schedule
# TODO: Add your scheduled tasks here
CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-tokens": {
        "task": "accounts.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    },
    "send-notifications": {
        "task": "common.tasks.send_pending_notifications",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
```

### 2. Update Main Settings Import

Create `project/settings/__init__.py`:

```python
"""
Settings module for the project.
Import the appropriate settings file based on environment.
"""

import os
from django.conf import settings

# Get the current environment (default: local)
ENVIRONMENT = os.getenv("DJANGO_ENVIRONMENT", "local")

if ENVIRONMENT == "production":
    from .production import *  # noqa
elif ENVIRONMENT == "local":
    from .local import *  # noqa
else:
    from .base import *  # noqa
```

### 3. Update `manage.py`

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

### 4. Update `project/wsgi.py`

```python
"""
WSGI config for project.
It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
application = get_wsgi_application()
```

### 5. Create `project/asgi.py`

```python
"""
ASGI config for project.
It exposes the ASGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

# Fetch Django ASGI application early to ensure AppRegistry is populated
# before importing routing modules that may import ORM models.
django_asgi_app = get_asgi_application()

# TODO: Update with your actual WebSocket URL patterns
from project.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        # Django's ASGI application to handle traditional HTTP requests
        "http": django_asgi_app,
        # WebSocket chat handler with authentication
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
```

### 6. Create `project/routing.py`

```python
"""
ASGI routing configuration for WebSocket connections.
"""

from django.urls import re_path
# TODO: Import your WebSocket consumers here
# from accounts.consumers import NotificationConsumer

websocket_urlpatterns = [
    # TODO: Add your WebSocket URL patterns
    # re_path(r"ws/notifications/(?P<room_name>\w+)/$", NotificationConsumer.as_asgi()),
]
```

### 7. Update `project/urls.py`

```python
"""
Main URL configuration for the project.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# API URLs
api_patterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/accounts/", include("accounts.urls")),
    # TODO: Add more API endpoints
]

# Admin panel
admin_patterns = [
    path("admin/", admin.site.urls),
]

# Health check endpoint (for Docker/monitoring)
health_patterns = [
    path("health/", lambda request: __import__("django.http", fromlist=["JsonResponse"]).JsonResponse({"status": "ok"})),
]

urlpatterns = api_patterns + admin_patterns + health_patterns

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

---

## Reusable Components

### 1. Abstract Models & Mixins (`common/models.py`)

```python
"""
Abstract models and mixins for reusable model components.
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
import uuid


class BaseModel(models.Model):
    """
    Abstract base model with common fields.
    All models should inherit from this for consistency.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        # TODO: Override this in child models
        return f"{self.__class__.__name__} - {self.id}"


class TimestampModel(models.Model):
    """
    Mixin for models that need timestamp tracking.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Mixin for soft delete functionality.
    Records are marked as deleted instead of being removed.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark the record as deleted without removing it."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    @classmethod
    def active_objects(cls):
        """Get only non-deleted objects."""
        return cls.objects.filter(is_deleted=False)


class StatusModel(models.Model):
    """
    Mixin for models with status tracking.
    """
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True
    )

    class Meta:
        abstract = True


class CustomUser(AbstractUser):
    """
    Custom user model with additional fields.
    TODO: Add custom fields specific to your project
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.get_full_name() or self.username

    def mark_as_verified(self):
        """Mark user as verified."""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()
```

### 2. Base Serializers (`common/serializers.py`)

```python
"""
Reusable base serializers for DRF.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class BaseSerializer(serializers.ModelSerializer):
    """
    Base serializer with common functionality.
    All serializers should inherit from this.
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        abstract = True


class UserSerializer(BaseSerializer):
    """User serializer for displaying user information."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "avatar",
            "is_verified",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_full_name(self, obj):
        """TODO: Custom logic to get full name"""
        return obj.get_full_name()


class ListSerializer(BaseSerializer):
    """
    Base serializer for list view responses.
    Simplified version of detailed serializer.
    """
    pass


class DetailSerializer(BaseSerializer):
    """
    Base serializer for detail view responses.
    Can include nested relationships.
    """
    pass


class CreateUpdateSerializer(serializers.ModelSerializer):
    """
    Base serializer for create/update operations.
    Usually has write permissions only.
    """
    class Meta:
        abstract = True


class ErrorSerializer(serializers.Serializer):
    """Standard error response serializer."""
    error = serializers.CharField()
    detail = serializers.CharField(required=False)
    code = serializers.CharField(required=False)
```

### 3. Base ViewSets (`common/viewsets.py`)

```python
"""
Reusable base viewsets with common functionality.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter


class BaseViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet with common CRUD operations and utilities.
    All viewsets should inherit from this.
    
    TODO: Override the following in child classes:
    - queryset
    - serializer_class
    - permission_classes
    - filter_backends
    - filterset_fields
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    def get_queryset(self):
        """
        Override this method to filter queryset based on user.
        """
        # TODO: Implement user-specific filtering
        queryset = super().get_queryset()
        return queryset

    def get_serializer_class(self):
        """
        Use different serializers for different actions.
        """
        # TODO: Customize based on your needs
        if self.action == "list":
            return self.list_serializer_class
        elif self.action == "create" or self.action == "update":
            return self.create_update_serializer_class
        return self.serializer_class

    def get_permissions(self):
        """
        Customize permissions based on action.
        """
        # TODO: Implement action-specific permissions
        if self.action in ["list", "retrieve"]:
            permission_classes = []  # Allow anyone to read
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def my_items(self, request):
        """Get items belonging to the current user."""
        # TODO: Implement logic to filter items for current user
        queryset = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """Hook to save additional data during creation."""
        # TODO: Add custom logic before saving
        serializer.save()

    def perform_update(self, serializer):
        """Hook to save additional data during update."""
        # TODO: Add custom logic before saving
        serializer.save()

    def perform_destroy(self, instance):
        """Hook for custom deletion logic."""
        # TODO: Implement soft delete if needed
        instance.delete()


class ReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for displaying data without modification.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    def get_queryset(self):
        """TODO: Override in child classes"""
        return super().get_queryset()
```

### 4. Custom Permissions (`common/permissions.py`)

```python
"""
Custom permissions for the API.
"""

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Allow access only to the owner of the object.
    Model must have an 'owner' or 'user' field.
    """
    def has_object_permission(self, request, view, obj):
        # TODO: Customize owner field name if different
        owner_field = getattr(obj, "user", None) or getattr(obj, "owner", None)
        return owner_field == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow owner to edit, others can only read.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # TODO: Customize owner field name if different
        owner_field = getattr(obj, "user", None) or getattr(obj, "owner", None)
        return owner_field == request.user


class IsAdmin(permissions.BasePermission):
    """
    Allow access only to admin users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsAuthenticated(permissions.BasePermission):
    """
    Allow access only to authenticated users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow admins to edit, others can only read.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
```

### 5. Helper Functions (`common/helpers.py`)

```python
"""
Utility helper functions used throughout the application.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


# ===========================
# String & Encoding Helpers
# ===========================

def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """
    Hash a password using PBKDF2 algorithm.
    Returns tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify a password against its hash."""
    new_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(new_hash, hashed)


# ===========================
# Date & Time Helpers
# ===========================

def get_next_weekday(day: int, current_date: Optional[datetime] = None) -> datetime:
    """
    Get the next occurrence of a specific weekday.
    Args:
        day: Weekday (0=Monday, 6=Sunday)
        current_date: Start date (defaults to today)
    Returns:
        datetime object for next occurrence of the weekday
    """
    if current_date is None:
        current_date = datetime.now()
    
    days_ahead = day - current_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return current_date + timedelta(days=days_ahead)


def is_date_in_past(date: datetime) -> bool:
    """Check if a date is in the past."""
    return date < datetime.now()


# ===========================
# Validation Helpers
# ===========================

def is_valid_email(email: str) -> bool:
    """
    Simple email validation.
    TODO: Use django email validation instead
    """
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def is_valid_phone(phone: str) -> bool:
    """Validate phone number format."""
    import re
    # Simple validation for international format
    pattern = r"^\+?1?\d{9,15}$"
    return re.match(pattern, phone.replace(" ", "").replace("-", "")) is not None


# ===========================
# Pagination & Filtering Helpers
# ===========================

def paginate_queryset(queryset, page: int = 1, page_size: int = 10):
    """
    Paginate a queryset manually.
    Args:
        queryset: Django QuerySet
        page: Page number (1-indexed)
        page_size: Items per page
    Returns:
        Tuple of (paginated_items, total_count, total_pages)
    """
    total_count = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = queryset[start:end]
    total_pages = (total_count + page_size - 1) // page_size
    return paginated_items, total_count, total_pages


# ===========================
# Notification & Email Helpers
# ===========================

def send_email_async(subject: str, message: str, recipient_list: list):
    """
    Queue email to be sent asynchronously.
    TODO: Implement with Celery task
    """
    from accounts.tasks import send_email_task
    send_email_task.delay(subject, message, recipient_list)


def format_datetime_for_display(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime for display."""
    return dt.strftime(format_str)


# ===========================
# Data Transformation Helpers
# ===========================

def dict_to_queryset_kwargs(**kwargs) -> Dict[str, Any]:
    """
    Convert dictionary to Django ORM filter kwargs.
    Useful for dynamic filtering.
    TODO: Customize based on your filtering needs
    """
    filter_kwargs = {}
    for key, value in kwargs.items():
        if value is not None:
            filter_kwargs[key] = value
    return filter_kwargs


def flatten_dict(d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
```

### 6. Pagination Classes (`common/pagination.py`)

```python
"""
Custom pagination classes for API responses.
"""

from rest_framework.pagination import PageNumberPagination, CursorPagination


class CustomPagination(PageNumberPagination):
    """
    Custom pagination with configurable page size.
    """
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        """
        Override to include pagination metadata in response.
        """
        from rest_framework.response import Response
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "page_size": self.page_size,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "results": data,
            }
        )


class LargeResultsSetPagination(CustomPagination):
    """Pagination for large result sets."""
    page_size = 100
    max_page_size = 1000


class SmallResultsSetPagination(CustomPagination):
    """Pagination for small result sets."""
    page_size = 5
    max_page_size = 20


class CursorBasedPagination(CursorPagination):
    """
    Cursor-based pagination for more efficient paging of large datasets.
    Better for real-time data that changes frequently.
    """
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"  # TODO: Customize based on your model
```

### 7. Filter Classes (`common/filters.py`)

```python
"""
Custom filter classes for API filtering.
"""

from django_filters import rest_framework as filters
from django.db.models import Q


class BaseFilterSet(filters.FilterSet):
    """
    Base FilterSet with common filtering logic.
    """
    # TODO: Add custom filters in child classes
    class Meta:
        abstract = True


class SearchableFilterSet(BaseFilterSet):
    """
    FilterSet with search capability across multiple fields.
    """
    search = filters.CharFilter(
        method="filter_search",
        label="Search across multiple fields"
    )

    def filter_search(self, queryset, name, value):
        """
        TODO: Implement search across your model fields
        Example:
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(author__name__icontains=value)
        )
        """
        return queryset
```

### 8. Custom Exceptions (`common/exceptions.py`)

```python
"""
Custom exceptions and error handlers.
"""

from rest_framework.exceptions import APIException
from rest_framework import status


class CustomAPIException(APIException):
    """Base custom API exception."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = "error"


class ResourceNotFound(CustomAPIException):
    """Resource not found exception."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "resource_not_found"


class InvalidInput(CustomAPIException):
    """Invalid input exception."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid input provided."
    default_code = "invalid_input"


class UnauthorizedAction(CustomAPIException):
    """Unauthorized action exception."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You don't have permission to perform this action."
    default_code = "unauthorized"


class ResourceConflict(CustomAPIException):
    """Resource conflict exception."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This resource conflicts with existing data."
    default_code = "conflict"


class RateLimitExceeded(CustomAPIException):
    """Rate limit exceeded exception."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded. Please try again later."
    default_code = "rate_limit_exceeded"


class ExternalServiceError(CustomAPIException):
    """External service error exception."""
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "External service error. Please try again later."
    default_code = "external_service_error"
```

### 9. Constants & Enums (`common/constants.py`)

```python
"""
Application constants and enumeration values.
"""

from enum import Enum
from django.db import models


class BaseEnum(str, Enum):
    """Base enum class for string-based enums."""
    def __str__(self):
        return self.value


class UserRole(BaseEnum):
    """User role choices."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


class NotificationStatus(BaseEnum):
    """Notification status choices."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class PaymentStatus(BaseEnum):
    """Payment status choices."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


# Application-wide constants
class AppConstants:
    """Application-wide constants."""
    
    # Pagination
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1
    
    # Token expiry times
    EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24
    PASSWORD_RESET_TOKEN_EXPIRY_HOURS = 1
    
    # Rate limiting
    API_RATE_LIMIT_ANONYMOUS = "100/hour"
    API_RATE_LIMIT_USER = "1000/hour"
    
    # File upload limits
    MAX_FILE_SIZE_MB = 10
    ALLOWED_FILE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".pdf"]
    
    # Cache timeouts (in seconds)
    CACHE_TIMEOUT_MINUTES = 5 * 60
    CACHE_TIMEOUT_HOURS = 60 * 60
    CACHE_TIMEOUT_DAYS = 24 * 60 * 60
    
    # Database
    MAX_BULK_CREATE_SIZE = 1000
```

### 10. Decorators (`common/decorators.py`)

```python
"""
Custom decorators for views and functions.
"""

from functools import wraps
from rest_framework.response import Response
from rest_framework import status


def handle_exceptions(func):
    """
    Decorator to handle exceptions in views.
    Converts exceptions to appropriate HTTP responses.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper


def require_permissions(*permissions):
    """
    Decorator to require specific permissions.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            for permission in permissions:
                if not request.user.has_perm(permission):
                    return Response(
                        {"error": "Permission denied"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def validate_input(**validators):
    """
    Decorator to validate input parameters.
    TODO: Implement validation logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # TODO: Validate kwargs against validators dict
            return func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(calls: int, period: int):
    """
    Simple rate limiting decorator.
    Args:
        calls: Number of calls allowed
        period: Time period in seconds
    TODO: Implement using cache backend
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # TODO: Implement rate limiting logic
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### 11. Admin Configuration (`common/admin.py`)

```python
"""
Common admin configurations for Django Unfold.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline, StackedInline


# TODO: Create a dashboard callback function
def dashboard_callback(request, extra_context):
    """
    Dashboard callback for custom admin dashboard.
    Implement to show statistics, recent items, etc.
    """
    extra_context["custom_stat"] = "value"
    return extra_context


class BaseModelAdmin(ModelAdmin):
    """Base admin class for all models."""
    
    # Unfold specific options
    unfold_readonly_on_create = []
    unfold_readonly_on_update = []
    
    # Common options
    list_per_page = 20
    search_help_text = "Search by name, email, etc."
    
    class Media:
        css = {
            "all": ("admin/css/base.css",)
        }
        js = ("admin/js/base.js",)
```

### 12. Celery Tasks (`accounts/tasks.py`)

```python
"""
Celery tasks for the accounts app.
"""

from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_verification_email(self, user_id: int, email: str):
    """
    Send verification email to user.
    Args:
        user_id: User ID
        email: Email address
    """
    try:
        # TODO: Implement email sending logic
        user = User.objects.get(id=user_id)
        subject = "Verify your email"
        message = f"Please verify your email by clicking: http://localhost:8000/verify/{user_id}/"
        
        send_mail(
            subject,
            message,
            "noreply@example.com",
            [email],
            fail_silently=False,
        )
        logger.info(f"Verification email sent to {email}")
    except Exception as exc:
        logger.error(f"Error sending email: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * 2 ** self.request.retries)


@shared_task
def cleanup_expired_tokens():
    """
    Clean up expired JWT tokens and verification tokens.
    Scheduled to run daily.
    """
    try:
        # TODO: Implement token cleanup logic
        logger.info("Expired tokens cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up tokens: {str(e)}")


@shared_task
def send_email_task(subject: str, message: str, recipient_list: list):
    """
    Generic task to send emails asynchronously.
    """
    try:
        send_mail(
            subject,
            message,
            "noreply@example.com",
            recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email sent to {recipient_list}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")


@shared_task
def generate_report(report_type: str, user_id: int):
    """
    Generate a report asynchronously.
    TODO: Implement report generation logic
    """
    try:
        user = User.objects.get(id=user_id)
        # TODO: Generate report based on type
        logger.info(f"Report {report_type} generated for user {user.username}")
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
```

---

## Complete Project Template

This section provides a complete, production-ready Django project structure with all configurations.

### Step 1: Create accounts/models.py

```python
"""
User and authentication models.
"""

from common.models import CustomUser
from django.db import models
from django.core.validators import URLValidator
import uuid


class UserProfile(models.Model):
    """Extended user profile information."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, max_length=500)
    website = models.URLField(blank=True, validators=[URLValidator()])
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    social_media_links = models.JSONField(default=dict, blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile of {self.user.username}"


class LoginActivity(models.Model):
    """Track user login activities."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="login_activities")
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    device_type = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Login Activity"
        verbose_name_plural = "Login Activities"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} - {self.timestamp}"
```

### Step 2: Create accounts/serializers.py

```python
"""
Serializers for user authentication and profiles.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model, authenticate
from accounts.models import UserProfile, LoginActivity
from common.serializers import BaseSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer with additional user information.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token["email"] = user.email
        token["username"] = user.username
        token["is_staff"] = user.is_staff
        return token


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "username", "password", "password_confirm", "first_name", "last_name"]

    def validate(self, data):
        """Validate password confirmation."""
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        """Create and return user instance."""
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        # TODO: Send verification email
        return user


class UserProfileSerializer(BaseSerializer):
    """Serializer for user profile."""
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "bio",
            "website",
            "location",
            "birth_date",
            "social_media_links",
            "is_public",
            "created_at",
            "updated_at",
        ]


class UserDetailSerializer(BaseSerializer):
    """Detailed user information serializer."""
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "avatar",
            "is_verified",
            "is_active",
            "profile",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LoginActivitySerializer(BaseSerializer):
    """Serializer for login activity tracking."""
    class Meta:
        model = LoginActivity
        fields = ["id", "ip_address", "user_agent", "device_type", "timestamp"]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        """Validate password confirmation."""
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        return data


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset."""
    email = serializers.EmailField()
```

### Step 3: Create accounts/viewsets.py

```python
"""
ViewSets for user authentication and management.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from accounts.models import UserProfile, LoginActivity
from accounts.serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserDetailSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
)
from common.viewsets import BaseViewSet
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token obtain view."""
    serializer_class = CustomTokenObtainPairSerializer


class UserRegistrationViewSet(viewsets.ViewSet):
    """ViewSet for user registration."""
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"])
    def register(self, request):
        """Register a new user."""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "User registered successfully. Please verify your email.",
                    "user_id": str(user.id),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(BaseViewSet):
    """ViewSet for user management."""
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["created_at", "username"]

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user profile."""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def change_password(self, request):
        """Change user password."""
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data["old_password"]):
                return Response(
                    {"error": "Old password is incorrect"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.set_password(serializer.validated_data["new_password"])
            user.save()
            return Response({"message": "Password changed successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def logout(self, request):
        """Logout user by blacklisting refresh token."""
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                # TODO: Implement token blacklisting
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"message": "Logged out successfully"})
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserProfileViewSet(BaseViewSet):
    """ViewSet for user profiles."""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter profiles based on user."""
        return UserProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get", "put"])
    def my_profile(self, request):
        """Get or update current user's profile."""
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)

        if request.method == "PUT":
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
```

### Step 4: Create accounts/urls.py

```python
"""
URL routing for accounts app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.viewsets import (
    UserViewSet,
    UserProfileViewSet,
    UserRegistrationViewSet,
    CustomTokenObtainPairView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"profiles", UserProfileViewSet, basename="profile")
router.register(r"register", UserRegistrationViewSet, basename="register")

urlpatterns = [
    path("", include(router.urls)),
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
```

### Step 5: Create pytest.ini

```ini
[pytest]
DJANGO_SETTINGS_MODULE = project.settings
python_files = tests.py test_*.py *_tests.py
addopts = --cov=. --cov-report=html --cov-report=term-missing
testpaths = tests
norecursedirs = venv .git .tox
```

### Step 6: Create tests/conftest.py

```python
"""
Pytest configuration and fixtures.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from faker import Faker

fake = Faker()
User = get_user_model()


@pytest.fixture
def api_client():
    """Fixture for API client."""
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    """Fixture for authenticated user."""
    user = User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123"
    )
    return user


@pytest.fixture
def authenticated_client(db, authenticated_user):
    """Fixture for authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=authenticated_user)
    return client


@pytest.fixture
def admin_user(db):
    """Fixture for admin user."""
    user = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass123"
    )
    return user


@pytest.fixture
def admin_client(db, admin_user):
    """Fixture for admin API client."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def sample_users(db):
    """Fixture for creating multiple test users."""
    users = []
    for _ in range(5):
        user = User.objects.create_user(
            username=fake.username(),
            email=fake.email(),
            password="testpass123"
        )
        users.append(user)
    return users
```

### Step 7: Create accounts/tests.py

```python
"""
Tests for accounts app.
"""

import pytest
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistration:
    """Tests for user registration."""
    
    def test_register_user_success(self, api_client):
        """Test successful user registration."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepass123",
            "password_confirm": "securepass123",
            "first_name": "John",
            "last_name": "Doe",
        }
        response = api_client.post(reverse("register-register"), data)
        assert response.status_code == status.HTTP_201_CREATED
        assert "user_id" in response.json()

    def test_register_user_password_mismatch(self, api_client):
        """Test registration with mismatched passwords."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepass123",
            "password_confirm": "differentpass123",
        }
        response = api_client.post(reverse("register-register"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_user_duplicate_email(self, api_client, authenticated_user):
        """Test registration with duplicate email."""
        data = {
            "username": "anotheruser",
            "email": authenticated_user.email,
            "password": "securepass123",
            "password_confirm": "securepass123",
        }
        response = api_client.post(reverse("register-register"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserAuthentication:
    """Tests for user authentication."""
    
    def test_obtain_token_success(self, api_client, authenticated_user):
        """Test successful token obtaining."""
        data = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post(reverse("token_obtain_pair"), data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.json()
        assert "refresh" in response.json()

    def test_obtain_token_invalid_credentials(self, api_client):
        """Test token obtaining with invalid credentials."""
        data = {
            "username": "nonexistent",
            "password": "wrongpass",
        }
        response = api_client.post(reverse("token_obtain_pair"), data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfile:
    """Tests for user profile."""
    
    def test_get_user_profile(self, authenticated_client):
        """Test getting user profile."""
        response = authenticated_client.get(reverse("user-me"))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["username"] == "testuser"

    def test_change_password_success(self, authenticated_client, authenticated_user):
        """Test successful password change."""
        data = {
            "old_password": "testpass123",
            "new_password": "newpass123",
            "new_password_confirm": "newpass123",
        }
        response = authenticated_client.post(reverse("user-change_password"), data)
        assert response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_old(self, authenticated_client):
        """Test password change with wrong old password."""
        data = {
            "old_password": "wrongpass",
            "new_password": "newpass123",
            "new_password_confirm": "newpass123",
        }
        response = authenticated_client.post(reverse("user-change_password"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
```

---

## Deployment Guide

### Using Gunicorn (for WSGI - REST APIs)

Gunicorn is the recommended WSGI server for traditional Django REST APIs.

#### Installation (already in requirements.txt)

```bash
pip install gunicorn==21.2.0
```

#### Run Gunicorn

```bash
# Development
gunicorn project.wsgi:application --bind 0.0.0.0:8000 --reload

# Production
gunicorn project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30 \
    --access-logfile - \
    --error-logfile -
```

#### Production Configuration (gunicorn_config.py)

```python
"""
Gunicorn configuration for production.
"""

import multiprocessing

# Server bindings
bind = ["0.0.0.0:8000"]

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"  # Use "gevent" for async
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn.pid"
umask = 0
user = None
group = None

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "project"

# Timeouts
timeout = 30
graceful_timeout = 30

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
```

### Using Uvicorn (for ASGI - WebSockets + Async)

Uvicorn is required when using Django Channels for WebSocket support.

#### Installation (already in requirements.txt)

```bash
pip install uvicorn==0.24.0
```

#### Run Uvicorn

```bash
# Development
uvicorn project.asgi:application --reload --host 0.0.0.0 --port 8000

# Production
uvicorn project.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
```

#### Production Uvicorn Configuration

```bash
uvicorn project.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --loop auto \
    --http h11 \
    --log-level info \
    --access-log
```

### Gunicorn vs Uvicorn: Which to Choose?

| Aspect | Gunicorn | Uvicorn |
|--------|----------|---------|
| **Protocol** | WSGI (HTTP only) | ASGI (HTTP + WebSocket) |
| **Use Case** | Traditional REST APIs | Real-time apps (WebSocket) |
| **Performance** | Better for CPU-bound tasks | Better for I/O-bound tasks |
| **Async Support** | Limited | Full async/await support |
| **Django Channels** | ❌ Not supported | ✅ Full support |
| **Deployment** | Traditional, stable | Modern, evolving |

**Recommendation**: Use **Gunicorn** for traditional REST APIs. Use **Uvicorn** if you need WebSocket support (Channels).

### Docker Deployment

See the `docker-compose.yml` file above for complete Docker setup with PostgreSQL, Redis, and both Gunicorn and Celery services.

#### Build and Run

```bash
# Build images
docker-compose build

# Run services
docker-compose up -d

# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Stop services
docker-compose down
```

### Nginx Configuration (Reverse Proxy)

```nginx
upstream django {
    server localhost:8000;
}

server {
    listen 80;
    server_name example.com www.example.com;
    client_max_body_size 10M;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com www.example.com;
    client_max_body_size 10M;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Static and media files
    location /static/ {
        alias /app/staticfiles/;
    }

    location /media/ {
        alias /app/media/;
    }

    # API proxy
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
}
```

### Environment-based Settings

```bash
# .env.development
DJANGO_ENVIRONMENT=local
DEBUG=True
SECRET_KEY=dev-secret-key

# .env.production
DJANGO_ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-secure-key>
ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
```

---

## Running the Project

### Initial Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Run development server
python manage.py runserver
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=.

# Generate HTML coverage report
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### Running Celery

```bash
# Start Celery worker
celery -A project worker --loglevel=info

# Start Celery beat (scheduler)
celery -A project beat --loglevel=info

# Monitor Celery
celery -A project events
```

---

## Production Checklist

- [ ] Set `DEBUG=False` in production settings
- [ ] Generate secure `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up HTTPS/SSL certificates
- [ ] Configure email backend for production
- [ ] Set up database backups
- [ ] Configure logging and monitoring
- [ ] Set up error tracking (Sentry)
- [ ] Configure rate limiting
- [ ] Test all API endpoints
- [ ] Set up CI/CD pipeline
- [ ] Configure health checks
- [ ] Document API endpoints
- [ ] Security audit

---

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/)
- [pytest-django](https://pytest-django.readthedocs.io/)

---

## License

This guide is provided as a reference for setting up Django projects. Modify according to your project requirements.

## Support & Contribution

For questions or improvements, please refer to the official documentation of each package used in this guide.

---

**Last Updated**: February 2026  
**Django Version**: 4.2+  
**Python Version**: 3.9+
