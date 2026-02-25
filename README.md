# 🚀 Django 6.0 Production-Ready Project Template

A comprehensive, production-ready Django project setup with modern best practices, including REST APIs, WebSockets, async task processing, and complete Docker containerization.

**Updated for February 2026** - Django 6.0.2, Python 3.13, DRF 3.16, Celery 5.6, PostgreSQL 17

## ✨ Features

- **Django 6.0** - Latest Django framework
- **Django REST Framework 3.16** - Build powerful REST APIs
- **Django Channels 4.1** - WebSocket support for real-time communication
- **Celery 5.6 + Beat + Flower** - Async task processing and scheduling
- **Simple JWT 5.4** - Token-based authentication
- **PostgreSQL 17** - Production-grade database
- **Redis 7** - Caching and message broker
- **Django Unfold 0.42** - Modern admin interface
- **drf-spectacular 0.30** - Auto-generated API documentation (Swagger/ReDoc)
- **Docker & Docker Compose** - Complete containerization
- **Gunicorn 23 / Uvicorn 0.31** - Production WSGI/ASGI servers
- **pytest 8.3** - Comprehensive testing framework
- **Nginx** - Reverse proxy and static file serving
- **Modular Settings** - Environment-based configuration
- **Type Safety** - mypy + django-stubs support
- **Pre-commit Hooks** - Code quality automation

## 📊 Tech Stack Comparison

| Component | Version | Released |
|-----------|---------|----------|
| **Python** | 3.13 | Oct 2024 |
| **Django** | 6.0.2 | Feb 2024 |
| **DRF** | 3.16.1 | Nov 2024 |
| **Celery** | 5.6.2 | Oct 2024 |
| **PostgreSQL** | 17 | Oct 2024 |
| **Redis** | 7 | Apr 2023 |

## 📋 Requirements

- Python 3.13 (3.10+ minimum)
- PostgreSQL 14+ (17 recommended)
- Docker & Docker Compose (optional)
- Redis 7+
- Git

## 🏃 Quick Start

### Option 1: Docker (Recommended - 5 Minutes)

```bash
# Clone or download this project
git clone your-repo-url
cd project

# Copy environment file
cp .env.example .env

# Start all services (PostgreSQL, Redis, Django, Celery, Flower, Nginx)
docker-compose up -d

# Wait for migrations to complete, then access:
# - API: http://localhost:8000
# - Admin: http://localhost:8000/admin (admin / admin123)
# - API Docs: http://localhost:8000/api/docs/
# - Flower: http://localhost:5555

# View logs
docker-compose logs -f web
```

### Option 2: Local Development (10 Minutes)

```bash
# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL (macOS)
brew install postgresql@17
createdb project_db
createuser project_user
# psql postgres: ALTER USER project_user WITH PASSWORD 'secure_password_here';

# Setup Redis (macOS)
brew install redis
redis-server

# Configure environment
cp .env.example .env
# Edit .env and set DB_HOST=localhost

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver

# In another terminal: Start Celery worker
celery -A project worker --loglevel=info

# In another terminal: Start Celery beat
celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Access: http://localhost:8000
```

Or use Makefile shortcuts:

```bash
make help              # Show all commands
make dev               # Setup development environment
make run               # Start dev server
make celery-worker     # Start Celery worker
make test              # Run tests
make docker-up         # Start Docker services
```

## 📁 Project Structure

