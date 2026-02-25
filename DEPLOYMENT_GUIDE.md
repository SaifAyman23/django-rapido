# 🚀 Production Deployment Guide

Complete guide for deploying your Django project to production.

---

## 📋 Pre-Deployment Checklist

### Code & Configuration

- [ ] All tests passing: `pytest --cov`
- [ ] No hardcoded secrets in code
- [ ] `DEBUG=False` in production settings
- [ ] Unique, secure `SECRET_KEY` generated
- [ ] `ALLOWED_HOSTS` configured for your domain(s)
- [ ] `CSRF_TRUSTED_ORIGINS` configured
- [ ] Database migrations tested
- [ ] Static files can be collected without errors
- [ ] All environment variables documented
- [ ] `.env.production` created and secured

### Security

- [ ] HTTPS/SSL certificates obtained (Let's Encrypt)
- [ ] SECURE_SSL_REDIRECT enabled
- [ ] SESSION_COOKIE_SECURE enabled
- [ ] CSRF_COOKIE_SECURE enabled
- [ ] SECURE_HSTS_SECONDS configured
- [ ] X-Frame-Options set to DENY
- [ ] X-Content-Type-Options set to nosniff
- [ ] Security headers configured in Nginx
- [ ] CORS settings properly configured
- [ ] Rate limiting enabled
- [ ] Security audit completed: `python manage.py check --deploy`

### Infrastructure

- [ ] PostgreSQL database created and secured
- [ ] PostgreSQL user created with limited privileges
- [ ] Redis instance running and secured
- [ ] Database backups configured
- [ ] Monitoring/logging configured
- [ ] Error tracking (Sentry) configured
- [ ] Email service configured
- [ ] CDN configured for static files (optional)
- [ ] Docker images built and tested
- [ ] Domain name registered and DNS configured

---

## 🌐 Deployment Options

### Option 1: Docker (Recommended)

#### Prerequisites

- Docker installed on server
- Docker Compose installed
- Domain name pointing to server
- SSL certificates ready

#### Steps

1. **SSH into Server**

```bash
ssh user@your-server.com
```

2. **Clone Repository**

```bash
cd /opt
git clone your-repo-url project
cd project
```

3. **Configure Environment**

```bash
# Copy and edit .env for production
cp .env.example .env.production

# Edit with production values
nano .env.production

# Important variables:
# DJANGO_ENVIRONMENT=production
# DEBUG=False
# SECRET_KEY=<generate-new-secure-key>
# ALLOWED_HOSTS=example.com,www.example.com
# DB_NAME=project_prod_db
# DB_USER=project_prod_user
# DB_PASSWORD=<strong-password>
```

4. **Generate SSL Certificates**

```bash
# Using Let's Encrypt with Certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d example.com -d www.example.com

# Certificates will be at:
# /etc/letsencrypt/live/example.com/fullchain.pem
# /etc/letsencrypt/live/example.com/privkey.pem
```

5. **Update docker-compose.yml**

```yaml
# Update these services:
environment:
  - DJANGO_ENVIRONMENT=production
  - DEBUG=False
  - ALLOWED_HOSTS=example.com,www.example.com
  - DB_PASSWORD=<strong-password>

# For Nginx, mount SSL certificates:
volumes:
  - /etc/letsencrypt/live/example.com:/etc/nginx/ssl:ro
```

6. **Build and Start Services**

```bash
# Pull latest code
git pull origin main

# Build Docker images
docker-compose -f docker-compose.yml build --no-cache

# Start services
docker-compose -f docker-compose.yml up -d

# Check logs
docker-compose logs -f web
```

7. **Initialize Database**

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

8. **Verify Deployment**

```bash
# Check all services running
docker-compose ps

# Test API
curl https://example.com/api/health/

# Check logs for errors
docker-compose logs
```

### Option 2: Manual Deployment (Ubuntu/Debian)

#### 1. System Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
    python3 python3-venv python3-dev \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    git \
    curl \
    supervisor \
    certbot python3-certbot-nginx

# Start services
sudo systemctl start postgresql
sudo systemctl start redis-server
sudo systemctl enable postgresql redis-server
```

#### 2. Create Application User

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash django

# Switch to user
sudo su - django

# Clone repository
git clone your-repo-url ~/project
cd ~/project
```

#### 3. Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure Database

```bash
# Create PostgreSQL database
sudo su - postgres
psql

CREATE DATABASE project_prod_db;
CREATE USER project_prod_user WITH PASSWORD 'strong_password';

ALTER ROLE project_prod_user SET client_encoding TO 'utf8';
ALTER ROLE project_prod_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE project_prod_user SET default_transaction_deferrable TO on;
ALTER ROLE project_prod_user SET timezone TO 'UTC';

GRANT ALL PRIVILEGES ON DATABASE project_prod_db TO project_prod_user;
\q
```

#### 5. Configure Environment

```bash
# As django user, create .env
nano /home/django/project/.env

# Content:
DJANGO_ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-new-key>
ALLOWED_HOSTS=example.com,www.example.com
DB_ENGINE=django.db.backends.postgresql
DB_NAME=project_prod_db
DB_USER=project_prod_user
DB_PASSWORD=strong_password
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

#### 6. Django Setup

```bash
cd ~/project

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Test deployment
python manage.py check --deploy
```

#### 7. Setup Gunicorn

```bash
# Create systemd service file
sudo nano /etc/systemd/system/gunicorn.service

# Content:
[Unit]
Description=gunicorn daemon for django project
After=network.target

[Service]
User=django
Group=www-data
WorkingDirectory=/home/django/project
ExecStart=/home/django/project/venv/bin/gunicorn \
          --workers 4 \
          --worker-class sync \
          --max-requests 1000 \
          --timeout 30 \
          --bind unix:/run/gunicorn.sock \
          project.wsgi:application

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
```

#### 8. Setup Celery Worker

```bash
# Create systemd service
sudo nano /etc/systemd/system/celery.service

# Content:
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=django
Group=www-data
WorkingDirectory=/home/django/project
ExecStart=/home/django/project/venv/bin/celery multi start worker \
          -A project \
          --pidfile=/var/run/celery/%n.pid \
          --logfile=/var/log/celery/%n%I.log \
          --loglevel=info \
          --concurrency=4

ExecStop=/home/django/project/venv/bin/celery multi stopwait worker \
         --pidfile=/var/run/celery/%n.pid

[Install]
WantedBy=multi-user.target

# Setup directories
sudo mkdir -p /var/run/celery /var/log/celery
sudo chown django:www-data /var/run/celery /var/log/celery

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable celery
sudo systemctl start celery
```

#### 9. Setup Celery Beat

```bash
# Create systemd service
sudo nano /etc/systemd/system/celery-beat.service

# Content:
[Unit]
Description=Celery Beat Service
After=network.target

[Service]
User=django
Group=www-data
WorkingDirectory=/home/django/project
ExecStart=/home/django/project/venv/bin/celery \
          -A project \
          beat \
          --loglevel=info \
          --scheduler django_celery_beat.schedulers:DatabaseScheduler

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable celery-beat
sudo systemctl start celery-beat
```

#### 10. Configure Nginx

```bash
# Create Nginx config
sudo nano /etc/nginx/sites-available/django

# Content:
upstream django {
    server unix:/run/gunicorn.sock;
}

server {
    listen 80;
    server_name example.com www.example.com;
    client_max_body_size 10M;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name example.com www.example.com;
    client_max_body_size 10M;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    location /static/ {
        alias /home/django/project/staticfiles/;
    }

    location /media/ {
        alias /home/django/project/media/;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/django /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

#### 11. Setup SSL Certificate

```bash
# Get SSL certificate
sudo certbot certonly --webroot -w /var/www/certbot -d example.com -d www.example.com

# Auto-renew
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Verify renewal (test)
sudo certbot renew --dry-run
```

---

## 🔄 Continuous Deployment

### Using GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      env:
        DB_ENGINE: django.db.backends.postgresql
        DB_NAME: test_db
        DB_USER: test_user
        DB_PASSWORD: test_pass
        DB_HOST: localhost
      run: |
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to production
      env:
        DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
        DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}
        DEPLOY_USER: ${{ secrets.DEPLOY_USER }}
      run: |
        mkdir -p ~/.ssh
        echo "$DEPLOY_KEY" > ~/.ssh/deploy_key
        chmod 600 ~/.ssh/deploy_key
        ssh-keyscan -H $DEPLOY_HOST >> ~/.ssh/known_hosts
        
        ssh -i ~/.ssh/deploy_key $DEPLOY_USER@$DEPLOY_HOST << 'EOF'
          cd ~/project
          git pull origin main
          docker-compose -f docker-compose.yml pull
          docker-compose -f docker-compose.yml up -d
          docker-compose exec -T web python manage.py migrate
        EOF
```

---

## 📊 Monitoring & Maintenance

### Database Backups

```bash
# Automated daily backups
# Create cron job:
crontab -e

# Add:
0 2 * * * /home/django/project/backup.sh

# Create backup.sh:
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +\%Y\%m\%d_\%H\%M\%S)
pg_dump -U project_prod_user project_prod_db | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete
```

### Log Rotation

```bash
# Configure logrotate
sudo nano /etc/logrotate.d/django

# Content:
/home/django/project/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 django www-data
    sharedscripts
    postrotate
        systemctl reload gunicorn > /dev/null 2>&1 || true
    endscript
}
```

### Monitoring with Sentry

```bash
# Install Sentry SDK
pip install sentry-sdk

