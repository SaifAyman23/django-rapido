# Django Modular Settings Guide

## Overview

Your Django settings have been reorganized from a single 470-line file into a modular structure with 13 focused files. This improves maintainability, reduces merge conflicts, and provides clear separation between environments.

---

## File Structure

```
project/settings/
├── __init__.py              # Entry point, loads environment variables and imports all components
├── base.py                  # Core Django configuration shared across all environments
├── local.py                 # Development environment settings
├── production.py            # Production environment settings
├── testing.py               # Test environment settings (fast, isolated)
├── unfold_config.py         # Admin interface theme configuration
│
└── components/              # Feature-specific settings modules
    ├── __init__.py
    ├── apps.py              # INSTALLED_APPS and MIDDLEWARE
    ├── database.py          # Database configuration
    ├── cache.py             # Redis caching and session storage
    ├── celery.py            # Async task processing with Celery
    ├── api.py               # REST Framework and JWT authentication
    ├── security.py          # CORS, SSL, CSRF, and security headers
    ├── logging.py           # Logging handlers and formatters
    ├── channels.py          # Django Channels for WebSockets
    └── third_party.py       # AWS, Sentry, and external services
```

---

## Loading Order

Settings are loaded in this sequence:

1. Environment variables from `.env` files
2. `base.py` - Core configuration
3. `components/*` - Feature-specific settings
4. `unfold_config.py` - Admin theme
5. Environment-specific file (`local.py`, `production.py`, or `testing.py`)

Later imports override earlier ones, allowing environment-specific customization.

---

## Environment Management

### Setting the Environment

Control which settings file loads using the `DJANGO_ENVIRONMENT` variable:

```bash
# Local development (default, no variable needed)
python manage.py runserver

# Testing
DJANGO_ENVIRONMENT=testing python manage.py test

# Production
DJANGO_ENVIRONMENT=production gunicorn project.wsgi:application
```

### Environment Files

| Environment | File | Characteristics |
|------------|------|-----------------|
| local | `local.py` | DEBUG enabled, relaxed security, development tools |
| production | `production.py` | DEBUG disabled, SSL enforced, security hardened |
| testing | `testing.py` | In-memory database, no migrations, fast execution |

---

## Common Modifications

### Database Configuration

**File:** `components/database.py` or `.env`

Update environment variables:
```bash
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### Adding Django Applications

**File:** `components/apps.py`

```python
INSTALLED_APPS = [
    # Existing apps...
    "your_new_app",
]
```

### Celery Configuration

**File:** `components/celery.py` or `.env`

```bash
CELERY_BROKER_URL=redis://:password@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:password@localhost:6379/0
```

### Email Settings

**File:** `components/email.py` or `.env`

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
```

> Added in `base.py`

### Security Headers (Production Only)

**File:** `production.py`

These are already configured but can be modified:
```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

---

## File Reference

| File | Purpose | When to Edit |
|------|---------|--------------|
| `base.py` | Core Django settings | Rarely, only for fundamental changes |
| `local.py` | Development settings | Add dev-specific tools or relaxed security |
| `production.py` | Production settings | Adjust security headers or allowed hosts |
| `testing.py` | Test settings | Optimize test performance or change test database |
| `components/apps.py` | Apps and middleware | Add/remove Django apps or middleware |
| `components/database.py` | Database | Change database engine or connection pooling |
| `components/cache.py` | Caching | Modify Redis cache configuration |
| `components/celery.py` | Task queue | Update Celery broker or task settings |
| `components/api.py` | API docs | Adjust JWT token lifetimes or DRF settings Update API documentation metadata |
| `components/security.py` | Security | Configure CORS or base security settings |
| `components/logging.py` | Logging | Adjust log levels or add new handlers |
| `components/channels.py` | WebSockets | Configure Channels layer or Redis connection |
| `components/third_party.py` | External services | Add AWS, Sentry, or other integrations |

---

## Environment Variables

All sensitive configuration should be stored in environment variables, not hardcoded in Python files.

### .env File Structure

```bash
# Django Core
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=project_db
DB_USER=project_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_PASSWORD=redis_password
REDIS_URL=redis://:redis_password@localhost:6379/0
CACHE_URL=redis://:redis_password@localhost:6379/1

# Celery
CELERY_BROKER_URL=redis://:redis_password@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:redis_password@localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
CORS_TRUSTED_ORIGINS=http://localhost:3000,http://localhost:8000

# Security
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

### Environment-Specific Files

- `.env` - Base configuration (committed to repository with example values)
- `.env.local` - Local overrides (not committed, developer-specific)
- `.env.production` - Production overrides (not committed, contains secrets)

---

## Testing Configuration

The `testing.py` file provides optimized settings for test execution:

**Run tests:**
```bash
DJANGO_ENVIRONMENT=testing python manage.py test
```

**Key optimizations:**
- In-memory SQLite database (10-100x faster than PostgreSQL)
- Migrations disabled (tables created directly from models)
- Fast password hashing (MD5 instead of bcrypt)
- Synchronous Celery (no worker process needed)
- Dummy cache backend (no Redis needed)

---

## Migration from Single File

### Before
```
project/settings.py  (many lines)
```

### After
```
project/settings/  (several files, average 40 lines each)
```

### No Code Changes Required

Your existing code continues to work without modification:
- `manage.py` automatically detects `settings/__init__.py`
- `wsgi.py` and `asgi.py` remain unchanged
- All Django commands work identically
- All apps and URLs continue functioning

---

## Troubleshooting

### Changes Not Applied

1. Restart the development server after modifying settings
2. Verify `DJANGO_ENVIRONMENT` is set correctly: `echo $DJANGO_ENVIRONMENT`
3. Check the `.env` file is in the project root (same directory as `manage.py`)
4. Ensure the correct environment-specific file is being loaded

### Wrong Environment Loading

```bash
# Check current environment
python manage.py shell
>>> import os
>>> print(os.getenv('DJANGO_ENVIRONMENT'))

# Reset to default (local)
unset DJANGO_ENVIRONMENT
```

### Import Errors

If you encounter import errors after migration:
1. Verify `__init__.py` exists in both `settings/` and `settings/components/`
2. Check import order in `settings/__init__.py`
3. Ensure `BASE_DIR` is correctly defined before component imports

---

## Best Practices

1. **Never commit `.env.local` or `.env.production`** - Add to `.gitignore`
2. **Use environment variables for secrets** - Never hardcode passwords or API keys
3. **Keep environment files in sync** - Document required variables in `.env.example`
4. **Test with testing.py** - Always use `DJANGO_ENVIRONMENT=testing` for test runs
5. **Document custom settings** - Add comments when adding new configuration
6. **Maintain separation** - Keep environment-specific settings in appropriate files

---

## Summary

This modular structure provides:

- Clear organization by feature and environment
- Reduced merge conflicts in team development
- Easy maintenance and debugging
- Explicit environment separation
- No changes to existing Django workflow

All settings continue to work as before, but are now organized into logical, maintainable components.