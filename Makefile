# Makefile for Django Rapido MINI V1.0
# A simplified Django project template for quick project setup
# Usage: make [target]
#
# NOTE: This Makefile uses bash syntax. On Windows:
#       - Use Git Bash, WSL (Windows Subsystem for Linux), or PowerShell
#       - Or run commands manually (see individual targets)

.PHONY: help install migrate runserver test clean docker-up docker-down celery-worker celery-beat flower lint format

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Python command (works on Windows and Unix)
PY := py

help:
	@echo "$(CYAN)Django Rapido MINI V1.0 - Project Management Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Setup & Installation:$(NC)"
	@echo "  make install           Install dependencies"
	@echo "  make init              Initialize project (creates .env, secret key, migrations, superuser)"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make runserver         Run development server"
	@echo "  make migrate           Run migrations"
	@echo "  make makemigrations    Create migrations"
	@echo "  make shell             Open Django shell"
	@echo "  make createsuperuser   Create superuser"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test              Run all tests"
	@echo "  make test-coverage     Run tests with coverage"
	@echo "  make test-fast         Run tests (fail fast)"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  make lint              Run code linting (flake8)"
	@echo "  make format            Format code (black, isort)"
	@echo "  make check-format      Check code format without changes"
	@echo "  make type-check        Run type checking (mypy)"
	@echo ""
	@echo "$(GREEN)Docker:$(NC)"
	@echo "  make docker-up         Start Docker services"
	@echo "  make docker-down       Stop Docker services"
	@echo "  make docker-build      Build Docker images"
	@echo "  make docker-logs       View Docker logs"
	@echo "  make docker-ps         List running containers"
	@echo ""
	@echo "$(GREEN)Utilities:$(NC)"
	@echo "  make clean             Remove Python cache files"
	@echo "  make requirements      Freeze current requirements"
	@echo "  make collectstatic     Collect static files"
	@echo "  make seed              Seed database with sample data"
	@echo ""

# ===========================
# Installation & Setup
# ===========================
install:
	@echo "$(CYAN)Installing Python dependencies...$(NC)"
	$(PY) -m pip install --upgrade pip setuptools wheel
	$(PY) -m pip install -r requirements.txt
	@echo "$(GREEN)Python dependencies installed$(NC)"
	@if [ -f package.json ]; then \
		echo "$(CYAN)Installing Node.js dependencies...$(NC)"; \
		npm install; \
		echo "$(GREEN)Node.js dependencies installed$(NC)"; \
	fi

# Initialize the project:
# 1. Create .env from .env.example (if .env doesn't exist)
# 2. Generate SECRET_KEY if not present in .env
# 3. Run migrations
# 4. Create superuser (non-interactive using env vars from .env)
# 5. Collect static files
# Note: This uses bash syntax - on Windows use Git Bash, WSL, or PowerShell
init:
	@echo "$(CYAN)Initializing Django Rapido MINI project...$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 0: Installing dependencies...$(NC)"
	@$(MAKE) install
	@echo ""
	@echo "$(YELLOW)Step 1: Creating .env from .env.example...$(NC)"
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "$(GREEN)  - .env created from .env.example$(NC)"; \
		else \
			echo "$(RED)  - .env.example not found!$(NC)"; \
			exit 1; \
		fi; \
	else \
		echo "$(GREEN)  - .env already exists, skipping...$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Step 2: Generating SECRET_KEY...$(NC)"
	@if grep -q "^SECRET_KEY=" .env 2>/dev/null; then \
		echo "$(GREEN)  - SECRET_KEY already exists in .env$(NC)"; \
	else \
		$(PY) -c "from django.core.management.utils import get_random_secret_key; print('SECRET_KEY=django-insecure-' + get_random_secret_key())" >> .env; \
		echo "$(GREEN)  - SECRET_KEY generated and added to .env$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Step 3: Running migrations...$(NC)"
	$(PY) manage.py migrate --noinput
	@echo "$(GREEN)  - Migrations completed$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 4: Creating superuser...$(NC)"
	$(PY) manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); import os; u, created = User.objects.get_or_create(username=os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin'), defaults={'email': os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com'), 'is_staff': True, 'is_superuser': True}); u.set_password(os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')); u.save(); print('Superuser ready!' if created else 'Superuser already exists')"
	@echo ""
	@echo "$(YELLOW)Step 5: Collecting static files...$(NC)"
	$(PY) manage.py collectstatic --noinput
	@echo "$(GREEN)  - Static files collected$(NC)"
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)  Django Rapido MINI V1.0 Initialized!$(NC)"
	@echo "$(GREEN)========================================$(NC)"
	@echo ""
	@echo "$(CYAN)Next steps:$(NC)"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Run: make runserver"
	@echo "  3. Visit: http://localhost:8000/admin"
	@echo ""
	@echo "$(YELLOW)Default admin credentials:$(NC)"
	@echo "  Username: admin (or from DJANGO_SUPERUSER_USERNAME in .env)"
	@echo "  Password: admin123 (or from DJANGO_SUPERUSER_PASSWORD in .env)"
	@echo ""
	@echo "$(YELLOW)Note:$(NC) To switch to PostgreSQL, see guides/Settings guide.md"

