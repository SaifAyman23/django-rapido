# Dockerfile (Production - Django 5.2, Python 3.13)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=project.settings \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies + Node.js (for Tailwind)
# REUSE: remove nodejs/npm if your project has no frontend build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    netcat-openbsd \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy and install dependencies
COPY requirements.txt .
COPY package.json .
RUN npm install
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directories
RUN mkdir -p /app/logs /app/staticfiles /app/media

# Collect static files (before changing user)
RUN python manage.py collectstatic --noinput

# Copy entrypoint and set permissions
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Change ownership and switch to non-root user
RUN chown -R appuser:appuser /app /entrypoint.sh
USER appuser

EXPOSE 8000

# Default command (overridden by docker-compose command:)
CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000"]

ENTRYPOINT ["/entrypoint.sh"]
