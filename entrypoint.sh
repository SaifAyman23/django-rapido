#!/bin/sh
set -e

if [ "$CONTAINER_ROLE" = "web" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput

    exec gunicorn project.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000}
fi

exec "$@"
