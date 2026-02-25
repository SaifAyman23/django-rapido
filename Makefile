# Makefile for Django 6.0 Project (Feb 2026)
# Usage: make [target]

.PHONY: help install migrate run test clean docker-up docker-down celery-worker celery-beat flower lint format

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help:
	@echo "$(CYAN)Django 6.0 Project Management Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Setup & Installation:$(NC)"
	@echo "  make install           Install dependencies"
	@echo "  make init              Initialize project (migrations + superuser)"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make run               Run development server"
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
	@echo "$(GREEN)Celery Tasks:$(NC)"
	@echo "  make celery-worker     Start Celery worker"
	@echo "  make celery-beat       Start Celery beat scheduler"
	@echo "  make flower            Start Celery Flower monitoring"
	@echo "  make celery-purge      Purge all Celery tasks"
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
	@echo "$(CYAN)Installing dependencies...$(NC)"
	pip install --upgrade pip setuptools wheel
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

init: migrate
	@echo "$(CYAN)Initializing project...$(NC)"
	python manage.py createsuperuser
	python manage.py collectstatic --noinput
	@echo "$(GREEN)✓ Project initialized$(NC)"

# ===========================
# Django Management
# ===========================
run:
	@echo "$(CYAN)Starting Django development server...$(NC)"
	python manage.py runserver

migrate:
	@echo "$(CYAN)Running migrations...$(NC)"
	python manage.py migrate
	@echo "$(GREEN)✓ Migrations completed$(NC)"

makemigrations:
	@echo "$(CYAN)Creating migrations...$(NC)"
	python manage.py makemigrations
	@echo "$(GREEN)✓ Migrations created$(NC)"

shell:
	@echo "$(CYAN)Opening Django shell...$(NC)"
	python manage.py shell

createsuperuser:
	@echo "$(CYAN)Creating superuser...$(NC)"
	python manage.py createsuperuser

collectstatic:
	@echo "$(CYAN)Collecting static files...$(NC)"
	python manage.py collectstatic --noinput
	@echo "$(GREEN)✓ Static files collected$(NC)"

check:
	@echo "$(CYAN)Running Django system checks...$(NC)"
	python manage.py check --deploy

seed:
	@echo "$(CYAN)Seeding database...$(NC)"
	python manage.py seed
	@echo "$(GREEN)✓ Database seeded$(NC)"

# ===========================
# Testing
# ===========================
test:
	@echo "$(CYAN)Running tests...$(NC)"
	pytest -v

test-coverage:
	@echo "$(CYAN)Running tests with coverage...$(NC)"
	pytest --cov=. --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

test-fast:
	@echo "$(CYAN)Running tests (fail fast)...$(NC)"
	pytest -x -v

test-file:
	@echo "$(CYAN)Running tests for specific file...$(NC)"
	pytest $(FILE) -v

# ===========================
# Code Quality
# ===========================
lint:
	@echo "$(CYAN)Running code linting...$(NC)"
	flake8 --config=.flake8 --max-line-length=100 .
	@echo "$(GREEN)✓ Linting completed$(NC)"

format:
	@echo "$(CYAN)Formatting code...$(NC)"
	black . --line-length=100
	isort . --profile=black --line-length=100
	@echo "$(GREEN)✓ Code formatted$(NC)"

check-format:
	@echo "$(CYAN)Checking code format...$(NC)"
	black . --line-length=100 --check
	isort . --profile=black --line-length=100 --check-only
	@echo "$(GREEN)✓ Code format check passed$(NC)"

type-check:
	@echo "$(CYAN)Running type checking...$(NC)"
	mypy . --ignore-missing-imports
	@echo "$(GREEN)✓ Type check completed$(NC)"

# ===========================
# Celery Tasks
# ===========================
celery-worker:
	@echo "$(CYAN)Starting Celery worker...$(NC)"
	celery -A project worker --loglevel=info --concurrency=4

celery-beat:
	@echo "$(CYAN)Starting Celery beat scheduler...$(NC)"
	celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

flower:
	@echo "$(CYAN)Starting Celery Flower monitoring...$(NC)"
	@echo "$(YELLOW)Flower will be available at http://localhost:5555$(NC)"
	celery -A project flower --port=5555

celery-purge:
	@echo "$(RED)Purging all Celery tasks...$(NC)"
	celery -A project purge -f

# ===========================
# Docker
# ===========================
docker-up:
	@echo "$(CYAN)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Docker services started$(NC)"
	@echo "$(YELLOW)Services:$(NC)"
	@echo "  Django:  http://localhost:8000"
	@echo "  Admin:   http://localhost:8000/admin"
	@echo "  Docs:    http://localhost:8000/api/docs/"
	@echo "  Flower:  http://localhost:5555"

docker-down:
	@echo "$(CYAN)Stopping Docker services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Docker services stopped$(NC)"

docker-build:
	@echo "$(CYAN)Building Docker images...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)✓ Docker images built$(NC)"

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
	docker-compose exec web python manage.py migrate

docker-createsuperuser:
	@echo "$(CYAN)Creating superuser in Docker...$(NC)"
	docker-compose exec web python manage.py createsuperuser

docker-clean:
	@echo "$(RED)Removing Docker containers and volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ Docker cleaned$(NC)"

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
	@echo "$(GREEN)✓ Cache cleaned$(NC)"

requirements:
	@echo "$(CYAN)Freezing requirements...$(NC)"
	pip freeze > requirements.txt
	@echo "$(GREEN)✓ Requirements updated$(NC)"

db-reset:
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		python manage.py flush; \
		python manage.py migrate; \
		python manage.py createsuperuser; \
		@echo "$(GREEN)✓ Database reset$(NC)"; \
	fi

db-backup:
	@echo "$(CYAN)Backing up database...$(NC)"
	pg_dump project_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Database backed up$(NC)"

# ===========================
# Pre-commit Hooks
# ===========================
install-hooks:
	@echo "$(CYAN)Installing pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"

run-hooks:
	@echo "$(CYAN)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

# ===========================
# Documentation
# ===========================
docs:
	@echo "$(CYAN)Building documentation...$(NC)"
	cd docs && make html
	@echo "$(GREEN)✓ Documentation built in docs/_build/html/$(NC)"

# ===========================
# Development Workflow
# ===========================
dev: install migrate
	@echo "$(GREEN)✓ Development environment ready!$(NC)"
	@echo "$(CYAN)Starting development servers...$(NC)"
	@echo "  - Django server (terminal 1): make run"
	@echo "  - Celery worker (terminal 2): make celery-worker"
	@echo "  - Celery beat (terminal 3): make celery-beat"

.DEFAULT_GOAL := help