```
project/
├── project/                    # Main Django project
│   ├── settings/              # Modular settings
│   │   ├── __init__.py
│   │   ├── base.py            # Shared configuration
│   │   ├── local.py           # Local development
│   │   └── production.py       # Production settings
│   ├── asgi.py                # ASGI (async) entry point
│   ├── wsgi.py                # WSGI (sync) entry point
│   ├── urls.py                # Main URL router
│   └── routing.py             # WebSocket routing
│
├── accounts/                  # User management app
│   ├── models.py             # User models
│   ├── serializers.py        # DRF serializers
│   ├── viewsets.py           # API viewsets
│   ├── urls.py               # App-specific URLs
│   ├── tasks.py              # Celery tasks
│   └── tests.py              # Tests
│
├── common/                    # Shared utilities
│   ├── models.py             # Base models & mixins
│   ├── serializers.py        # Base serializers
│   ├── viewsets.py           # Base viewsets
│   ├── permissions.py        # Custom permissions
│   ├── pagination.py         # Pagination classes
│   ├── filters.py            # Filter classes
│   ├── helpers.py            # Helper functions
│   ├── decorators.py         # Custom decorators
│   ├── exceptions.py         # Custom exceptions
│   └── constants.py          # Constants & enums
│
├── api/                       # Main API app
│   └── v1/                   # API version
│
├── tests/                     # Test configuration
│   ├── conftest.py           # pytest fixtures
│   └── factories.py          # Test factories
│
├── docker/                    # Docker configuration
│   ├── Dockerfile
│   └── nginx.conf
│
├── static/                    # Static files (CSS, JS)
├── media/                     # User uploads
├── logs/                      # Application logs
│
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── .dockerignore             # Docker ignore rules
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # Docker services
├── Dockerfile                # Container image
├── Makefile                  # Development commands
├── pytest.ini                # pytest configuration
├── pyproject.toml            # Python project configuration
├── manage.py                 # Django CLI
├── README.md                 # This file
└── DEPLOYMENT_GUIDE.md       # Production deployment guide
```

## 🛠️ Installation & Setup

### 1. System Dependencies

**macOS:**
```bash
brew install python@3.13 postgresql@17 redis
brew services start postgresql@17
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3.13 python3.13-venv postgresql postgresql-contrib redis-server
sudo systemctl start postgresql
sudo systemctl start redis-server
```

### 2. Clone and Setup Project

```bash
git clone your-repo-url
cd project

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 3. Configure Database

```bash
# Create PostgreSQL database and user
createdb project_db
createuser project_user
psql postgres

-- In psql:
ALTER USER project_user WITH PASSWORD 'secure_password_here';
ALTER ROLE project_user SET client_encoding TO 'utf8';
ALTER ROLE project_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE project_user SET default_transaction_deferrable TO on;
ALTER ROLE project_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;
\q
```

### 4. Setup Environment Variables

```bash
cp .env.example .env
nano .env  # Edit with your settings

# Key variables:
# DJANGO_ENVIRONMENT=local
# DEBUG=True
# SECRET_KEY=your-secret-key
# DB_HOST=localhost
# REDIS_URL=redis://localhost:6379/0
```

### 5. Initialize Database

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 6. Run Development Server

```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A project worker --loglevel=info --concurrency=4

# Terminal 3: Celery beat (optional)
celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Terminal 4: Flower monitoring (optional)
celery -A project flower --port=5555
```

Access the application at http://localhost:8000

## 🐳 Docker Usage

### Start Services

```bash
# Build and start all services
docker-compose up -d

# Follow logs
docker-compose logs -f web

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Available Services

- **Web (Gunicorn)**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Flower (Celery Monitoring)**: http://localhost:5555
- **Nginx (Reverse Proxy)**: http://localhost:80/443

### Common Docker Commands

```bash
make docker-up              # Start services
make docker-down            # Stop services
make docker-build           # Build images
make docker-logs            # View logs
make docker-migrate         # Run migrations
make docker-createsuperuser # Create admin user
docker-compose ps           # List containers
docker-compose exec web /bin/bash  # Shell access
```

## 📝 Common Commands

### Django

```bash
python manage.py runserver          # Development server
python manage.py migrate            # Run migrations
python manage.py makemigrations     # Create migrations
python manage.py createsuperuser    # Create admin user
python manage.py collectstatic      # Collect static files
python manage.py check --deploy     # Security checks
python manage.py shell              # Interactive shell
```

### Testing

```bash
pytest                  # Run all tests
pytest --cov=.         # With coverage
pytest -v              # Verbose output
pytest tests/test_api.py::TestUserRegistration::test_register_user
```

### Code Quality

```bash
make lint               # Flake8 linting
make format            # Black + isort formatting
make check-format      # Check without changes
make type-check        # mypy type checking
```

### Celery

```bash
celery -A project worker --loglevel=info           # Worker
celery -A project beat --loglevel=info             # Scheduler
celery -A project flower --port=5555               # Monitoring
celery -A project purge                            # Purge tasks
celery -A project inspect active                   # Active tasks
```

