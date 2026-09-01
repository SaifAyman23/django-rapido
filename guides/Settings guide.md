# Django Rapido Settings Guide

## Overview

Settings are modular by environment: `base.py` (shared) → `local.py` / `production.py` (overlay) → `__init__.py` dispatches. No `components/` split — that was aspirational and removed for clarity. Fail-fast secrets, TESTING detection, and REUSE comments document portability.

---

## File Structure (actual)

```
project/settings/
├── __init__.py              # Dispatches ENVIRONMENT, DX print if DEBUG
├── base.py                  # Shared config (DB, cache, Celery, DRF, JWT, i18n)
├── local.py                 # Dev overrides (DEBUG=True, eager Celery, conditional CORS)
├── production.py            # Production hardening (HSTS, SSL, fail-fast ALLOWED_HOSTS)
└── unfold_config.py         # Admin theme (sidebar nav, colors, branding)
```

Removed: `components/` (13-file split was aspirational), `testing.py` (handled via `TESTING` flag in `base.py` + `sys.argv`).

---

## Loading Order

1. `.env` via `load_dotenv('.env')` (`base.py:12`)
2. `base.py` — core config + `TESTING = os.getenv("TESTING")=="true" or "test" in sys.argv` + `SECRET_KEY` guard
3. `unfold_config.py` wildcard import
4. `__init__.py` — `if ENVIRONMENT=='production': from .production import * else: from .local import *`

`__init__.py:4` prints `[settings] Loading environment: {ENVIRONMENT}` when `DEBUG=True`.

---

## Environment Management

| Environment | File | Characteristics |
|-------------|------|-----------------|
| local | `local.py` | `DEBUG=True`, `ALLOWED_HOSTS=*`, `CELERY_ALWAYS_EAGER`, conditional CORS override |
| production | `production.py` | `DEBUG=False`, `SECURE_PROXY_SSL_HEADER`, HSTS ramp `31536000`, `ALLOWED_HOSTS` fail-fast |
| testing | auto | `TESTING=True` → SQLite `db.sqlite3` + `CELERY_ALWAYS_EAGER`, `SECURE_*` forced off, `SECRET_KEY` ephemeral |

```bash
# Local (default)
python manage.py runserver

# Testing (auto-detected)
python manage.py test  # TESTING=True via sys.argv

# Explicit
DJANGO_ENVIRONMENT=production gunicorn project.wsgi:application
```

---

## Key Settings (base.py) — REUSE notes

| Setting | Lines | REUSE |
|---------|-------|-------|
| `TESTING` + `CELERY_ALWAYS_EAGER` | `base.py:19-32` | `TESTING` wins via env or `test` in argv; syncs `os.environ["TESTING"]` for mixins error handling |
| `SECRET_KEY` guard | `base.py:34-43` | Raises `ImproperlyConfigured` if missing unless `TESTING`; never hardcoded fallback |
| `BUSINESS_TIME_ZONE` | `base.py:217` | `os.getenv("BUSINESS_TIME_ZONE","Africa/Cairo")` — used by `contacts.services.is_ordering_open()` for hours gate |
| `INSTALLED_APPS` | `base.py:51-93` | `modeltranslation` before `admin` (required order), `markdownx`, opt-in `allauth` providers commented, `notifications/compliance/contacts` added |
| `MODELTRANSLATION_*` + `LOCALE_PATHS` | `base.py:206-214` | `LANGUAGES en/ar`, `LOCALE_PATHS=[BASE_DIR/locale]`, `USE_L10N=True` |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | `base.py:259` | `50MB` for Excel/CSV base64 Celery imports (`catalog/tasks.py`) |
| `CACHES` + `SESSION_ENGINE` | `base.py:265-283` | `django_redis` `max_connections 50`, `SOCKET_TIMEOUT 5`, Redis `cache` backend |
| `CELERY_*` + `CELERY_BEAT_SCHEDULE` | `base.py:286-319` | `BROKER redis:6379/0` JSON, `HEARTBEAT 120`, `PREFETCH 1`, `ACKS_LATE`; example beat commented |
| `REST_FRAMEWORK` + `SIMPLE_JWT` | `base.py:325-403` | `JWT` `ACCESS 30m REFRESH 30d`, `SIGNING_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY` (dedicated key), throttles `anon 100/h auth 30/m` |
| `SPECTACULAR ENUM_NAME_OVERRIDES` | `base.py:413` | Stable names for `UserStatusEnum/OrderStatusEnum/LocationTypeEnum/OTPTypeEnum` to avoid OpenAPI collisions |
| `CORS / SECURITY` | `base.py:425-440` | `CORS_ALLOW_CREDENTIALS`, env-driven origins, `SECURE_* = False if TESTING else getenv()` |
| `SOCIALACCOUNT_*` | `base.py:237-250` | Opt-in `allauth` adapter `accounts.auth.adapters.SocialAccountAdapter` + providers dict commented |
| `GOOGLE_APPLICATION_CREDENTIALS` | `base.py:470` | `firebase-adminsdk.json` fallback for FCM `notifications/` |
| `ASGI_APPLICATION` | `base.py:474` | `project.asgi.application` for future Channels |

