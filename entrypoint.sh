#!/bin/sh
set -e

# REUSE: Only web runs migrations + collectstatic + superuser.
# Worker/beat/flower receive their own command via docker-compose.
if [ "${CONTAINER_ROLE:-web}" = "web" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    python manage.py createsuperuser --noinput || true
fi

exec "$@"
