# Django Project Complete Setup Guide (2025/2026) 🚀

A comprehensive guide for setting up a production-ready Django project with the latest stable versions, modern best practices, all necessary packages, and a complete project structure template.

**Last Updated:** February 2026  
**Python Version:** 3.13  
**Django Version:** 6.0 (Latest) / 5.2 (LTS)  
**Django REST Framework:** 3.16  
**Celery:** 5.6

---

## Table of Contents

1. [Prerequisites & Installation](#prerequisites--installation)
2. [Version Overview](#version-overview)
3. [Project Architecture Overview](#project-architecture-overview)
4. [Initial Setup](#initial-setup)
5. [Package Installation & Configuration](#package-installation--configuration)
6. [Database Setup (PostgreSQL)](#database-setup-postgresql)
7. [Project Structure](#project-structure)
8. [Core Configurations](#core-configurations)
9. [Reusable Components](#reusable-components)
10. [Complete Project Template](#complete-project-template)
11. [Deployment Guide](#deployment-guide)

---

## Prerequisites & Installation

### System Requirements

- **Python:** 3.13 (or 3.12, 3.11, 3.10 minimum)
- **PostgreSQL:** 14+ (13+ minimum for Django 5.2)
- **Redis:** 7.0+ (for caching and Celery)
- **Docker & Docker Compose:** Latest
- **Git:** Latest

### Python Virtual Environment

```bash
# Create virtual environment
python3.13 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.13.x
```

---

## Version Overview

### ⚠️ Important: Django Version Choice

Django 5.2 is designated as a long-term support release. It will receive security updates for at least three years after its release. Support for Django 4.2 ends in April 2026.

**Recommendation:**
- **For New Projects:** Use Django 6.0 (latest features)
- **For Production Stability:** Use Django 5.2 LTS (3 years of support)

This guide covers both options. Choose one:

```bash
# Option 1: Latest (Django 6.0)
pip install django==6.0.2

# Option 2: LTS (Django 5.2 - Recommended for production)
pip install django==5.2.11
```

### Latest Stable Versions (Feb 2026)

| Package | Latest Stable | Min Version | Notes |
|---------|---------------|------------|-------|
| Python | 3.13 | 3.10 | 3.13 recommended |
| Django | 6.0.2 | 5.0 | 5.2 LTS available |
| Django REST Framework | 3.16.1 | 4.2 | Full Django 6.0 support |
| Celery | 5.6.2 | 5.5 | Python 3.13 support |
| Django Channels | 4.0+ | 4.0 | WebSocket support |
| PostgreSQL | 17+ | 14 | Use 15+ for production |
| Redis | 7.2+ | 7.0 | For cache & Celery |

---

## Project Architecture Overview

This guide covers building a modern Django application with:

- **REST APIs** via Django REST Framework 3.16
- **Real-time Communication** via Django Channels 4.0
- **Async Task Processing** via Celery 5.6 + Beat + Redis
- **JWT Authentication** via Django Simple JWT
- **API Documentation** via drf-spectacular
- **Testing** via pytest-django
- **Admin Interface** enhancement via django-unfold
- **Caching** via django-redis
- **Filtering & Pagination** via django-filter
- **Containerization** via Docker & Docker Compose
- **Production Server** via Gunicorn + Uvicorn
- **Type Safety** via mypy + django-stubs

---

## Initial Setup

### Step 1: Create Django Project

```bash
# Install Django
pip install django==6.0.2

# Create project
django-admin startproject project .

# Create initial apps
python manage.py startapp accounts
python manage.py startapp common
python manage.py startapp api

# Create requirements directory
mkdir requirements
```

### Step 2: Initialize Git

```bash
git init
cat > .gitignore << 'EOF'
# Virtual Environment
venv/
.venv/
ENV/
env/

# Python
*.py[cod]
__pycache__/
*.so
.Python
*.egg-info/
dist/
build/

# Django
*.log
*.pot
db.sqlite3
db.sqlite3-journal
/media/
/staticfiles/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local
.env.*.local

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db
EOF
```

---

## Package Installation & Configuration

### Step 1: Install All Packages

**Create a modular requirements structure:**

```bash
# Create base requirements file
cat > requirements/base.txt << 'EOF'
# Django LTS + REST API + Admin customization
Django==5.2                    
djangorestframework==3.16.1
django-celery-beat==2.8.0
django-celery-results==2.5.1
django-cors-headers==4.4.0
django-filter==24.3
django-redis==5.4.0
django-unfold==0.42.0          # Modern Tailwind admin theme
drf-spectacular==0.29.0        # OpenAPI/Swagger docs
djangorestframework_simplejwt==5.4.0
django-channels==0.7.0
channels==4.3.2
channels_redis==4.3.0

# Celery tasks + Redis backend + ASGI support
celery==5.6.2
kombu==5.6.0                   # Celery messaging (AMQP/Redis)
billiard==4.2.4                # Celery multiprocessing
vine==5.1.0                    # Celery promise library
redis==5.2.0                   # Cache + Celery broker
asgiref==3.11.1                # Django ASGI
anyio==4.12.1                  # Async compatibility
uvicorn==0.31.0                # ASGI server
watchfiles==1.1.1              # Hot reload
websockets==16.0               # WebSocket protocol

# PostgreSQL + Image handling + Static files
psycopg==3.2.1                 # Modern PostgreSQL adapter
pillow==11.0.0                 # Images (upgrade to 11.2.0)
whitenoise==6.8.2              # Static files in production
django-timezone-field==7.2.1   # TZ-aware DateTimeField
pytz==2024.2                   # Timezone definitions
tzdata==2025.3                 # IANA timezone DB

# Type checking + Linting + Testing
django-stubs==5.0.0            # Django mypy stubs
mypy==1.11.2                   # Static type checker
black==24.10.0                 # Code formatter
isort==5.13.2                  # Import sorter
flake8==7.1.1                  # Linter
pytest==8.3.4                  # Testing framework
pytest-django==4.7.0           # Django testing utils
coverage==7.13.4               # Test coverage
pre-commit==3.7.1              # Git hooks
factory-boy==3.3.0             # Test factories
Faker==25.9.2                  # Fake test data

# Production deployment + Config
gunicorn==23.0.0               # WSGI server
python-decouple==3.8           # .env files
python-dotenv==1.0.1           # Environment variables
PyYAML==6.0.3                  # YAML config
requests==2.32.3               # HTTP client
sqlparse==0.5.2                # SQL formatter
typing_extensions==4.15.0      # Backported type hints
sentry-sdk==2.0.0              # Monitoring

EOF

# Create development requirements
cat > requirements/development.txt << 'EOF'
-r base.txt

# Debug tools
django-debug-toolbar==4.4.2
django-extensions==3.2.3

# API Testing
httpx==0.28.1
boto3==1.35.32

EOF

# Create production requirements
cat > requirements/production.txt << 'EOF'
-r base.txt

# Production specific
whitenoise==6.8.2
django-cors-headers==4.4.0

EOF

# Install base requirements
pip install -r requirements/base.txt
```

### Step 2: Create .env Files

```bash
# Create main .env for local development
cat > .env.local << 'EOF'
# Environment
DJANGO_ENVIRONMENT=local
DEBUG=True
SECRET_KEY=django-insecure-your-dev-key-change-in-production-with-secrets

# Django Settings
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=project_db
DB_USER=project_user
DB_PASSWORD=secure_password_here
DB_HOST=localhost
DB_PORT=5432

# Redis (Cache & Celery)
REDIS_URL=redis://localhost:6379/0
CACHE_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production
JWT_ALGORITHM=HS256

# Email Configuration (Development uses console backend)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@localhost.com

# Celery
CELERY_TIMEZONE=UTC
CELERY_TASK_TRACK_STARTED=True
CELERY_TASK_TIME_LIMIT=1800

# Security (Development)
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# Logging
LOG_LEVEL=INFO

# Testing
TESTING=False
EOF

# Create production .env template
cat > .env.production << 'EOF'
# Environment
DJANGO_ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-production-secret-key-min-50-chars-random

# Django Settings
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=project_db
DB_USER=project_user
DB_PASSWORD=your-secure-database-password
DB_HOST=db.example.com
DB_PORT=5432

# Redis
REDIS_URL=redis://:password@redis.example.com:6379/0
CACHE_URL=redis://:password@redis.example.com:6379/1
CELERY_BROKER_URL=redis://:password@redis.example.com:6379/0
CELERY_RESULT_BACKEND=redis://:password@redis.example.com:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-production-secret-key-min-50-chars

# Email (Production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-production-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Security (Production)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Monitoring
SENTRY_DSN=your-sentry-dsn-url
LOG_LEVEL=WARNING
EOF

# Use local env by default
cp .env.local .env
```

### Step 3: Update requirements.txt

```bash
# Generate frozen requirements for deployment
pip freeze > requirements.txt
```

---

## Database Setup (PostgreSQL)

### Step 1: Create Docker Compose File

```yaml
# docker-compose.yml (Updated for 2025)
version: '3.10'

services:
  # PostgreSQL Database
  db:
    image: postgres:17-alpine
    container_name: project_db
    environment:
      POSTGRES_DB: ${DB_NAME:-project_db}
      POSTGRES_USER: ${DB_USER:-project_user}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-secure_password}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-project_user} -d ${DB_NAME:-project_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - project_network
    restart: unless-stopped

  # Redis for Caching and Celery
  redis:
    image: redis:7-alpine
    container_name: project_redis
    command: redis-server --appendonly yes --requirepass "${REDIS_PASSWORD:-redis_password}"
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - project_network
    restart: unless-stopped

  # Django Web Application
  web:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: project_web
    command: >
      sh -c "python manage.py migrate &&
             python manage.py createsuperuser --no-input &&
             gunicorn project.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120"
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    environment:
      - DJANGO_ENVIRONMENT=production
      - DEBUG=False
      - DB_HOST=db
      - DB_PORT=5432
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis_password}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis_password}@redis:6379/0
      - ALLOWED_HOSTS=localhost,127.0.0.1
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
    networks:
      - project_network
    restart: unless-stopped

  # Celery Worker
  celery_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: project_celery_worker
    command: celery -A project worker --loglevel=info --concurrency=4
    volumes:
      - .:/app
    environment:
      - DJANGO_ENVIRONMENT=production
      - DEBUG=False
      - DB_HOST=db
      - DB_PORT=5432
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis_password}@redis:6379/0
    depends_on:
      - db
      - redis
    networks:
      - project_network
    restart: unless-stopped

  # Celery Beat (Scheduler)
  celery_beat:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: project_celery_beat
    command: celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    environment:
      - DJANGO_ENVIRONMENT=production
      - DEBUG=False
      - DB_HOST=db
      - DB_PORT=5432
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis_password}@redis:6379/0
    depends_on:
      - db
      - redis
    networks:
      - project_network
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  static_volume:
    driver: local
  media_volume:
    driver: local

networks:
  project_network:
    driver: bridge
```

### Step 2: Create Dockerfile

```dockerfile
# docker/Dockerfile (Updated for Python 3.13 & Django 6.0)
FROM python:3.13-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 appuser

# Copy requirements
COPY requirements/base.txt .
COPY requirements/production.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r production.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Create superuser environment variables
ENV DJANGO_SUPERUSER_USERNAME=admin \
    DJANGO_SUPERUSER_EMAIL=admin@example.com \
    DJANGO_SUPERUSER_PASSWORD=admin123

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

### Step 3: Run Services with Docker

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f web

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Stop services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Step 4: Local Database Setup (Without Docker)

```bash
# Install PostgreSQL (macOS with Homebrew)
brew install postgresql@17
brew services start postgresql@17

# Install PostgreSQL (Ubuntu)
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start

# Create database and user
sudo -u postgres psql << 'EOF'
CREATE DATABASE project_db;
CREATE USER project_user WITH PASSWORD 'secure_password_here';
ALTER ROLE project_user SET client_encoding TO 'utf8';
ALTER ROLE project_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE project_user SET default_transaction_deferrable TO on;
ALTER ROLE project_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;
\q
EOF

# Install Redis (macOS)
brew install redis
brew services start redis

# Test connection
psql -h localhost -U project_user -d project_db
redis-cli ping
```

---

## Project Structure

```
project/
├── project/                      # Main project config
│   ├── __init__.py
│   ├── settings/                 # Modular settings (NEW in 2025)
│   │   ├── __init__.py
│   │   ├── base.py              # Base configuration
│   │   ├── local.py             # Local development
│   │   └── production.py         # Production settings
│   ├── asgi.py                  # ASGI for Channels
│   ├── wsgi.py                  # WSGI for Gunicorn
│   ├── urls.py                  # Main URL router
│   └── routing.py               # WebSocket routing
│
├── accounts/                     # User management
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── viewsets.py
│   ├── urls.py
│   ├── permissions.py
│   ├── tasks.py                 # Celery tasks
│   ├── tests.py
│   └── admin.py
│
├── common/                       # Shared utilities
│   ├── models.py                # Abstract models
│   ├── serializers.py           # Base serializers
│   ├── viewsets.py              # Base viewsets
│   ├── permissions.py           # Custom permissions
│   ├── helpers.py               # Utilities
│   ├── decorators.py            # Custom decorators
│   ├── pagination.py            # Pagination classes
│   ├── filters.py               # Filter classes
│   ├── exceptions.py            # Custom exceptions
│   ├── constants.py             # Constants & enums
│   ├── middleware.py            # Custom middleware
│   └── admin.py
│
├── docker/                       # Docker configuration
│   ├── Dockerfile
│   ├── .dockerignore
│   └── entrypoint.sh
│
├── tests/                        # Global test configuration
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures
│   ├── factories.py             # Test factories (factory-boy)
│   └── utils.py                 # Test utilities
│
├── static/                       # Static files
│   ├── css/
│   ├── js/
│   └── images/
│
├── media/                        # User uploads
│
├── logs/                         # Application logs
│
├── requirements/                 # Modular requirements
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── .env                          # Local env (git ignored)
├── .env.production              # Production env template
├── .gitignore
├── .pre-commit-config.yaml      # Pre-commit hooks
├── docker-compose.yml           # Docker services
├── Dockerfile                   # Alternative Dockerfile
├── manage.py
├── pytest.ini                   # pytest configuration
├── pyproject.toml               # Modern Python config
├── setup.cfg                    # Setup configuration
└── README.md
```

---

## Core Configurations

### 1. Modern Settings Structure

#### `project/settings/base.py` (Simplified for 2025)

```python
"""
Base settings for Django 6.0 project.
Uses pathlib and modern Python features.
"""

import os
from pathlib import Path
from datetime import timedelta
import logging.config

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition (Django 6.0 compatible)
INSTALLED_APPS = [
    # Unfold admin (before django.contrib.admin)
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.inlines",
    
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third-party
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
    "whitenoise.middleware.WhiteNoiseMiddleware",  # For static files
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

# Database (PostgreSQL)
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DB_NAME", "project_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
        }
    }
}

# Password validators
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static & Media files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default auto field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL = "accounts.CustomUser"

# ===========================
# REST Framework (DRF 3.16)
# ===========================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
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
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# ===========================
# JWT Configuration (5.4.0)
# ===========================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.getenv("JWT_SECRET_KEY", SECRET_KEY),
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
}

# ===========================
# Celery Configuration (5.6.2)
# ===========================
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE", "UTC")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_RESULT_EXPIRES = 3600  # 1 hour
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_HEARTBEAT = 0

# ===========================
# Redis Caching (5.4.0)
# ===========================
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("CACHE_URL", "redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        }
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ===========================
# Channels Configuration (4.0+)
# ===========================
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
            "filename": BASE_DIR / "logs" / "django.log",
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

# Create logs directory
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ===========================
# DRF Spectacular (API Docs)
# ===========================
SPECTACULAR_SETTINGS = {
    "TITLE": "Project API",
    "DESCRIPTION": "Modern Django REST API with latest technologies",
    "VERSION": "1.0.0",
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
        }
    },
}

# ===========================
# Django Unfold Admin (0.42.0)
# ===========================
UNFOLD = {
    "SITE_HEADER": "Project Admin",
    "SITE_TITLE": "Project Administration",
    "SITE_URL": "/",
    "SIDEBAR": {
        "show": True,
        "navigation": [
            {
                "title": "Authentication",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": "/admin/auth/user/",
                    },
                    {
                        "title": "Groups",
                        "icon": "group",
                        "link": "/admin/auth/group/",
                    },
                ],
            },
        ],
    },
}

# ===========================
# Security Settings
# ===========================
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
}

CSRF_FAILURE_VIEW = "common.views.csrf_failure"
```

#### `project/settings/local.py`

```python
"""Local development settings"""
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Allow all origins in development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
]

# Debug toolbar
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
INTERNAL_IPS = ["127.0.0.1"]

# Disable SSL in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Logging
import logging
logging.getLogger("django.db.backends").setLevel(logging.DEBUG)
```

#### `project/settings/production.py`

```python
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
```

### 2. Update Settings Import

Create `project/settings/__init__.py`:

```python
"""Settings loader for different environments"""
import os
from django.conf import settings

ENVIRONMENT = os.getenv("DJANGO_ENVIRONMENT", "local")

if ENVIRONMENT == "production":
    from .production import *  # noqa
else:
    from .local import *  # noqa
```

### 3. Update `manage.py`

```python
#!/usr/bin/env python
"""Django's command-line utility"""
import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Ensure it's installed and available."
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
```

### 4. Update `project/wsgi.py`

```python
"""WSGI config for Gunicorn"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
application = get_wsgi_application()
```

### 5. Create `project/asgi.py`

```python
"""ASGI config for Uvicorn/Channels"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django_asgi_app = get_asgi_application()

from project.routing import websocket_urlpatterns  # noqa

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

### 6. Create `project/routing.py`

```python
"""WebSocket routing for Channels"""
from django.urls import re_path

websocket_urlpatterns = [
    # Add your WebSocket endpoints here
    # re_path(r"ws/chat/(?P<room_name>\w+)/$", ChatConsumer.as_asgi()),
]
```

### 7. Create Modern `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "project"
version = "1.0.0"
description = "Modern Django 6.0 Project"
requires-python = ">=3.10"
license = {text = "MIT"}

[tool.django]
django-project = "project.settings"

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "project.settings"
python_files = ["tests.py", "test_*.py", "*_tests.py"]
addopts = "--cov=. --cov-report=html --cov-report=term-missing"
testpaths = ["tests"]
norecursedirs = ["venv", ".git", ".tox"]

[tool.black]
line-length = 100
target-version = ["py313"]
extend-exclude = '''
/(
  # directories
  \.git
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
skip_glob = [".venv"]
known_django = ["django"]
sections = ["FUTURE", "STDLIB", "DJANGO", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]

[tool.mypy]
python_version = "3.13"
plugins = ["mypy_django_plugin.main"]
check_untyped_defs = true
ignore_missing_imports = true

[tool.django-stubs]
django_settings_module = "project.settings"

[tool.coverage.run]
source = ["."]
omit = [
    "*/tests*",
    "*/migrations/*",
    "*/__pycache__/*",
    "*/virtualenvs/*",
    "manage.py",
    "setup.py"
]
```

---

## Reusable Components (Updated for 2025)

### 1. Abstract Models

```python
# common/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    """Custom user manager for UUID primary keys"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Email is required"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class BaseModel(models.Model):
    """Abstract base model with UUID and timestamps"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

class CustomUser(AbstractUser):
    """Custom user model with email as unique identifier"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["-created_at"]),
        ]
```

### 2. Base Serializers (Updated for DRF 3.16)

```python
# common/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from typing import Any, Dict

User = get_user_model()

class BaseSerializer(serializers.ModelSerializer):
    """Base serializer with common functionality"""
    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%dT%H:%M:%SZ")
    updated_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%dT%H:%M:%SZ")

    class Meta:
        abstract = True

class UserSerializer(BaseSerializer):
    """User serializer"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "full_name", "is_verified", "created_at"
        ]
        read_only_fields = ["id", "created_at"]

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.username
```

### 3. Base ViewSets

```python
# common/viewsets.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

class BaseViewSet(viewsets.ModelViewSet):
    """Base viewset with common CRUD operations"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    def perform_create(self, serializer):
        """Hook for custom create logic"""
        serializer.save()
    
    def perform_update(self, serializer):
        """Hook for custom update logic"""
        serializer.save()
    
    @action(detail=False, methods=["get"])
    def my_items(self, request):
        """Get items belonging to current user"""
        queryset = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
```

### 4. Updated Pagination (DRF 3.16)

```python
# common/pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    """Custom pagination class"""
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "page_size": self.page_size,
            "total_pages": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "results": data,
        })
```

### 5. Celery Tasks (5.6.2)

```python
# accounts/tasks.py
from celery import shared_task, current_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email(self, user_id: str, email: str):
    """Send verification email with retry logic"""
    try:
        user = User.objects.get(id=user_id)
        subject = "Verify your email"
        message = f"Please verify your email: http://localhost:8000/verify/{user_id}/"
        
        send_mail(
            subject,
            message,
            "noreply@example.com",
            [email],
            fail_silently=False,
        )
        logger.info(f"Verification email sent to {email}")
        return {"status": "success", "email": email}
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {"status": "error", "message": "User not found"}
    except Exception as exc:
        logger.error(f"Error sending email: {str(exc)}")
        raise self.retry(exc=exc)

@shared_task
def cleanup_expired_tokens():
    """Celery beat task to cleanup expired tokens daily"""
    logger.info("Starting token cleanup")
    # Implementation here
    logger.info("Token cleanup completed")
```

### 6. Custom Permissions

```python
# common/permissions.py
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """Owner can edit, others can only read"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user

class IsAdmin(permissions.BasePermission):
    """Only admin users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff
```

### 7. Custom Middleware

```python
# common/middleware.py
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all HTTP requests"""
    def process_request(self, request):
        logger.info(f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}")
        return None

class APIVersionHeaderMiddleware(MiddlewareMixin):
    """Add API version header to responses"""
    def process_response(self, request, response):
        response["X-API-Version"] = "1.0.0"
        return response
```

---

## Complete Project Template (Updated Accounts App)

### `accounts/models.py`

```python
"""User and authentication models"""
from common.models import BaseModel, CustomUser
from django.db import models
import uuid

class UserProfile(BaseModel):
    """Extended user profile"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, max_length=500)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile of {self.user.username}"
```

### `accounts/serializers.py`

```python
"""User serializers for DRF 3.16"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model, authenticate
from accounts.models import UserProfile
from common.serializers import BaseSerializer

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer with additional claims"""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["username"] = user.username
        return token

class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "username", "password", "password_confirm", "first_name", "last_name"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class UserDetailSerializer(BaseSerializer):
    """Detailed user information"""
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_verified", "created_at"]
        read_only_fields = ["id", "created_at"]
```

### `accounts/viewsets.py`

```python
"""User viewsets for Django REST Framework 3.16"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from accounts.serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserDetailSerializer,
)
from common.viewsets import BaseViewSet

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view"""
    serializer_class = CustomTokenObtainPairSerializer

class UserViewSet(BaseViewSet):
    """User management viewset"""
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["username", "email", "first_name"]
    ordering_fields = ["created_at", "username"]

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def register(self, request):
        """Register new user"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"message": "User registered successfully"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### `accounts/urls.py`

```python
"""Account URLs"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.viewsets import UserViewSet, CustomTokenObtainPairView

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
```

---

## Deployment Guide (Updated for 2025)

### Using Gunicorn (REST APIs)

```bash
# Production configuration
gunicorn project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

### Using Uvicorn (WebSockets + Async)

```bash
# For Django Channels support
uvicorn project.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop auto
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d
docker-compose logs -f web

# Migrations
docker-compose exec web python manage.py migrate
```

### Nginx Configuration (Reverse Proxy)

```nginx
upstream django {
    server localhost:8000;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location /static/ {
        alias /app/staticfiles/;
    }
    
    location /media/ {
        alias /app/media/;
    }
    
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Running the Project (2025)

### Initial Setup

```bash
# Create environment
python3.13 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements/base.txt

# Setup environment
cp .env.local .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static
python manage.py collectstatic

# Run server
python manage.py runserver
```

### Running Tests

```bash
# All tests with coverage
pytest

# Specific test file
pytest accounts/tests.py

# With coverage report
pytest --cov=. --cov-report=html
```

### Running Celery

```bash
# Worker
celery -A project worker --loglevel=info

# Beat scheduler
celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## Production Checklist ✅

- [ ] Set `DEBUG=False` in production
- [ ] Generate secure `SECRET_KEY` (min 50 chars)
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Setup HTTPS/SSL certificates
- [ ] Configure email backend
- [ ] Setup database backups
- [ ] Configure error tracking (Sentry)
- [ ] Test all API endpoints
- [ ] Setup monitoring & logging
- [ ] Configure rate limiting
- [ ] Run security checks: `python manage.py check --deploy`
- [ ] Update dependencies regularly
- [ ] Setup CI/CD pipeline

---

## Key Changes from Previous Versions (2024→2025)

| Change | 2024 | 2025 |
|--------|------|------|
| Django | 4.2 | 6.0 / 5.2 LTS |
| Python | 3.9+ | 3.10+ (3.13 recommended) |
| DRF | 3.14 | 3.16 |
| Celery | 5.3 | 5.6 |
| PostgreSQL | 12+ | 14+ |
| Channels | 3.x | 4.0+ |
| JWT | 5.2 | 5.4 |
| Settings | monolithic | modular (settings/) |
| Requirements | single file | modular (requirements/) |
| Python Config | setup.py | pyproject.toml |

---

## Resources

- Django 6.0 is the latest official version
- [Django Documentation](https://docs.djangoproject.com/en/6.0/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- Celery 5.6 includes official support for Python 3.13
- [PostgreSQL 17 Documentation](https://www.postgresql.org/docs/17/)
- [Docker Documentation](https://docs.docker.com/)

---

**Last Updated:** February 25, 2026  
**Status:** Production Ready ✅
