# Makefile for Django Rapido V2.0
# Usage: make [target]
# NOTE: Uses bash syntax. On Windows: Git Bash, WSL, or PowerShell.

.PHONY: help install migrate runserver test clean docker-up docker-down lint format type-check check quality ci

# Colors
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m

PY := py

help:
	@echo "$(CYAN)Django Rapido V2.0 — Project Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  make install           Install dependencies"
	@echo "  make init              Init project (.env, secret, migrate, superuser)"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make runserver         Run dev server"
	@echo "  make migrate           Run migrations"
	@echo "  make makemigrations    Create migrations"
	@echo "  make shell             Django shell"
	@echo "  make createsuperuser   Create superuser"
	@echo ""
	@echo "$(GREEN)Quality Gates:$(NC)"
	@echo "  make quality           Run all quality gates (format, lint, type-check, test, check)"
	@echo "  make ci                Alias for quality (for CI parity)"
	@echo "  make lint              flake8"
	@echo "  make format            black + isort"
	@echo "  make check-format      black/isort --check"
	@echo "  make type-check        mypy"
	@echo "  make check             python manage.py check --deploy"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test              pytest"
	@echo "  make test-coverage     pytest --cov (fail under 40%)"
	@echo "  make test-fast         pytest -x --ff"
	@echo ""
	@echo "$(GREEN)Docker:$(NC)"
	@echo "  make docker-up         Start Docker"
	@echo "  make docker-down       Stop Docker"
	@echo "  make docker-build      Build images"
	@echo "  make docker-logs       Logs"
	@echo "  make docker-ps         List containers"
	@echo ""
	@echo "$(GREEN)Utilities:$(NC)"
	@echo "  make clean             Remove cache"
	@echo "  make requirements      Freeze requirements"
	@echo "  make collectstatic     Collect static"

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

init:
	@echo "$(CYAN)Initializing Django Rapido...$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 0: Installing dependencies...$(NC)"
	@$(MAKE) install
	@echo ""
	@echo "$(YELLOW)Step 1: Creating .env...$(NC)"
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "$(GREEN)  - .env created$(NC)"; \
		else \
			echo "$(RED)  - .env.example not found!$(NC)"; exit 1; \
		fi; \
	else \
		echo "$(GREEN)  - .env exists, skipping$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Step 2: SECRET_KEY...$(NC)"
	@if grep -q "^SECRET_KEY=" .env 2>/dev/null; then \
		echo "$(GREEN)  - SECRET_KEY exists$(NC)"; \
	else \
		$(PY) -c "from django.core.management.utils import get_random_secret_key; print('SECRET_KEY=django-insecure-' + get_random_secret_key())" >> .env; \
		echo "$(GREEN)  - SECRET_KEY generated$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Step 3: Migrations...$(NC)"
	$(PY) manage.py migrate --noinput
	@echo "$(GREEN)  - Migrations done$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 4: Superuser...$(NC)"
	$(PY) manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); import os; u, created = User.objects.get_or_create(username=os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin'), defaults={'email': os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com'), 'is_staff': True, 'is_superuser': True}); u.set_password(os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin123')); u.save(); print('Superuser ready!' if created else 'Superuser exists')"
	@echo ""
	@echo "$(YELLOW)Step 5: Static...$(NC)"
	$(PY) manage.py collectstatic --noinput
	@echo "$(GREEN)  - Static collected$(NC)"
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)  Django Rapido V2.0 Initialized!$(NC)"
	@echo "$(GREEN)========================================$(NC)"

# ===========================
# Django Management
# ===========================
runserver:
	@echo "$(CYAN)Starting dev server...$(NC)"
	$(PY) manage.py runserver

migrate:
	@echo "$(CYAN)Running migrations...$(NC)"
	$(PY) manage.py migrate
	@echo "$(GREEN)Migrations done$(NC)"

makemigrations:
	@echo "$(CYAN)Creating migrations...$(NC)"
	$(PY) manage.py makemigrations
	@echo "$(GREEN)Migrations created$(NC)"

shell:
	@echo "$(CYAN)Opening shell...$(NC)"
	$(PY) manage.py shell

createsuperuser:
	@echo "$(CYAN)Creating superuser...$(NC)"
	$(PY) manage.py createsuperuser

collectstatic:
	@echo "$(CYAN)Collecting static...$(NC)"
	$(PY) manage.py collectstatic --noinput
	@echo "$(GREEN)Static collected$(NC)"

check:
	@echo "$(CYAN)Django system checks...$(NC)"
	$(PY) manage.py check
	@echo "$(CYAN)Deploy checks...$(NC)"
	$(PY) manage.py check --deploy || true

