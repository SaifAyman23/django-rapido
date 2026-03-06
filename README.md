# Django Rapido V1.0

**A modern, scalable, and production-ready Django project template.**

*Updated for Django 5.2+ • Python 3.13 • PostgreSQL 17*

---

## Table of Contents

- [Django Rapido V1.0](#django-rapido-v10)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
    - [Option 1: Using Docker (Recommended)](#option-1-using-docker-recommended)
    - [Option 2: Local Setup](#option-2-local-setup)
  - [Project Structure](#project-structure)
  - [Environment Configuration](#environment-configuration)
  - [Development Guide](#development-guide)
    - [Common Commands](#common-commands)
    - [Code Quality \& Formatting](#code-quality--formatting)
  - [Celery \& Background Tasks](#celery--background-tasks)
  - [Production Deployment](#production-deployment)
    - [Using Docker Compose (Recommended)](#using-docker-compose-recommended)
    - [Manual Deployment](#manual-deployment)
  - [Testing](#testing)
  - [Security Checklist](#security-checklist)

---

## Features

- **Core Framework**: Django 5.2+ & Python 3.13
- **API**: Django REST Framework (DRF) 3.16 with JWT Authentication (SimpleJWT)
- **Real-time**: WebSocket support via Django Channels 4.1 & Redis
- **Background Tasks**: Celery 5.6 for async workers, Celery Beat for cron, and Flower for monitoring
- **Database**: PostgreSQL 17 integration out of the box
- **Admin**: Beautiful, modern UI with Django Unfold
- **DevOps**: Complete Docker containerization (`Dockerfile`, `docker-compose.yml`, `entrypoint.sh`)
- **Web Server**: Nginx configured as a reverse proxy serving static and media files securely
- **Settings**: Modular, environment-based configuration for clean separation of concerns
- **Code Quality**: Pre-configured with Black, isort, Flake8, Mypy, and Pytest
- **Frontend Assets**: Tailwind CSS integration configured via `package.json`

---

## Prerequisites

Before beginning, ensure the following are installed:

- **Python**: 3.13+ (for local, non-Docker development)
- **Node.js**: Required to install frontend assets like Tailwind CSS dependencies
- **Docker & Docker Compose**: (Optional, but highly recommended)
- **PostgreSQL & Redis**: If running locally without Docker

---

## Quick Start

The fastest way to get started is by using the streamlined `Makefile` commands to bootstrap the environment automatically.

### Option 1: Using Docker (Recommended)

Docker Compose provides a seamless development sandbox containing the Web app, PostgreSQL, Redis, Celery, and Flower.

```bash
# 1. Clone the repository
git clone <repository-url> my-project
cd my-project

# 2. Copy the environment variables template
cp .env.example .env

# 3. Start all services in the background
make docker-up

# 4. View logs (if needed)
make docker-logs
```

**Access URLs:**
- Application: `http://localhost:8000`
- Admin Panel: `http://localhost:8000/admin`
- API Docs: `http://localhost:8000/api/docs/`
- Flower (Celery Dashboard): `http://localhost:5555`

### Option 2: Local Setup

If running services directly on the host machine is preferred:

```bash
# 1. Clone the repository
git clone <repository-url> my-project
cd my-project

# 2. Ensure PostgreSQL and Redis are running locally.
# Update the generated .env file to point DB_HOST and REDIS_HOST to 'localhost'.

# 3. Initialize the project
# This command automatically:
# - Installs Python & Node.js dependencies
# - Creates .env from .env.example
# - Generates a secure SECRET_KEY
# - Runs database migrations
# - Collects static files
# - Creates a superuser (admin/admin123)
make init

# 4. Start the Django development server
make run
```

---

## Project Structure

```text
project-root/
├── project/                    # Main Django project directory
│   ├── settings/               # Modular settings configuration
│   │   ├── __init__.py         # Environment-aware settings loader
│   │   ├── base.py             # Core settings shared across environments
│   │   ├── local.py            # Development-specific overrides
│   │   ├── production.py       # Production-specific overrides
│   │   ├── testing.py          # Fast, isolated test-specific settings
│   │   └── components/         # Feature-specific modules (db.py, celery.py, apps.py, etc.)
│   ├── urls.py                 # Root URL routing
│   ├── asgi.py                 # ASGI entry point (for WebSockets/Channels)
│   └── wsgi.py                 # WSGI entry point (for Gunicorn)
│
├── accounts/                   # Custom User model and authentication
├── common/                     # Utility helpers, base models, custom exceptions
├── dashboard/                  # Custom Django Unfold admin adjustments
├── tests/                      # Pytest suite structure
├── guides/                     # Extensive architectural documentation
│
├── docker-compose.yml          # Container orchestration for dev & prod
├── Dockerfile                  # Production-ready Python image
├── entrypoint.sh               # Smart container initialization script (handles migrations, static files, and waits for DB)
├── nginx.conf                  # Nginx reverse proxy configuration for port 80 routing and serving static/media
│
├── static/                     # Global static files
├── media/                      # User-uploaded files
├── logs/                       # Application logs directory
│
├── Makefile                    # Task automation commands
├── requirements.txt            # Python dependencies
├── package.json                # Node.js dependencies
└── .env.example                # Baseline environment configuration
```

---

## Environment Configuration

Configuration is managed securely, primarily utilizing environment variables. Settings logic dictates which file is loaded depending on the stated `DJANGO_ENVIRONMENT`:

1. `DJANGO_ENVIRONMENT=local` (Default): Loads `settings/local.py` + `base.py`. Features `DEBUG=True`.
2. `DJANGO_ENVIRONMENT=production`: Loads `settings/production.py`. Enforces strict security configurations like HTTPS and `DEBUG=False`.
3. `DJANGO_ENVIRONMENT=testing`: Loads `settings/testing.py`. Uses an in-memory SQLite DB for lightning-fast speeds and disables explicit Celery delays.

**Note:** Never commit the populated `.env` file to version control.

---

## Development Guide

### Common Commands

A robust `Makefile` is provided to simplify common development operations.

| Command | Description |
|---------|-------------|
| `make init` | **(Important)** Fully initialize the project setup. |
| `make install` | Install Python (`requirements.txt`) and Node (`package.json`) dependencies. |
| `make run` | Starts the local Django development server. |
| `make migrate` | Applies pending database migrations. |
| `make makemigrations`| Scans models to yield new migration schema files. |
| `make shell` | Bootstraps a Django interactive shell. |
| `make dev` | Ensures dependencies map directly to a booted local development suite. |
| `make clean` | Wipes caching, compiled Python code (`__pycache__`), bytecodes. |

### Code Quality & Formatting

To ensure consistent project readability:

```bash
# Code formatters (Black & isort)
make format

# Linter checks (Flake8)
make lint

# Static type checking (Mypy)
make type-check
```

---

## Celery & Background Tasks

The project seamlessly handles heavy async computational tasks via **Celery**.

**To run Celery locally without Docker:**
1. Ensure Redis is available (`redis-server`).
2. Boot a Celery Worker daemon:
   ```bash
   make celery-worker
   ```
3. Boot the Celery Beat daemon for recurring cron tasks:
   ```bash
   make celery-beat
   ```

*(Using Docker Compose implicitly provides these background daemons alongside a `Flower` UI tracker.)*

---

## Production Deployment

We use a multi-service container approach orchestrated by `docker-compose.yml` and managed by a smart `entrypoint.sh` script.

**Container Roles (`docker-compose.yml`):**
1. **web:** Runs the Django application via Gunicorn.
2. **nginx:** Acts as a reverse proxy, fielding requests on port 80/443 and routing to the `web` container, while efficiently serving static and media files directly.
3. **db:** PostgreSQL database server.
4. **redis:** In-memory store used for caching and Celery message brokering.
5. **celery_worker, celery_beat, flower:** Background asynchronous processing and cron job management.

**Smart Entrypoint (`entrypoint.sh`):**
The `entrypoint.sh` script automatically:
- Waits for the database and Redis to boot before launching Django.
- Collects static files if the container role is `web`.
- Runs database migrations seamlessly.
- (Local Only) Creates a superuser based on `.env`.

### Using Docker Compose (Recommended)

1. Check out the source matrix onto the production box.
2. Initialize and secure the `.env`:
   - Set `DJANGO_ENVIRONMENT=production`.
   - Ensure `DEBUG=False`.
   - Define exact URLs inside `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`.
   - Replace variables like `REDIS_PASSWORD` and `DB_PASSWORD` with extremely strong values.
   - Run `make secret-key` locally to spawn a secure hash and patch it into `SECRET_KEY`.
3. Read the `docker-compose.yml` inline comments inside the **PRODUCTION block**:
   - Swap the `web` container `command` to boot via `gunicorn`.
   - Update `nginx` port mappings to route `443:443` HTTPS connections and mount an `ssl/` certificate volume.
4. Compose and deploy:
   ```bash
   make docker-build
   make docker-up
   ```
5. Your application will now be securely available via Nginx acting as a reverse proxy. Nginx will directly serve the `/static/` and `/media/` endpoints without hitting Gunicorn cache.

### Manual Deployment

If opting to deploy conventionally via Systemd + Gunicorn daemonized background process instead of Docker:

```bash
# 1. Gather static files payload
python manage.py collectstatic --noinput

# 2. Push database schema migrations
python manage.py migrate

# 3. Spin up Gunicorn bound securely
gunicorn project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --max-requests 1000 \
    --timeout 120
```

---

## Testing

The project uses `pytest` combined with `pytest-django`. The test settings drastically optimize runtimes via in-core SQLite logic bridging:

```bash
# Run the core validation test suite
make test

# To run specifically against coverage tooling
make test-coverage

# Execute with debug fail-fast mode
make test-fast
```

---

## Security Checklist

When publishing Django code onto a live server, strictly confirm the baseline markers below:

- [ ] `DEBUG=False` must be toggled within `.env`.
- [ ] Ensure `DJANGO_ENVIRONMENT=production`.
- [ ] Run `make secret-key` to configure a massive randomized hash inside `SECRET_KEY`.
- [ ] Ensure the domain namespace is exactly configured within `ALLOWED_HOSTS`.
- [ ] Securely update unassigned generic keys (e.g. `DB_PASSWORD`, `REDIS_PASSWORD`, Unfold Dashboard users, Flower tracking users).
- [ ] Set `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, and `CSRF_COOKIE_SECURE=True` to encrypt packets.
- [ ] Run `python manage.py check --deploy` iteratively ensuring all red flags vanish.

---
**Django Rapido V1.0** — Build faster, scale beautifully.
