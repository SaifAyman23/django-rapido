# 🚀 Django Production-Ready Project Template

A comprehensive, production-ready Django project setup with all modern best practices, including REST APIs, WebSockets, async task processing, and complete Docker containerization.

## ✨ Features

- **Django REST Framework** - Build powerful REST APIs
- **Django Channels** - WebSocket support for real-time communication
- **Celery + Beat + Flower** - Async task processing and scheduling
- **Simple JWT** - Token-based authentication
- **PostgreSQL** - Production-grade database
- **Redis** - Caching and message broker
- **Django Unfold** - Modern admin interface
- **drf-spectacular** - Auto-generated API documentation with Swagger/ReDoc
- **Docker & Docker Compose** - Complete containerization
- **Gunicorn/Uvicorn** - Production WSGI/ASGI servers
- **pytest** - Comprehensive testing framework
- **Nginx** - Reverse proxy and static file serving
- **Modular Settings** - Environment-based configuration

## 📋 Requirements

- Python 3.9+
- PostgreSQL 12+
- Docker & Docker Compose (optional)
- Redis 7+
- Git

## 🏃 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone or download this project
git clone your-repo-url
cd project

# Copy environment file
cp .env.example .env

# Start all services (PostgreSQL, Redis, Django, Celery, Flower)
docker-compose up -d

# Wait for migrations to complete, then access:
# - API: http://localhost:8000
# - Admin: http://localhost:8000/admin (admin / admin123)
# - API Docs: http://localhost:8000/api/docs/
# - Flower: http://localhost:5555

# View logs
docker-compose logs -f web
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL database
createdb project_db
createuser project_user
# Set password: secure_password_here

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
celery -A project beat --loglevel=info

# Access: http://localhost:8000
```

## 📁 Project Structure

```
project/
├── project/                    # Main Django project
│   ├── settings/              # Modular settings
│   │   ├── base.py            # Shared configuration
│   │   ├── local.py           # Local development
│   │   ├── production.py       # Production settings
│   │   └── celery.py          # Celery configuration
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
│   ├── decorators.py         # Decorators
│   ├── exceptions.py         # Custom exceptions
│   └── constants.py          # Constants & enums
│
├── tests/                     # Test configuration
│   ├── conftest.py           # pytest fixtures
│   └── factories.py          # Test factories
│
├── docker/                    # Docker configuration
│   ├── Dockerfile
│   ├── nginx.conf
│   └── .dockerignore
│
├── static/                    # Static files (CSS, JS)
├── media/                     # User uploads
│
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # Docker services
├── Dockerfile                # Container image
├── Makefile                  # Development commands
├── pytest.ini                # pytest configuration
├── manage.py                 # Django CLI
└── README.md                 # This file
```

## 🛠️ Installation & Setup

### 1. Install System Dependencies

**macOS:**
```bash
brew install python postgresql redis
brew services start postgresql
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3 python3-venv postgresql postgresql-contrib redis-server
sudo systemctl start postgresql
sudo systemctl start redis-server
```

**Windows:**
- Download and install Python 3.11+ from python.org
- Download and install PostgreSQL
- Download and install Redis (using Windows Subsystem for Linux or Redis for Windows)

### 2. Clone and Setup Project

```bash
# Clone repository
git clone your-repo-url
cd project

# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate
# Or Windows
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

### 3. Configure Database

```bash
# Create PostgreSQL database and user
createdb project_db
createuser project_user
psql postgres
ALTER USER project_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE project_db TO project_user;
\q
```

### 4. Setup Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor

# Key variables to set:
# DJANGO_ENVIRONMENT=local
# DEBUG=True
# SECRET_KEY=your-secret-key
# DB_HOST=localhost
# REDIS_URL=redis://localhost:6379/0
```

### 5. Initialize Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 6. Run Development Server

```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A project worker --loglevel=info

# Terminal 3: Celery beat (optional)
celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
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
# View running services
docker-compose ps

# View logs
docker-compose logs -f web

# Execute command in container
docker-compose exec web python manage.py migrate

# Shell into container
docker-compose exec web /bin/bash

# Rebuild images
docker-compose build --no-cache

# Restart services
docker-compose restart
```

## 📝 Common Commands

### Django

```bash
# Create new app
python manage.py startapp app_name

# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Django shell
python manage.py shell

# Check settings
python manage.py check
```

### Testing

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_api.py

# Run with coverage
pytest --cov=.

# Generate HTML coverage report
pytest --cov=. --cov-report=html
# Open htmlcov/index.html

# Run specific test
pytest tests/test_api.py::TestUserRegistration::test_register_user
```

### Code Quality

```bash
# Lint code
flake8 .

# Format code
black .
isort .

# Check formatting
black --check .
```

### Celery

```bash
# Start worker
celery -A project worker --loglevel=info

# Start beat scheduler
celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Start Flower monitoring
celery -A project flower

# Purge all tasks
celery -A project purge
```

### Using Makefile (Shortcut Commands)

```bash
make help          # Show all available commands
make install       # Install dependencies
make migrate       # Run migrations
make run           # Start dev server
make test          # Run tests
make test-coverage # Run tests with coverage
make celery-worker # Start Celery worker
make docker-up     # Start Docker services
make docker-down   # Stop Docker services
make clean         # Clean Python cache files
```

## 🔑 API Documentation

Once the server is running, access API documentation at:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### Available Endpoints

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

Profiles:
  GET    /api/accounts/profiles/my_profile/ - Get own profile
  PUT    /api/accounts/profiles/my_profile/ - Update profile
```

## 📧 Email Configuration

Configure email in `.env`:

```bash
# Console backend (development)
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
- [ ] Generate secure `SECRET_KEY` using: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up database backups
- [ ] Configure secure email settings
- [ ] Enable CSRF protection
- [ ] Set `SECURE_SSL_REDIRECT=True`
- [ ] Set secure cookie flags
- [ ] Configure CORS properly
- [ ] Run security checks: `python manage.py check --deploy`
- [ ] Review `INSTALLED_APPS` and remove unused apps
- [ ] Implement rate limiting
- [ ] Set up monitoring and logging
- [ ] Regular security updates

## 📚 Documentation

Full documentation is available in:

- **DJANGO_COMPLETE_SETUP_GUIDE.md** - Comprehensive setup guide with all details
- **QUICK_START.md** - Quick reference guide
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [Celery Documentation](https://docs.celeryproject.org/)

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

### Using Gunicorn (for REST APIs)

```bash
gunicorn project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --max-requests 1000 \
    --timeout 30
```

### Using Uvicorn (for WebSocket support)

```bash
uvicorn project.asgi:application \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
```

### With Nginx Reverse Proxy

See `nginx.conf` for complete Nginx configuration.

### Docker Deployment

```bash
# Build production image
docker-compose -f docker-compose.yml build

# Run with production settings
docker-compose -f docker-compose.yml up -d
```

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

# Check Redis tasks
redis-cli
KEYS *
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

1. Check the [complete setup guide](DJANGO_COMPLETE_SETUP_GUIDE.md)
2. Review [quick start guide](QUICK_START.md)
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

Last Updated: February 2026  
Django Version: 4.2+  
Python Version: 3.9+