seed:
	@echo "$(CYAN)Seeding database...$(NC)"
	$(PY) manage.py seed
	@echo "$(GREEN)Database seeded$(NC)"

secret-key:
	@echo Generating secret key...
	@$(PY) -c "from django.core.management.utils import get_random_secret_key; print(f'SECRET_KEY=django-insecure-{get_random_secret_key()}')" >> .env
	@echo Secret key appended to .env

# ===========================
# Quality Gates — REUSE: mirrors CI (.github/workflows/ci.yml)
# ===========================
lint:
	@echo "$(CYAN)Running flake8...$(NC)"
	flake8 --max-line-length=100 --extend-ignore=E203,W503 --exclude=migrations,venv,.venv,.git,__pycache__,staticfiles,media,node_modules .

format:
	@echo "$(CYAN)Formatting with black + isort...$(NC)"
	black --line-length=100 .
	isort --profile=black --line-length=100 .

check-format:
	@echo "$(CYAN)Checking format (black + isort)...$(NC)"
	black --check --line-length=100 .
	isort --check-only --profile=black --line-length=100 .

type-check:
	@echo "$(CYAN)Running mypy...$(NC)"
	mypy --ignore-missing-imports .

test:
	@echo "$(CYAN)Running tests...$(NC)"
	pytest -v --tb=short

test-coverage:
	@echo "$(CYAN)Running tests with coverage (fail under 40%)...$(NC)"
	pytest --cov=. --cov-report=term-missing --cov-report=xml --cov-fail-under=40

test-fast:
	@echo "$(CYAN)Running tests (fail fast)...$(NC)"
	pytest -x --ff

quality: check-format lint type-check test check
	@echo "$(GREEN)All quality gates passed$(NC)"

ci: quality
	@echo "$(GREEN)CI parity passed$(NC)"

# ===========================
# Docker
# ===========================
docker-up:
	@echo "$(CYAN)Starting Docker...$(NC)"
	docker compose up --build -d
	@echo "$(GREEN)Docker started$(NC)"
	@echo "  Django: http://localhost:8000"
	@echo "  Admin:  http://localhost:8000/admin"
	@echo "  Docs:   http://localhost:8000/api/schema/swagger-ui/"

docker-down:
	@echo "$(CYAN)Stopping Docker...$(NC)"
	docker compose down -v
	@echo "$(GREEN)Docker stopped$(NC)"

docker-build:
	@echo "$(CYAN)Building Docker images...$(NC)"
	docker compose build --no-cache
	@echo "$(GREEN)Images built$(NC)"

docker-logs:
	@echo "$(CYAN)Logs...$(NC)"
	docker compose logs -f web

docker-ps:
	@echo "$(CYAN)Containers:$(NC)"
	docker compose ps

docker-shell:
	@echo "$(CYAN)Shell in web...$(NC)"
	docker compose exec web /bin/bash

docker-migrate:
	@echo "$(CYAN)Migrating in Docker...$(NC)"
	docker compose exec web $(PY) manage.py migrate

docker-createsuperuser:
	@echo "$(CYAN)Superuser in Docker...$(NC)"
	docker compose exec web $(PY) manage.py createsuperuser

docker-clean:
	@echo "$(RED)Removing containers and volumes...$(NC)"
	docker compose down -v
	@echo "$(GREEN)Cleaned$(NC)"

# ===========================
# Utilities
# ===========================
clean:
	@echo "$(CYAN)Cleaning cache...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cleaned$(NC)"

requirements:
	@echo "$(CYAN)Freezing requirements...$(NC)"
	pip freeze > requirements.txt
	@echo "$(GREEN)Requirements updated$(NC)"

db-reset:
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(PY) manage.py flush --noinput; \
		$(PY) manage.py migrate; \
		echo "$(GREEN)Database reset$(NC)"; \
	fi

db-backup:
	@echo "$(CYAN)Backing up database...$(NC)"
	pg_dump project_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backed up$(NC)"

install-hooks:
	@echo "$(CYAN)Installing pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)Hooks installed$(NC)"

run-hooks:
	@echo "$(CYAN)Running pre-commit...$(NC)"
	pre-commit run --all-files

docs:
	@echo "$(CYAN)Building docs...$(NC)"
	cd docs && make html 2>/dev/null || echo "No docs/Makefile — see guides/"

dev: install migrate
	@echo "$(GREEN)Dev ready!$(NC)"
	@echo "  make run  (terminal 1)"
	@echo "  make celery-worker (terminal 2)"

.DEFAULT_GOAL := help