---

## Environment-Specific Overrides

### local.py
- `ALLOWED_HOSTS=*`, `SECURE_*=False`
- Conditional CORS: `if _cors_env is not None: CORS_ALLOWED_ORIGINS = ...` (respects `.env` without hardcoding) — REUSE pattern
- `CELERY_ALWAYS_EAGER=True`
- Debug toolbar try-import

### production.py
- Wrapped in `if not TESTING:` (tests run plain HTTP)
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO","https")` for nginx TLS termination
- HSTS ramp comment: `0 → 300 → 86400 → 31536000` after TLS confirmed; `SECURE_HSTS_SECONDS = int(os.getenv(..., "31536000"))`
- Fail-fast: `if not _allowed: raise ImproperlyConfigured("ALLOWED_HOSTS must be set")`
- `LOGGING` downgraded to `WARNING`

---

## Project URLs & Routing (project/urls.py)

| Endpoint | Purpose | REUSE |
|----------|---------|-------|
| `api/v1/users/` | `accounts.urls` — login/register/verify/OTP/social | generic |
| `api/v1/notifications/` | `notifications.urls` — inbox + devices FCM | generic |
| `api/v1/contacts/` | `contacts.urls` — public message + singleton info | generic |
| `api/v1/compliance/` | `compliance.urls` — FAQ + legal docs | generic |
| `api/schema/`, `swagger/`, `redoc/` | Spectacular — `SchemaView(exclude=True)` hides schema | REUSE |
| `health/` | `lambda healthy` for LB | keep |
| `admin/` + `i18n/` | `i18n_patterns` locale-prefixed | keep |
| `markdownx/` | `markdownx.urls` for `MarkdownAdminMixin` | REUSE |
| `accounts/social/signup/` | JSON `404` stub prevents `NoReverseMatch` 500 when allauth auto-signup blocked | REUSE if allauth |
| `__debug__/` | Debug toolbar (DEBUG only) | keep |

Home `""` → `HomeView` redirect to `admin:index` (`dashboard.views`).

---

## Deployment

| File | Role |
|------|------|
| `project/wsgi.py` | Gunicorn entry (`docker-compose.prod.yml` `gunicorn --workers 4 --max-requests 1000`) |
| `project/asgi.py` | ASGI entry (Channels-ready) |
| `project/routing.py` | Stub for WebSockets |
| `docker-compose.yml` | Dev base: `runserver 0.0.0.0:8000`, ports open |
| `docker-compose.prod.yml` | Prod override: `ports: !reset []` for DB/Redis/Flower, `gunicorn`, `concurrency 4`, `443` + certbot volumes |
| `nginx.conf` | Dev `client_max_body_size 100M` (Excel imports), proxy `django:8000` |
| `nginx.prod.conf` | Prod dual `80→443` redirect + `/.well-known/acme-challenge/` for Let's Encrypt, `api.` + `www` servers |
| `.dockerignore` | Prevents baking `venv/.env/google-services.json` |
| `entrypoint.sh` | Role-aware `CONTAINER_ROLE:-web` → `migrate+collectstatic+createsuperuser` only on `web` |

First deploy cert issuance:
```bash
docker compose run --rm certbot certbot certonly --webroot -w /var/www/certbot -d example.com -d www.example.com -d api.example.com
```

---

## Environment Variables (.env.example)

Updated with REUSE sections:
- `BUSINESS_TIME_ZONE`, `JWT_SECRET_KEY` (dedicated), `GOOGLE_OAUTH_*`, `FACEBOOK_*`, `GOOGLE_APPLICATION_CREDENTIALS`, `DOMAIN`, `TESTING` (auto via `sys.argv`)
- See `.env.example` comments — uncomment OAuth/FCM sections when needed

---

## Testing

No `testing.py`; use `TESTING=True`:
```bash
DJANGO_ENVIRONMENT=testing python manage.py test  # uses SQLite, eager Celery, dummy cache
# or simply
python manage.py test  # auto-detected via "test" in sys.argv
```

Optimizations: in-memory SQLite (10-100x), migrations disabled via SQLite path, MD5 hasher not configured but can be added, synchronous Celery, dummy cache when `TESTING`.

---

## Migration from Old Guide

| Before (guide claim) | After (actual) |
|---|---|
| `components/*.py` 13 files | Monolithic `base.py` + env overlays (clearer, fewer merges) |
| `testing.py` | `TESTING` flag + `sys.argv` detection in `base.py` |
| `channels.py` assumed | `routing.py` stub (Channels opt-in) |
| Only `accounts` documented | Now `notifications/compliance/contacts` documented + `docs/examples/` patterns |

---

## Best Practices

