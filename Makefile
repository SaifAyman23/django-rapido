# Django Project Makefile
# Convenient commands for development

.PHONY: help install migrate run test lint format docker-up docker-down clean

PYTHON := python
MANAGE := $(PYTHON) manage.py
PROJECT := project

help:
	@echo "=============================="
	@echo "Django Project Management"
	@echo "=============================="
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  install          Install dependencies"
	@echo "  venv             Create virtual environment"
	@echo "  migrate          Run database migrations"
	@echo "  makemigrations   Create new migrations"
	@echo "  run              Run development server"
	@echo "  shell            Open Django shell"
	@echo "  createsuperuser  Create superuser"
	@echo "  test             Run tests with pytest"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  lint             Run linting (flake8)"
	@echo "  format           Format code (black, isort)"
	@echo "  docker-up        Start Docker services"
	@echo "  docker-down      Stop Docker services"
	@echo "  docker-logs      View Docker logs"
	@echo "  docker-shell     Shell into web container"
	@echo "  celery-worker    Start Celery worker"
	@echo "  celery-beat      Start Celery beat"
	@echo "  celery-flower    Start Flower (monitoring)"
	@echo "  collectstatic    Collect static files"
	@echo "  clean            Clean up cache files"
	@echo "  clean-db         Reset database (WARNING)"
	@echo ""

# ===========================
# Environment Setup
# ===========================

venv:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "Dependencies installed successfully"

# ===========================
# Database
# ===========================

migrate:
	@echo "Running database migrations..."
	$(MANAGE) migrate

makemigrations:
	@echo "Creating migrations..."
	$(MANAGE) makemigrations

createsuperuser:
	@echo "Creating superuser..."
	$(MANAGE) createsuperuser

# ===========================
# Development Server
# ===========================

run:
	@echo "Starting Django development server..."
	$(MANAGE) runserver

run-verbose:
	@echo "Starting Django with verbose output..."
	$(MANAGE) runserver --verbosity=2

shell:
	@echo "Opening Django shell..."
	$(MANAGE) shell

# ===========================
# Testing
# ===========================

test:
	@echo "Running tests..."
	pytest

test-verbose:
	@echo "Running tests with verbose output..."
	pytest -v

test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=. --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-file:
	@echo "Usage: make test-file FILE=tests/test_api.py"
	pytest $(FILE)

# ===========================
# Code Quality
# ===========================

lint:
	@echo "Running linting..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	@echo "Linting complete"

format:
	@echo "Formatting code..."
	black .
	isort .
	@echo "Code formatted"

format-check:
	@echo "Checking code format..."
	black --check .
	isort --check-only .

# ===========================
# Static Files
# ===========================

collectstatic:
	@echo "Collecting static files..."
	$(MANAGE) collectstatic --noinput

# ===========================
# Celery
# ===========================

celery-worker:
	@echo "Starting Celery worker..."
	celery -A $(PROJECT) worker --loglevel=info

celery-worker-debug:
	@echo "Starting Celery worker in debug mode..."
	celery -A $(PROJECT) worker --loglevel=debug

celery-beat:
	@echo "Starting Celery beat..."
	celery -A $(PROJECT) beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

celery-flower:
	@echo "Starting Flower..."
	celery -A $(PROJECT) flower

celery-purge:
	@echo "WARNING: This will delete all pending Celery tasks"
	celery -A $(PROJECT) purge

# ===========================
# Docker
# ===========================

docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "Services started. Waiting for initialization..."
	sleep 5
	docker-compose logs -f web

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-down-volumes:
	@echo "WARNING: This will delete all Docker volumes (database, redis)"
	docker-compose down -v

docker-logs:
	docker-compose logs -f web

docker-logs-all:
	docker-compose logs -f

docker-logs-celery:
	docker-compose logs -f celery_worker

docker-logs-db:
	docker-compose logs -f db

docker-shell:
	@echo "Opening shell in web container..."
	docker-compose exec web /bin/bash

docker-python:
	@echo "Opening Python shell in web container..."
	docker-compose exec web python

docker-manage:
	@echo "Usage: make docker-manage CMD=migrate"
	docker-compose exec web python manage.py $(CMD)

docker-migrations:
	docker-compose exec web python manage.py migrate

docker-createsuperuser:
	docker-compose exec web python manage.py createsuperuser

docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-build-nocache:
	@echo "Building Docker images (no cache)..."
	docker-compose build --no-cache

docker-ps:
	docker-compose ps

docker-restart:
	@echo "Restarting Docker services..."
	docker-compose restart

# ===========================
# Database Management
# ===========================

db-dump:
	@echo "Dumping database to backup.sql..."
	pg_dump -U project_user -d project_db > backup.sql
	@echo "Database dumped successfully"

db-restore:
	@echo "Restoring database from backup.sql..."
	psql -U project_user -d project_db < backup.sql
	@echo "Database restored successfully"

db-reset:
	@echo "WARNING: This will delete all data in the database"
	$(MANAGE) flush

# ===========================
# Cleanup
# ===========================

clean:
	@echo "Cleaning up Python cache files..."
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	@echo "Cleanup complete"

clean-all: clean
	@echo "Removing virtual environment and cache..."
	rm -rf venv/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf build/
	rm -rf dist/
	@echo "Full cleanup complete"

# ===========================
# Project Info
# ===========================

info:
	@echo "=============================="
	@echo "Project Information"
	@echo "=============================="
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Django: $$($(PYTHON) -c 'import django; print(django.get_version())')"
	@echo "Environment: $$(grep DJANGO_ENVIRONMENT .env || echo 'Not set')"
	@echo ""
	@echo "Running processes:"
	docker-compose ps || echo "Docker services not running"

# ===========================
# Development Workflow
# ===========================

dev: migrate run

dev-docker: docker-up

install-dev: install
	pip install -r requirements.txt
	@echo "Development environment ready"

# ===========================
# Production Preparation
# ===========================

build-prod:
	@echo "Building for production..."
	$(MANAGE) collectstatic --noinput
	docker-compose -f docker-compose.yml build

# ===========================
# Aliases
# ===========================

m: migrate
mm: makemigrations
t: test
tc: test-coverage
l: lint
f: format
cw: celery-worker
cb: celery-beat
du: docker-up
dd: docker-down
dl: docker-logs