# ===========================
# Django Management
# ===========================
runserver:
	@echo "$(CYAN)Starting Django development server...$(NC)"
	$(PY) manage.py runserver

migrate:
	@echo "$(CYAN)Running migrations...$(NC)"
	$(PY) manage.py migrate
	@echo "$(GREEN)Migrations completed$(NC)"

makemigrations:
	@echo "$(CYAN)Creating migrations...$(NC)"
	$(PY) manage.py makemigrations
	@echo "$(GREEN)Migrations created$(NC)"

shell:
	@echo "$(CYAN)Opening Django shell...$(NC)"
	$(PY) manage.py shell

createsuperuser:
	@echo "$(CYAN)Creating superuser...$(NC)"
	$(PY) manage.py createsuperuser

collectstatic:
	@echo "$(CYAN)Collecting static files...$(NC)"
	$(PY) manage.py collectstatic --noinput
	@echo "$(GREEN)Static files collected$(NC)"

check:
	@echo "$(CYAN)Running Django system checks...$(NC)"
	$(PY) manage.py check --deploy

seed:
	@echo "$(CYAN)Seeding database...$(NC)"
	$(PY) manage.py seed
	@echo "$(GREEN)Database seeded$(NC)"

secret-key:
	@echo Generating production-ready Django secret key...
	@$(PY) -c "from django.core.management.utils import get_random_secret_key; print(f'SECRET_KEY=django-insecure-{get_random_secret_key()}')" >> .env
	@echo Secret key appended to .env file
	@echo Note: If SECRET_KEY already exists, you will have duplicates - edit manually

# ===========================
# Docker
# ===========================
docker-up:
	@echo "$(CYAN)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Docker services started$(NC)"
	@echo "$(YELLOW)Services:$(NC)"
	@echo "  Django:  http://localhost:8000"
	@echo "  Admin:   http://localhost:8000/admin"
	@echo "  Docs:    http://localhost:8000/api/docs/"

docker-down:
	@echo "$(CYAN)Stopping Docker services...$(NC)"
	docker-compose down
	@echo "$(GREEN)Docker services stopped$(NC)"

docker-build:
	@echo "$(CYAN)Building Docker images...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)Docker images built$(NC)"

docker-logs:
	@echo "$(CYAN)Viewing Docker logs...$(NC)"
	docker-compose logs -f web

docker-ps:
	@echo "$(CYAN)Running containers:$(NC)"
	docker-compose ps

docker-shell:
	@echo "$(CYAN)Opening shell in Docker container...$(NC)"
	docker-compose exec web /bin/bash

docker-migrate:
	@echo "$(CYAN)Running migrations in Docker...$(NC)"
	docker-compose exec web $(PY) manage.py migrate

docker-createsuperuser:
	@echo "$(CYAN)Creating superuser in Docker...$(NC)"
	docker-compose exec web $(PY) manage.py createsuperuser

docker-clean:
	@echo "$(RED)Removing Docker containers and volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)Docker cleaned$(NC)"

# ===========================
# Utilities
# ===========================
clean:
	@echo "$(CYAN)Cleaning Python cache files...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cache cleaned$(NC)"

requirements:
	@echo "$(CYAN)Freezing requirements...$(NC)"
	pip freeze > requirements.txt
	@echo "$(GREEN)Requirements updated$(NC)"

db-reset:
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(PY) manage.py flush; \
		$(PY) manage.py migrate; \
		$(PY) manage.py createsuperuser; \
		echo "$(GREEN)Database reset$(NC)"; \
	fi

db-backup:
	@echo "$(CYAN)Backing up database...$(NC)"
	pg_dump project_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Database backed up$(NC)"

# ===========================
# Pre-commit Hooks
# ===========================
install-hooks:
	@echo "$(CYAN)Installing pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed$(NC)"

run-hooks:
	@echo "$(CYAN)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

# ===========================
# Documentation
# ===========================
docs:
	@echo "$(CYAN)Building documentation...$(NC)"
	cd docs && make html
	@echo "$(GREEN)Documentation built in docs/_build/html/$(NC)"

# ===========================
# Development Workflow
# ===========================
dev: install migrate
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "$(CYAN)Starting development servers...$(NC)"
	@echo "  - Django server (terminal 1): make run"
	@echo "  - Celery worker (terminal 2): make celery-worker"
	@echo "  - Celery beat (terminal 3): make celery-beat"

.DEFAULT_GOAL := help