1. **Never commit `.env`** — `.gitignore` + `.dockerignore` already cover it
2. **Use `or SECRET_KEY` fallback for `JWT_SECRET_KEY`** — never commit `JWT_SECRET_KEY`
3. **Keep `TESTING` guards on `SECURE_*`** — `False if TESTING else getenv()`
4. **Ramp HSTS** `0→300→86400→31536000` after confirming TLS
5. **Replace `example.com` in `nginx.prod.conf` + `DOMAIN` env** before first prod deploy
6. **Document new settings with `# REUSE:`** comment indicating portability

---

## Removal — How to Remove PostgreSQL and Redis

### Drop PostgreSQL (use SQLite everywhere)

> All apps use generic `UUIDModel` + `TimestampedModel` — they run on SQLite already when `TESTING=True`. Switching prod to SQLite is a config change, not a code change.

1. **Settings `project/settings/base.py:121-146`** → replace `if not TESTING: DATABASES = {postgres}` block with single SQLite:
   ```python
   DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
   ```
   Delete `DB_ENGINE/DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/CONN_MAX_AGE/OPTIONS` env reads.
2. **Docker `docker-compose.yml:21`** → delete `db` service (7 lines: `pgvector/pgvector:pg17`, `postgres_data` volume, `healthcheck pg_isready`), delete `postgres_data` from `volumes`, remove `db` from every `depends_on` (`web`, `celery_worker`, `celery_beat`). `docker-compose.prod.yml` → delete `db: ports: !reset []`.
3. **Dockerfile `Dockerfile:13`** → delete `libpq-dev` from `apt-get install` (only needed for `psycopg`).
4. **Requirements `requirements.txt:67`** → delete `psycopg==3.2.1` (keep if you might re-add later).
5. **Env `.env.example:20-25`** → delete `DB_*` lines (keep `DB_NAME` if you keep SQLite path).
6. **Migrations** `python manage.py migrate` works on SQLite — but `pgvector` extension `CREATE EXTENSION vector` will fail if you had vector fields; this starter has none, so no change.
7. **Check** `make check && python manage.py dbshell` — should open SQLite.

### Drop Redis Caching (use local memory / dummy)

> `CACHES` is `django_redis` + `SESSION_ENGINE cache`. Live logs `dashboard/live_logs.py` falls back to in-memory `deque` when Redis is down — it stays live without Redis.

1. **Settings `project/settings/base.py:292-310`** → replace `if not TESTING: CACHES = {django_redis}` with dummy/local:
   ```python
   CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
   # or Dummy: "django.core.cache.backends.dummy.DummyCache"
   ```
   Change `SESSION_ENGINE = "django.contrib.sessions.backends.cache"` → `"django.contrib.sessions.backends.db"` (DB sessions, no Redis).
2. **Settings `project/settings/base.py:313-343` Celery** → already handled in `Celery guide.md` removal (delete `CELERY_BROKER_URL/RESULT_BACKEND` or point to `memory://` for eager only).
3. **Docker `docker-compose.yml:49`** → delete `redis` service (7 lines: `redis:7-alpine`, `redis_data` volume, `healthcheck redis-cli -a`), delete `redis_data` from `volumes`, remove `redis` from every `depends_on` (`web`, `celery_*`). `docker-compose.prod.yml` → delete `redis: ports: !reset []`.
4. **Requirements `requirements.txt:60-63`** → delete `redis==4.6.0`, `django-redis==5.4.0`, `msgpack==1.1.2` (keep `celery` if you keep Celery with `memory` broker — but Celery without Redis needs `CELERY_TASK_ALWAYS_EAGER=True`).
5. **Live logs** No change — `dashboard/live_logs.py` tries `get_redis_connection("default").lpush` and falls back to `deque` if `Exception` → works without Redis (single-process only, as documented).
6. **Common** `common/decorators.py:6 cache_result`, `common/pagination.py:13 OptimizedPagination`, `common/middleware.py:175 RateLimit cache.get/set`, `common/permissions.py:11 RateLimitPermission cache`, `common/views.py:462 CachedViewSet cache_page`, `notifications/tasks.py:171-186 get_unread_count/delete/set` — all degrade to `LocMemCache`/`DummyCache` (e.g. `CachedViewSet` no-op) — no code change, just `CACHES` switch.
7. **Env `.env.example:32-34`** → delete `REDIS_HOST/PORT/PASSWORD` (`33-36`), `REDIS_URL`, `CACHE_URL`, `CELERY_BROKER_URL` (or keep `CACHE_URL=locmem://` comment).
7. **Check** `make check && docker compose config > /dev/null`.

### Drop Both (pure SQLite + LocMemCache + Eager Celery)

Combine above: `DATABASES` → SQLite, `CACHES` → `LocMemCache`, `CELERY_TASK_ALWAYS_EAGER=True` in `base.py` (already when `TESTING`), delete `db` + `redis` services from both compose files, delete `psycopg` + `redis` + `django-redis` + `msgpack` + `flower`/`celery` if desired. `make test` still passes (`TESTING` SQLite path). No code change in `common/models.py` — `UUIDModel` works on SQLite.
