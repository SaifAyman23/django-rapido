# Django Project Quick Start Guide (Feb 2026)

Updated for Django 6.0, Python 3.13, DRF 3.16, Celery 5.6, PostgreSQL 17

## 📋 Prerequisites

- Python 3.13 (or 3.10+ minimum)
- PostgreSQL 14+ (17 recommended)
- Docker & Docker Compose (optional but recommended)
- Redis 7+
- Git

---

## 🚀 Quick Start (With Docker - Recommended)

### Step 1: Clone/Create Project

```bash
mkdir my-django-project
cd my-django-project
```

### Step 2: Copy Files

Copy all the files (Dockerfile, docker-compose.yml, requirements.txt, etc.) into your project directory.

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your values (defaults are fine for local development)
nano .env
```

### Step 4: Start Services

```bash
# Build and start all services
docker-compose up -d

# Watch logs
docker-compose logs -f web

# Wait for "Successfully created superuser" message
```

### Step 5: Access Services

- **Django API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin (admin / admin123)
- **API Docs (Swagger)**: http://localhost:8000/api/docs/
- **API Docs (ReDoc)**: http://localhost:8000/api/redoc/
- **Flower (Celery Monitoring)**: http://localhost:5555
- **API Schema**: http://localhost:8000/api/schema/

### Useful Docker Commands

```bash
# View logs
docker-compose logs -f web

# Run Django command in container
docker-compose exec web python manage.py createsuperuser

# Run migrations
docker-compose exec web python manage.py migrate

# Open shell in container
docker-compose exec web /bin/bash

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

---

## 💻 Quick Start (Local Development - No Docker)

### Step 1: Create Virtual Environment

```bash
python3.13 -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Verify Python version
python --version  # Should show Python 3.13.x
```

### Step 2: Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 3: Setup PostgreSQL

```bash
# macOS
brew install postgresql@17
brew services start postgresql@17

# Ubuntu
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql

# Create database and user
createdb project_db
createuser project_user

# Set password and permissions
psql postgres
ALTER USER project_user WITH PASSWORD 'secure_password_here';
ALTER ROLE project_user SET client_encoding TO 'utf8';
ALTER ROLE project_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE project_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;
\q
```

### Step 4: Setup Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis-server

# Test connection
redis-cli ping  # Should return PONG
```

### Step 5: Configure Environment

```bash
cp .env.example .env

# Edit .env and set:
DJANGO_ENVIRONMENT=local
DEBUG=True
DB_HOST=localhost
REDIS_URL=redis://localhost:6379/0
```

### Step 6: Run Migrations

```bash
python manage.py migrate
```

### Step 7: Create Superuser

```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

### Step 8: Run Development Servers

**Terminal 1: Django server**

```bash
python manage.py runserver
```

**Terminal 2: Celery worker**

```bash
celery -A project worker --loglevel=info --concurrency=4
```

**Terminal 3: Celery beat (optional)**

```bash
celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Terminal 4: Flower monitoring (optional)**

```bash
celery -A project flower --port=5555
```

### Step 9: Access Application

- **API**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/api/docs/
- **Flower**: http://localhost:5555

---

## 📁 Project Structure

```
project/
├── project/                 # Django project settings
│   ├── settings/           # Modular settings
│   │   ├── __init__.py
│   │   ├── base.py         # Base configuration
│   │   ├── local.py        # Local development
│   │   └── production.py    # Production settings
│   ├── wsgi.py             # WSGI entry point (Gunicorn)
│   ├── asgi.py             # ASGI entry point (Uvicorn/Channels)
│   ├── urls.py             # Main URL router
│   └── routing.py          # WebSocket routing
│
├── accounts/               # User management app
│   ├── models.py          # User-related models
│   ├── serializers.py     # DRF serializers
│   ├── viewsets.py        # API viewsets
│   ├── urls.py            # App-specific URLs
│   ├── tasks.py           # Celery tasks
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
├── tests/                # Test configuration
│   ├── conftest.py       # pytest fixtures
│   └── factories.py      # Test factories
│
├── docker/               # Docker configuration
│   ├── Dockerfile
│   └── nginx.conf
│
├── requirements/         # Modular requirements
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── .env.example         # Environment variables template
├── .gitignore           # Git ignore rules
├── .dockerignore        # Docker ignore rules
├── requirements.txt     # All dependencies
├── docker-compose.yml   # Docker services
├── Dockerfile          # Container image
├── Makefile            # Development commands
├── pytest.ini          # pytest configuration
├── manage.py           # Django CLI
└── README.md           # Project documentation
```

---

## 📚 Common Commands

### Django Commands

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

# Open Django shell
python manage.py shell

# Database shell
python manage.py dbshell

# System check
python manage.py check --deploy
```

### Celery Commands

```bash
# Start worker
celery -A project worker --loglevel=info

# Start beat scheduler
celery -A project beat --loglevel=info

# Start Flower monitoring
celery -A project flower

# Purge all tasks
celery -A project purge

# Inspect active tasks
celery -A project inspect active
```

