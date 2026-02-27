# Django 6.0 Production-Ready Project Template

**A modern Django starter with REST APIs, async tasks, and Docker containerization**

*Updated for February 2026 • Django 6.0.2 • Python 3.13 • PostgreSQL 17*

---

## Table of Contents

- [Django 6.0 Production-Ready Project Template](#django-60-production-ready-project-template)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Tech Stack](#tech-stack)
  - [Quick Start](#quick-start)
    - [Docker Setup (Recommended)](#docker-setup-recommended)
    - [Local Setup](#local-setup)
  - [Project Structure](#project-structure)
  - [Environment Configuration](#environment-configuration)
    - [Environment Files](#environment-files)
    - [Settings Loading Order](#settings-loading-order)
  - [Development](#development)
    - [Common Commands](#common-commands)
    - [Makefile Commands](#makefile-commands)
  - [Production Deployment](#production-deployment)
    - [Using Docker Compose](#using-docker-compose)
    - [Manual Deployment](#manual-deployment)
  - [Testing](#testing)
  - [Security Checklist](#security-checklist)

---

## Overview

This template provides a production-ready Django 6.0 foundation with:

- REST API support (DRF 3.16)
- JWT authentication
- WebSocket support (Channels 4.1)
- Async task processing (Celery 5.6)
- Modern admin interface (Unfold 0.42)
- Docker containerization
- Environment-based settings
- Testing with pytest
- Type checking with mypy

---

## Tech Stack

| Component | Version |
|-----------|---------|
| Python | 3.13 |
| Django | 6.0.2 |
| Django REST Framework | 3.16.1 |
| Django Channels | 4.1 |
| Celery | 5.6.2 |
| PostgreSQL | 17 |
| Redis | 7 |
| Docker | 24.0+ |

---

## Quick Start

### Docker Setup (Recommended)

```bash
# Clone and setup
git clone <repository-url>
cd project
cp .env.example .env

# Start services
docker-compose up -d

# Access:
# - Application: http://localhost:8000
# - Admin: http://localhost:8000/admin
# - API Docs: http://localhost:8000/api/docs/
# - Flower: http://localhost:5555
```

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set DB_HOST=localhost

# Run database migrations
python manage.py migrate

# Start development server
python manage.py runserver

# Start Celery worker (in separate terminal)
celery -A project worker --loglevel=info
```

---

## Project Structure

```
project/
├── project/                    # Main Django project
│   ├── settings/               # Modular settings
│   │   ├── __init__.py         # Environment-aware loader
│   │   ├── unfold_config.py    # Unfold config for styles and such
│   │   ├── base.py             # Base settings
│   │   ├── local.py            # Local overrides
│   │   ├── production.py       # Production overrides
│   │   └── components/          # Component-specific settings
│   ├── urls.py                  # Main URL routing
│   ├── routing.py                  # Channels routing
│   ├── asgi.py                   # ASGI entry point
│   └── wsgi.py                    # WSGI entry point
│
├── dashboard/                    # Unfold custom admin dashboard
├── accounts/                      # User management app
├── common/                         # Shared utilities (helpers, base classes, error handling)
│
├── tests/                             # Test suite
├── guides/                             
├── static/                             # Static files
├── media/                               # User uploads
├── logs/                                 # Application logs
│
├── .env.example                          # Environment template
├── .gitignore                             # Git ignore rules
├── .dockerignore                           # Docker ignore rules
├── requirements.txt                         # Python dependencies
├── pyproject.toml                            # Project configuration
├── manage.py                                   # Django CLI
│── Dockerfile
│── nginx.conf
│── docker-compose.yml
└── README.md                                      # This file
```

---

## Environment Configuration

### Environment Files

| File | Purpose | Git |
|------|---------|-----|
| `.env.example` | Template with safe defaults | ✅ Committed |
| `.env` | Base configuration | ❌ Ignored |
| `.env.local` | Local development overrides | ❌ Ignored |
| `.env.production` | Production secrets | ❌ Ignored |

### Settings Loading Order

1. `DJANGO_ENVIRONMENT` determines environment (default: 'local')
2. `.env` is loaded (base configuration)
3. Environment-specific file is loaded (`.env.local` or `.env.production`)
4. Environment-specific Python file is imported (`local.py` or `production.py`)

---

## Development

### Common Commands

```bash
# Database
python manage.py makemigrations
python manage.py migrate

# User
python manage.py createsuperuser

# Server
python manage.py runserver

# Celery
celery -A project worker --loglevel=info
celery -A project beat --loglevel=info
celery -A project flower --port=5555

# Testing
pytest
pytest --cov=. --cov-report=html

# Code Quality
black .
isort .
flake8
mypy .
```

### Makefile Commands

```bash
make dev          # Setup development environment
make run          # Start development server
make migrate      # Run migrations
make test         # Run tests
make lint         # Run linters
make format       # Format code
make type-check   # Run type checker
make docker-up    # Start Docker services
make docker-down  # Stop Docker services
```

---

## Production Deployment

### Using Docker Compose

```bash
# On production server
cd docker
docker-compose up -d

# Services started:
# - web (Gunicorn) - port 8000
# - nginx - ports 80/443
# - db - PostgreSQL
# - redis - Redis
# - celery_worker - Celery worker
# - celery_beat - Celery beat
# - flower - Celery monitoring (port 5555)
```

### Manual Deployment

```bash
# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Start Gunicorn
gunicorn project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --max-requests 1000 \
    --timeout 120
```

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

---

## Security Checklist

Before deploying to production:

- [ ] `DEBUG=False` in production
- [ ] `SECRET_KEY` is a long random string
- [ ] `ALLOWED_HOSTS` contains your domain names
- [ ] HTTPS is enabled with valid SSL certificates
- [ ] `SECURE_SSL_REDIRECT=True`
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] Database passwords are strong and unique
- [ ] Redis has a strong password set
- [ ] Run `python manage.py check --deploy`

---

**Last Updated**: February 27, 2026  
**Django Version**: 6.0.2  
**Python Version**: 3.13  
**Status**: Production Ready
