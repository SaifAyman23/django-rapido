# Docker Production Guide (REUSE)

## Compose Layers

- `docker-compose.yml` — **base** (dev): `runserver 0.0.0.0:8000`, ports `5432/6379/5555/80` open, hot-reload volumes `.:/app`
- `docker-compose.prod.yml` — **override** (prod): `ports: !reset []` hides DB/Redis/Flower, swaps `runserver → gunicorn 4 workers --max-requests 1000 --worker-tmp-dir /dev/shm`, `celery --concurrency=4`, `443:443` + certbot volumes

```bash
# Dev
docker compose up -d --build

# Prod (layered)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Services

| Service | Image | Command | Volumes | Ports dev → prod |
|---------|-------|---------|---------|------------------|
| `db` | `pgvector/pgvector:pg17` | `pg_isready` healthcheck 5s | `postgres_data:/var/lib/postgresql/data` | `5432:5432` → `!reset` |
| `redis` | `redis:7-alpine` | `redis-server --requirepass ... --appendonly yes`, healthcheck `redis-cli -a ... incr ping` 10s | `redis_data:/data` | `6379:6379` → `!reset` |
| `web` | `Dockerfile` | dev `runserver` / prod `gunicorn project.wsgi:application --bind 0.0.0.0:8000 --workers 4` | `.:/app` + `static_volume/media_volume/logs` → prod only `static/media` | `80` via nginx |
| `celery_worker` | same | `celery -A project worker --autoscale=10,4` → prod `--concurrency=4 --max-tasks-per-child=100` | `.:/app` → prod `!reset` | none |
| `celery_beat` | same | `beat --scheduler django_celery_beat.schedulers:DatabaseScheduler` | `.:/app` → `!reset` | none |
| `flower` | same | `flower --port=5555 --basic_auth` → prod `--persistent --db=/data/flower.db` `user 0:0` | none → prod `flower_data:/data` | `5555:5555` → prod `!reset` (proxy via nginx if needed) |
| `nginx` | `nginx:alpine` | `nginx.prod.conf` in prod, `nginx.conf` in dev (`client_max_body_size 100M`) | `static/media` + `nginx.conf` → prod `certbot/www + /etc/letsencrypt` | `80:80` → `80+443` |
| `certbot` | `certbot/certbot` | `trap exit TERM; while :; do certbot renew; sleep 12h & wait ${!}; done` (prod only) | `certbot/conf + www` | none |

## Dockerfile (python:3.13-slim)

- `gcc libpq-dev netcat-openbsd curl nodejs npm`, `useradd appuser 1000`, `npm install` (Tailwind), `pip install -r requirements.txt`, `collectstatic --noinput`, `chown appuser`, `USER appuser`, `gunicorn` default CMD, `ENTRYPOINT ["/entrypoint.sh"]`
- REUSE: remove `nodejs/npm` if no frontend build

## Entrypoint (entrypoint.sh:6)

```sh
if [ "${CONTAINER_ROLE:-web}" = "web" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    python manage.py createsuperuser --noinput || true
fi
exec "$@"
```

`CONTAINER_ROLE` set via `docker-compose.yml:96` per service; only `web` migrates.

## Nginx

- `nginx.conf` (dev): single `listen 80`, `client_max_body_size 100M` (Excel imports), `upstream django web:8000`, `/static/` `30d immutable`, `/media/` `7d`, `/health/` `200 healthy`, proxy `X-Forwarded-*`
- `nginx.prod.conf` (prod): dual `80→443` redirects + `/.well-known/acme-challenge/` root `/var/www/certbot` for Let's Encrypt, separate `api.example.com` + `www.example.com` servers, `ssl_certificate /etc/letsencrypt/live/.../fullchain.pem`, `X-Forwarded-Port 443`

## First Deploy

```bash
cp .env.example .env  # set DJANGO_ENVIRONMENT=production, SECRET_KEY, DOMAIN, DB_PASSWORD
# Issue certs before full up (nginx needs certs for 443)
docker compose run --rm certbot certbot certonly --webroot -w /var/www/certbot -d example.com -d www.example.com -d api.example.com
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## .dockerignore

Prevents baking `venv/.git/media/staticfiles/logs/.env/*firebase*.json` — all REUSE commented.

---

## Removal — How to Remove This Feature

> Docker is the deployment method, not a feature — removal means switching to manual Systemd/Gunicorn.

### Drop Docker Entirely (run bare metal)

1. **Delete files** `docker-compose.yml`, `docker-compose.prod.yml`, `Dockerfile`, `.dockerignore`, `nginx.conf`, `nginx.prod.conf`, `entrypoint.sh` (7 files).
2. **Settings** keep `project/settings/base.py` as is — `TESTING` SQLite fallback still works; `docker-compose` env vars (`CACHE_URL`, `CELERY_BROKER_URL`) can point to `localhost` instead of `redis`/`db` hosts.
3. **Deploy** Systemd + Gunicorn: `gunicorn project.wsgi:application --bind 0.0.0.0:8000 --workers 4` + Nginx on host (copy `nginx.conf` directives). No `web-sse` isolation — SSE runs on same `gunicorn --worker-class sync` (live logs still works but blocks one worker; use `gevent` if you keep SSE).
4. **Check** `make check --deploy` — no Docker needed.

### Keep Docker, Drop Prod Override Only

- Delete `docker-compose.prod.yml` + `nginx.prod.conf` + `certbot` service, keep `docker-compose.yml` dev base. `web-sse` isolation and `443` are prod-only — dev `runserver` + single `nginx:80` still works for `live_logs` via `nginx.conf` `proxy_buffering off` location.
- Keep `Dockerfile` + `entrypoint.sh` (`migrate/collectstatic/createsuperuser`).

### Drop PostgreSQL (keep Docker, use SQLite)

1. **Compose** `docker-compose.yml:21` → delete `db` service (`image pgvector/pgvector:pg17`, `environment POSTGRES_DB/USER/PASSWORD/INITDB_ARGS`, `ports 5432:5432`, `volumes postgres_data:/var/lib/postgresql/data`, `healthcheck pg_isready 5s`), delete `postgres_data` from `volumes:`, remove `db` from `depends_on` (`web`, `celery_worker`, `celery_beat` + `web-sse` if present). `docker-compose.prod.yml` → delete `db: ports: !reset []` (5 lines).
2. **Dockerfile** `Dockerfile:13` → delete `libpq-dev` from `apt-get install gcc libpq-dev netcat-openbsd curl nodejs npm` (only for `psycopg`).
3. **Settings** `project/settings/base.py:121-146` → `DATABASES` → SQLite single line (see Settings guide). This also removes `CONN_MAX_AGE 600` + `OPTIONS connect_timeout 10`.
4. **Requirements** `requirements.txt:67` → `psycopg==3.2.1`. Keep `common/models.py` — `UUIDModel` uses `UUIDField` which works on SQLite (no `pgvector` extension needed; this starter has no vector fields).
5. **Env** `.env.example:20-25` → delete `DB_ENGINE/DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT`. `DB_HOST` `db` → `localhost` not needed for SQLite.

### Drop Redis (keep Docker, use LocMemCache)

1. **Compose** `docker-compose.yml:49` → delete `redis` service (`image redis:7-alpine`, `command --requirepass`, `ports 6379:6379`, `volumes redis_data:/data`, `healthcheck redis-cli -a ... 10s`), delete `redis_data` from `volumes:`, remove `redis` from `depends_on` (`web`, `celery_worker`, `celery_beat`, `web-sse`). `docker-compose.prod.yml` → delete `redis: ports: !reset []`.
2. **Settings** `project/settings/base.py:292-310` → `CACHES` `django_redis` + `SESSION_ENGINE cache` → `LocMemCache` + `SESSION_ENGINE db` (see Settings guide). Live logs `dashboard/live_logs.py:24` falls back to `deque` (no Redis needed, single-process only). `notifications:unread` cache `notifications/tasks.py:171` degrades to local per worker.
3. **Requirements** `requirements.txt:60-63` → `redis==4.6.0`, `django-redis==5.4.0`, `msgpack==1.1.2`. Keep `celery` only if `CELERY_ALWAYS_EAGER=True` else delete per Celery guide.
4. **Env** `.env.example:32-38` → delete `REDIS_HOST/PORT/PASSWORD`, `REDIS_URL`, `CACHE_URL` (`redis://.../1`), `CELERY_BROKER_URL/RESULT_BACKEND` (`redis://.../0`) or replace `CACHE_URL=locmem://`.
5. **Common** `common/decorators.py:6 cache_result`, `common/pagination.py:13 OptimizedPagination`, `common/middleware.py:175 RateLimit cache.get/set`, `common/permissions.py:11 RateLimitPermission cache`, `common/views.py:462 CachedViewSet cache_page` — all degrade to local cache, no code change.

After removal, run `make check && docker compose config > /dev/null && python manage.py check --deploy`.
