# Django Project Quick Start Guide

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Docker & Docker Compose (optional but recommended)
- Git

---

## 🚀 Quick Start (With Docker - Recommended)

### Step 1: Clone/Create Project

```bash
# If you're using this as a template, create new project
mkdir my-django-project
cd my-django-project
```

### Step 2: Copy Files

Copy all the files from the output (Dockerfile, docker-compose.yml, requirements.txt, etc.) into your project directory.

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your values (for local development, defaults are fine)
nano .env
```

### Step 4: Start Services

```bash
# Build and start all services
docker-compose up -d

# Watch logs
docker-compose logs -f web

# Wait for migrations to complete (you'll see "Server is running" message)
```

### Step 5: Access Services

- **Django API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin (username: admin, password: admin123)
- **API Docs**: http://localhost:8000/api/docs/
- **Flower (Celery Monitoring)**: http://localhost:5555
- **Redis Commander** (optional): http://localhost:8081

---

## 🖥️ Quick Start (Local Development - No Docker)

### Step 1: Create Virtual Environment

```bash
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Setup PostgreSQL

```bash
# Create database and user
createdb project_db
createuser project_user

# Set password
psql -U postgres
ALTER USER project_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;
\q
```

### Step 4: Configure Environment

```bash
cp .env.example .env

# Edit .env and set:
# DJANGO_ENVIRONMENT=local
# DEBUG=True
# DB_HOST=localhost
```

### Step 5: Run Migrations

```bash
python manage.py migrate
```

### Step 6: Create Superuser

```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

### Step 7: Run Server

```bash
# Terminal 1: Django development server
python manage.py runserver

# Terminal 2: Celery worker
celery -A project worker --loglevel=info

# Terminal 3: Celery beat (optional)
celery -A project beat --loglevel=info
```

### Step 8: Access Application

- **API**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/api/docs/

---

## 📁 Project Structure

```
project/
├── project/                 # Django project settings
│   ├── settings/           # Modular settings (base, local, production)
│   ├── wsgi.py             # WSGI server entry point
│   ├── asgi.py             # ASGI server entry point (for Channels)
│   ├── urls.py             # Main URL router
│   └── routing.py          # WebSocket routing
│
├── accounts/               # User management app
│   ├── models.py          # User-related models
│   ├── serializers.py     # DRF serializers
│   ├── viewsets.py        # API viewsets
│   ├── urls.py            # App-specific URLs
│   └── tests.py           # Tests
│
├── common/                # Shared utilities
│   ├── models.py          # Base models and mixins
│   ├── serializers.py     # Base serializers
│   ├── viewsets.py        # Base viewsets
│   ├── permissions.py     # Custom permissions
│   ├── pagination.py      # Pagination classes
│   ├── filters.py         # Filter classes
│   ├── helpers.py         # Helper functions
│   ├── decorators.py      # Custom decorators
│   ├── exceptions.py      # Custom exceptions
│   └── constants.py       # Constants and enums
│
├── api/                   # Main API app
│   └── v1/               # API version
│
├── tests/                # Test configuration
│   ├── conftest.py       # pytest fixtures
│   └── factories.py      # Test data factories
│
├── docker/               # Docker configuration
│   ├── Dockerfile
│   └── nginx.conf
│
├── .env.example         # Environment variables template
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Docker services definition
├── Dockerfile          # Container image definition
├── manage.py           # Django CLI
└── pytest.ini          # pytest configuration
```

---

## 📚 Common Commands

### Django

```bash
# Create new app
python manage.py startapp app_name

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Collect static files
python manage.py collectstatic --noinput

# Run shell
python manage.py shell

# Create fixture
python manage.py dumpdata > fixture.json
```

### Celery

```bash
# Start worker
celery -A project worker --loglevel=info

# Start beat (scheduler)
celery -A project beat --loglevel=info

# Start Flower (monitoring)
celery -A project flower

# Purge tasks
celery -A project purge
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov

# Run with verbose output
pytest -v

# Run specific test class
pytest tests/test_api.py::TestUserRegistration

# Run specific test method
pytest tests/test_api.py::TestUserRegistration::test_register_user_success
```

### Database

```bash
# Reset database (WARNING: Deletes all data)
python manage.py flush