# Add to settings/production.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False
)
```

### Health Checks

```bash
# Add monitoring endpoint
# Create management command: accounts/management/commands/health_check.py

from django.core.management.base import BaseCommand
from django.db import connection
import redis

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            # Check database
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            # Check Redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            
            self.stdout.write(self.style.SUCCESS('Health check passed'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Health check failed: {e}'))
            sys.exit(1)
```

---

## 🚨 Troubleshooting

### Application won't start

```bash
# Check logs
docker-compose logs -f web

# Or check systemd service
sudo journalctl -u gunicorn -n 50

# Check migrations
docker-compose exec web python manage.py migrate --check

# Check settings
docker-compose exec web python manage.py check --deploy
```

### Database issues

```bash
# Check PostgreSQL
psql -U project_prod_user -d project_prod_db

# Backup and restore
pg_dump project_prod_db > backup.sql
psql project_prod_db < backup.sql
```

### Celery not processing tasks

```bash
# Check Redis
redis-cli ping

# Check worker
systemctl status celery

# Check beat
systemctl status celery-beat

# Purge tasks
celery -A project purge
```

### SSL certificate issues

```bash
# Test certificate
curl -vI https://example.com

# Renew manually
sudo certbot renew

# Check expiration
sudo certbot certificates
```

---

## 📈 Performance Optimization

### Database

```python
# settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Database query caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    }
}
```

### Gunicorn

```bash
# Optimize workers
# Formula: (2 x CPU cores) + 1
# For 4 cores: (2 x 4) + 1 = 9 workers

gunicorn project.wsgi:application \
    --workers 9 \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30 \
    --keep-alive 5
```

### Static Files

```bash
# Use CloudFront or similar CDN
# In settings/production.py:
STATIC_URL = 'https://cdn.example.com/static/'

# Or use WhiteNoise for gzip compression
pip install whitenoise
# Add to MIDDLEWARE (after SecurityMiddleware):
'whitenoise.middleware.WhiteNoiseMiddleware',
```

---

## 🔒 Security Hardening

### Firewall

```bash
# UFW (Ubuntu)
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### SSH Key Access

```bash
# Disable password authentication
sudo nano /etc/ssh/sshd_config

# Change:
PasswordAuthentication no
PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart ssh
```

### Fail2ban

```bash
# Install
sudo apt-get install fail2ban

# Configure
sudo nano /etc/fail2ban/jail.local

# Content:
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
```

---

**Last Updated**: February 2026  
**Version**: 1.0
