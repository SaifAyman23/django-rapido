#!/bin/sh
set -e

# REUSE: Only the primary web container runs migrations + collectstatic +
# superuser setup. Worker/beat/flower/SSE receive their own role.
if [ "${CONTAINER_ROLE:-web}" = "web" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    python manage.py shell <<'PY'
import os

from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()
username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin123")

if User.objects.filter(Q(email=email) | Q(username=username)).exists():
    print("Superuser already exists; skipping creation.")
else:
    User.objects.create_superuser(
        email=email,
        username=username,
        password=password,
    )
    print("Superuser created.")
PY
fi

exec "$@"