# Create database backup
pg_dump project_db > backup.sql

# Restore from backup
psql project_db < backup.sql

# Interactive database shell
python manage.py dbshell
```

### Docker

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Execute command in container
docker-compose exec web python manage.py migrate

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: Deletes data)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# View running containers
docker-compose ps
```

---

## 🔧 Configuration Guide

### Settings Management

Settings are split into modular files in `project/settings/`:

- **base.py**: Shared configuration
- **local.py**: Development settings (DEBUG=True)
- **production.py**: Production settings (DEBUG=False, security)

Switch environment via `DJANGO_ENVIRONMENT` variable:

```bash
export DJANGO_ENVIRONMENT=production  # or "local"
```

### Environment Variables

Key variables in `.env`:

```bash
# Django
DJANGO_ENVIRONMENT=local
DEBUG=True
SECRET_KEY=change-in-production

# Database
DB_HOST=localhost
DB_NAME=project_db
DB_USER=project_user
DB_PASSWORD=secure_password_here

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Celery Tasks

Define tasks in `app_name/tasks.py`:

```python
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def my_task(self, arg1, arg2):
    try:
        # TODO: Implement task logic
        logger.info(f"Processing: {arg1}, {arg2}")
        return f"Result: {arg1} + {arg2}"
    except Exception as exc:
        logger.error(f"Error: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)
```

Call task:

```python
from accounts.tasks import my_task

# Run asynchronously
my_task.delay("value1", "value2")

# Run with delay
my_task.apply_async(("value1", "value2"), countdown=10)

# Run synchronously (for testing)
my_task("value1", "value2")
```

---

## 🧪 Testing Guide

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_api.py

# Specific test
pytest tests/test_api.py::TestUserRegistration::test_register_user_success

# With coverage
pytest --cov=.

# Coverage report
pytest --cov=. --cov-report=html
# Open htmlcov/index.html
```

### Writing Tests

```python
import pytest
from rest_framework import status
from django.urls import reverse

@pytest.mark.django_db
class TestUserAPI:
    """Test user API endpoints."""
    
    def test_user_registration(self, api_client):
        """Test user registration."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
        }
        response = api_client.post(reverse("register-register"), data)
        assert response.status_code == status.HTTP_201_CREATED
```

---

## 🚢 Deployment Checklist

Before deploying to production:

- [ ] Set `DEBUG=False`
- [ ] Generate secure `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up PostgreSQL database
- [ ] Configure email backend
- [ ] Set up Redis
- [ ] Configure SSL/HTTPS
- [ ] Set up backups
- [ ] Configure monitoring/logging
- [ ] Run full test suite
- [ ] Load test the application
- [ ] Security audit
- [ ] Document API endpoints

---

## 🐛 Troubleshooting

### Common Issues

**Port already in use**

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

**Database connection error**

```bash
# Check PostgreSQL is running
pg_isready

# Check connection
psql -U project_user -d project_db -h localhost
```

**Redis connection error**

```bash
# Check Redis is running
redis-cli ping

# Connect to Redis
redis-cli
```

**Celery tasks not running**

```bash
# Check Celery worker logs
celery -A project worker --loglevel=debug

# Check Redis
redis-cli
KEYS *  # Should see celery tasks

# Purge failed tasks
celery -A project purge
```

**Static files not loading**

```bash
# Collect static files
python manage.py collectstatic --noinput

# Check static files directory
ls -la staticfiles/
```

---

## 📖 Documentation Links

- [Django Docs](https://docs.djangoproject.com/)
- [DRF Docs](https://www.django-rest-framework.org/)
- [Celery Docs](https://docs.celeryproject.org/)
- [Channels Docs](https://channels.readthedocs.io/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Redis Docs](https://redis.io/documentation)
- [Docker Docs](https://docs.docker.com/)

---

## 🤝 Need Help?

1. Check logs: `docker-compose logs -f web`
2. Check Django logs in `project/logs/`
3. Review the comprehensive guide: `DJANGO_COMPLETE_SETUP_GUIDE.md`
4. Check official documentation links above

---

**Last Updated**: February 2026  
**Django Version**: 4.2+  
**Python Version**: 3.9+