## 🔑 API Documentation

Once the server is running, access API documentation at:

- **Swagger UI (Interactive)**: http://localhost:8000/api/docs/
- **ReDoc (Beautiful)**: http://localhost:8000/api/redoc/
- **OpenAPI Schema (JSON)**: http://localhost:8000/api/schema/

### Example API Endpoints

```
Authentication:
  POST   /api/accounts/token/               - Get JWT token
  POST   /api/accounts/token/refresh/       - Refresh token
  POST   /api/accounts/register/register/   - Register new user

Users:
  GET    /api/accounts/users/               - List users
  POST   /api/accounts/users/               - Create user
  GET    /api/accounts/users/me/            - Get current user
  POST   /api/accounts/users/change_password/ - Change password
  POST   /api/accounts/users/logout/        - Logout user

Admin:
  GET    /admin/                            - Django admin panel
```

## 📧 Email Configuration

Configure email in `.env`:

```bash
# Console backend (development) - prints to console
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# SMTP backend (production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@example.com
```

## 🔐 Security Checklist

Before deploying to production:

- [ ] Set `DEBUG=False`
- [ ] Generate secure `SECRET_KEY`: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up database backups (automated)
- [ ] Configure secure email settings
- [ ] Enable CSRF protection
- [ ] Set `SECURE_SSL_REDIRECT=True`
- [ ] Set secure cookie flags: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- [ ] Configure CORS properly
- [ ] Run security checks: `python manage.py check --deploy`
- [ ] Review `INSTALLED_APPS` - remove unused apps
- [ ] Implement rate limiting
- [ ] Set up error tracking (Sentry)
- [ ] Configure logging and monitoring
- [ ] Regular security updates
- [ ] Security audit by professional
- [ ] Load testing

## 📚 Documentation

Comprehensive documentation is available in:

- **QUICK_START.md** - Quick reference guide
- **DEPLOYMENT_GUIDE.md** - Production deployment guide
- **django_setup_guide_2025.md** - Comprehensive setup guide
- [Django 6.0 Documentation](https://docs.djangoproject.com/en/6.0/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [Celery 5.6 Documentation](https://docs.celeryproject.org/)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run specific test
pytest tests/test_api.py::TestUserRegistration::test_register_user

# Run with verbose output
pytest -v

# Run with print statements visible
pytest -s
```

## 🚀 Deployment

### Using Gunicorn (REST APIs)

```bash
gunicorn project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --max-requests 1000 \
    --timeout 120
```

### Using Uvicorn (WebSocket Support)

```bash
uvicorn project.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
```

### With Nginx Reverse Proxy

See `nginx.conf` for complete Nginx configuration. Includes:
- SSL/HTTPS support
- Gzip compression
- Static file serving
- WebSocket support
- Security headers
- Rate limiting

### Docker Deployment

```bash
# Build and run with production settings
docker-compose -f docker-compose.yml up -d
```

## 🐛 Troubleshooting

### Port Already in Use

```bash
lsof -i :8000
kill -9 <PID>
```

### Database Connection Error

```bash
pg_isready
psql -U project_user -d project_db -h localhost
```

### Redis Connection Error

```bash
redis-cli ping
redis-cli info
```

### Celery Tasks Not Running

```bash
celery -A project worker --loglevel=debug
celery -A project purge
redis-cli KEYS *
```

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Open a Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 📞 Support

For issues and questions:

1. Check the [QUICK_START.md](QUICK_START.md)
2. Review [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. Check official documentation links
4. Review logs: `docker-compose logs -f web`

## 🎯 Next Steps

1. Customize `common/models.py` with your data models
2. Create serializers for your models in `common/serializers.py`
3. Create viewsets in `common/viewsets.py`
4. Add URLs to `project/urls.py`
5. Write tests in `tests/`
6. Deploy following the deployment guide

---

**Made with ❤️ for Django developers**

**Last Updated**: February 25, 2026  
**Django Version**: 6.0.2  
**Python Version**: 3.13  
**DRF Version**: 3.16.1  
**Status**: Production Ready ✅