### Testing Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov

# Run specific test class
pytest tests/test_api.py::TestUserRegistration

# Run with verbose output
pytest -v

# Run with print statements visible
pytest -s

# Generate HTML coverage report
pytest --cov=. --cov-report=html
# Open htmlcov/index.html
```

### Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Execute command
docker-compose exec web python manage.py migrate

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache

# View running containers
docker-compose ps
```

### Using Makefile

```bash
make help              # Show all commands
make install           # Install dependencies
make run               # Run development server
make test              # Run tests
make test-coverage     # Tests with coverage
make celery-worker     # Start Celery worker
make celery-beat       # Start Celery beat
make flower            # Start Flower
make lint              # Run code linting
make format            # Format code
make docker-up         # Start Docker services
make docker-down       # Stop Docker services
make clean             # Clean Python cache
```

---

## 🔧 Configuration Guide

### Settings Management

Settings are modular and located in `project/settings/`:

- **base.py**: Shared configuration
- **local.py**: Development settings (DEBUG=True)
- **production.py**: Production settings (DEBUG=False, security hardening)

Switch environments via `DJANGO_ENVIRONMENT` variable:

```bash
# Local development
export DJANGO_ENVIRONMENT=local

# Production
export DJANGO_ENVIRONMENT=production
```

### Key Environment Variables

```bash
# Django
DJANGO_ENVIRONMENT=local
DEBUG=True
SECRET_KEY=your-secret-key

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

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def my_async_task(self, arg1, arg2):
    """Example Celery task"""
    try:
        logger.info(f"Processing: {arg1}, {arg2}")
        # TODO: Implement task logic
        return f"Result: {arg1} + {arg2}"
    except Exception as exc:
        logger.error(f"Error: {str(exc)}")
        raise self.retry(exc=exc)
```

Call task from views:

```python
from accounts.tasks import my_async_task

# Run asynchronously
my_async_task.delay("value1", "value2")

# Run with delay
my_async_task.apply_async(("value1", "value2"), countdown=10)

# Run synchronously (for testing)
result = my_async_task("value1", "value2")
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
pytest tests/test_api.py::TestUserRegistration::test_register_user

# With coverage
pytest --cov=. --cov-report=html
```

### Writing Tests

```python
import pytest
from rest_framework import status
from django.urls import reverse

@pytest.mark.django_db
class TestUserAPI:
    """Test user API endpoints"""
    
    def test_user_registration(self, api_client):
        """Test user registration"""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
        }
        response = api_client.post(reverse("register-register"), data)
        assert response.status_code == status.HTTP_201_CREATED
        assert "user_id" in response.json()

    def test_user_login(self, api_client, authenticated_user):
        """Test user login"""
        data = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post(reverse("token_obtain"), data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.json()
        assert "refresh" in response.json()
```

---

## 📊 API Documentation

Automatic API documentation is generated at:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

All API endpoints are automatically documented based on your DRF viewsets.

---

## 🚢 Production Deployment Checklist

Before deploying to production:

- [ ] Set `DEBUG=False`
- [ ] Generate secure `SECRET_KEY` (min 50 chars)
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Setup PostgreSQL 14+ database
- [ ] Configure Redis instance
- [ ] Setup email backend (SMTP)
- [ ] Configure SSL/HTTPS certificates
- [ ] Set up database backups
- [ ] Configure logging and monitoring
- [ ] Run full test suite: `pytest`
- [ ] Run security checks: `python manage.py check --deploy`
- [ ] Configure firewall rules
- [ ] Setup monitoring (Sentry, New Relic, etc.)
- [ ] Load test the application

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database Connection Error

```bash
# Check PostgreSQL status
pg_isready

# Test connection
psql -U project_user -d project_db -h localhost
```

### Redis Connection Error

```bash
# Check Redis status
redis-cli ping

# Start Redis if not running
redis-server

# Check Redis info
redis-cli info
```

### Celery Tasks Not Running

```bash
# Check worker logs
celery -A project worker --loglevel=debug

# Purge failed tasks
celery -A project purge

# Check Redis keys
redis-cli
KEYS *  # View all keys
```

### Static Files Not Loading

```bash
# Collect static files
python manage.py collectstatic --noinput

# Verify location
ls -la staticfiles/
```

---

## 📖 Documentation Links

- [Django 6.0 Documentation](https://docs.djangoproject.com/en/6.0/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [Celery 5.6 Documentation](https://docs.celeryproject.org/)
- [PostgreSQL 17 Documentation](https://www.postgresql.org/docs/17/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Documentation](https://docs.docker.com/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/)

---

## 🤝 Need Help?

1. Check logs: `docker-compose logs -f web`
2. Check Django logs in `logs/` directory
3. Review the comprehensive setup guide
4. Check official documentation links above
5. Review error messages carefully

---

**Last Updated**: February 25, 2026  
**Django Version**: 6.0.2  
**Python Version**: 3.13  
**DRF Version**: 3.16.1  
**Celery Version**: 5.6.2
