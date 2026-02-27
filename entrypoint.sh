#!/bin/bash
set -e

# ===========================
# ENTRYPOINT FOR DJANGO + CELERY STACK
# Production-ready with organized sections for easy customization
# ===========================

echo "========================================="
echo "Container started: $(date)"
echo "========================================="

# ===========================
# 1. DETERMINE CONTAINER ROLE
# ===========================
# Set CONTAINER_ROLE in docker-compose.yml environment for each service
CONTAINER_ROLE=${CONTAINER_ROLE:-web}
echo "Container role: $CONTAINER_ROLE"

# ===========================
# 2. WAIT FOR DEPENDENCIES
# ===========================
echo ""
echo "Waiting for dependencies..."

# Wait for PostgreSQL
echo "  Checking PostgreSQL at ${DB_HOST:-db}:${DB_PORT:-5432}..."
max_retries=30
retry_count=0
while [ $retry_count -lt $max_retries ]; do
    if nc -z ${DB_HOST:-db} ${DB_PORT:-5432} 2>/dev/null; then
        echo "  ✓ PostgreSQL is ready"
        break
    fi
    retry_count=$((retry_count + 1))
    if [ $retry_count -lt $max_retries ]; then
        echo "    Attempt $retry_count/$max_retries..."
        sleep 2
    fi
done

if [ $retry_count -eq $max_retries ]; then
    echo "  ✗ PostgreSQL failed to start after $max_retries attempts"
    exit 1
fi

# Wait for Redis (optional - skip if SKIP_REDIS=true)
if [ "${SKIP_REDIS:-false}" != "true" ]; then
    echo "  Checking Redis at ${REDIS_HOST:-redis}:${REDIS_PORT:-6379}..."
    retry_count=0
    while [ $retry_count -lt $max_retries ]; do
        if nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379} 2>/dev/null; then
            echo "  ✓ Redis is ready"
            break
        fi
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            echo "    Attempt $retry_count/$max_retries..."
            sleep 2
        fi
    done
    
    if [ $retry_count -eq $max_retries ]; then
        echo "  ✗ Redis failed to start after $max_retries attempts"
        exit 1
    fi
fi

# ===========================
# 3. DJANGO SETUP (web and workers only)
# ===========================
if [ "$CONTAINER_ROLE" = "web" ] || [ "$CONTAINER_ROLE" = "celery_worker" ]; then
    echo ""
    echo "Running Django setup tasks..."
    
    # Collect static files
    echo "  Collecting static files..."
    python manage.py collectstatic --noinput --clear 2>&1 | grep -v "^Copying\|^Installed"
    
    # Create migrations
    echo "  Creating migrations..."
    python manage.py makemigrations --noinput 2>&1 | grep -v "No changes detected"
    
    # Apply migrations
    echo "  Applying migrations..."
    python manage.py migrate --noinput
    
    # Create superuser (local development only)
    if [ "${DJANGO_ENVIRONMENT:-local}" = "local" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
        echo "  Creating superuser..."
        python manage.py createsuperuser --noinput --username=${DJANGO_SUPERUSER_USERNAME:-admin} --email=${DJANGO_SUPERUSER_EMAIL:-admin@example.com} 2>/dev/null || echo "    (superuser may already exist)"
    fi
    
    echo "✓ Django setup complete"
fi

# ===========================
# 4. START THE APPROPRIATE SERVICE
# ===========================
echo ""
echo "Starting $CONTAINER_ROLE service..."
echo "========================================="
echo ""

case "$CONTAINER_ROLE" in
    web)
        if [ "${DJANGO_ENVIRONMENT:-local}" = "production" ]; then
            echo "Running Gunicorn (production mode)..."
            exec gunicorn project.wsgi:application \
                --bind 0.0.0.0:8000 \
                --workers 4 \
                --worker-class sync \
                --max-requests 1000 \
                --timeout 120 \
                --access-logfile - \
                --error-logfile -
        else
            echo "Running Django runserver (development mode)..."
            exec python manage.py runserver 0.0.0.0:8000
        fi
        ;;
    
    celery_worker)
        echo "Running Celery worker..."
        if [ "${DJANGO_ENVIRONMENT:-local}" = "production" ]; then
            exec celery -A project worker \
                --loglevel=info \
                --concurrency=4 \
                --max-tasks-per-child=100 \
                --time-limit=1800
        else
            exec celery -A project worker \
                --loglevel=info \
                --autoreload
        fi
        ;;
    
    celery_beat)
        echo "Running Celery beat scheduler..."
        exec celery -A project beat \
            --loglevel=info \
            --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    
    flower)
        echo "Running Flower monitoring dashboard..."
        if [ "${DJANGO_ENVIRONMENT:-local}" = "production" ]; then
            exec celery -A project flower \
                --port=5555 \
                --broker=redis://:${REDIS_PASSWORD:-redis_password}@${REDIS_HOST:-redis}:${REDIS_PORT:-6379}/0 \
                --basic_auth=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin123} \
                --persistent \
                --db=/data/flower.db
        else
            exec celery -A project flower \
                --port=5555 \
                --broker=redis://:${REDIS_PASSWORD:-redis_password}@${REDIS_HOST:-redis}:${REDIS_PORT:-6379}/0 \
                --basic_auth=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin123}
        fi
        ;;
    
    *)
        echo "ERROR: Unknown container role: $CONTAINER_ROLE"
        echo "Valid roles: web, celery_worker, celery_beat, flower"
        exit 1
        ;;
esac