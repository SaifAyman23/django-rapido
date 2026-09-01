# Celery Guide — Tasks, Beat, Flower (REUSE)

## Setup

```python
# project/celery.py — already wired
from celery import Celery
app = Celery("project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# project/settings/base.py
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://:redis_password@redis:6379/0")
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # fetch one at a time
CELERY_TASK_ACKS_LATE = True
CELERY_BROKER_HEARTBEAT = 120
CELERY_TASK_TIME_LIMIT = 1800

# Dev: CELERY_TASK_ALWAYS_EAGER=True in local.py / TESTING
```

Services: `celery_worker --autoscale=10,4` dev / `--concurrency=4` prod, `celery_beat --scheduler django_celery_beat.schedulers:DatabaseScheduler`, `flower :5555 --basic_auth`.

## Task Structure (bind + idempotent + should_notify guard)

```python
from celery import shared_task
from django.contrib.auth import get_user_model

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_order_status(self, user_id: str, order_id: str, status: str):
    from notifications.services import should_notify
    User = get_user_model()
    user = User.objects.get(id=user_id)
    if not should_notify(user):
        return {"status": "skipped"}
    try:
        send_fcm(user, f"Order {status}", order_id)
    except Exception as exc:
        raise self.retry(exc=exc)
    return {"status": "sent"}
```

Rules:
- `bind=True` for `self.retry`
- Idempotent — running twice same result
- Small — one task = one job
- Import models inside task (Django context)
- Every `notify_*` calls `should_notify()` first

## Accounts Tasks (accounts/tasks.py)

- `send_verification_email(user_id, email, otp)` — HTML OTP, 3 retries 60s
- `notify_welcome_email(user_id)` — checks `should_notify`
- `cleanup_expired_sessions()` — deletes `expire_date < now()`

## Notifications Tasks (notifications/tasks.py)

- `send_multicast_notifications_task(tokens, title, body, data)` — batches 500 via `messaging.MulticastMessage`, collects `failed_tokens` → `clean_up_invalid_tokens.delay`
- `clean_up_invalid_tokens(failed_tokens)` — deletes `Device` with stale tokens
- `create_notification_task(user_id, type, title, body, related_id, related_type)` — guard, create DB `Notification`, invalidate `notifications:unread:{user_id}`, `_dispatch_push_notification`
- `cleanup_old_notifications()` — deletes `created_at < now()-90d`
- `notify_welcome(user_id)` — example pattern, copy per event

## Beat Schedule (project/settings/base.py)

```python
CELERY_BEAT_SCHEDULE = {
    "scan-stale-objects": {"task": "myapp.tasks.scan_stale_objects", "schedule": 60},
    "cleanup-old-notifications": {"task": "notifications.tasks.cleanup_old_notifications", "schedule": 60*60*24*7},
}
# Managed via admin: PeriodicTask / Crontab / Interval (unfold_config sidebar Celery Tasks)
```

## Running Locally Without Docker

```bash
redis-server
celery -A project worker -l info
celery -A project beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
celery -A project flower --port=5555
```

---

## Removal — How to Remove This Feature

> Fully optional — **live logs** and **notifications** degrade gracefully to fallback `deque` / direct send, but Celery is the core async engine.

### Full Removal (drop Celery + Beat + Flower entirely)

1. **Settings `project/settings/base.py`** → delete entire `Celery configuration` block `base.py:313-343` (`CELERY_BROKER_URL .env:43`, `CELERY_RESULT_BACKEND .env:44`, `CELERY_TIMEZONE .env:45`, `CELERY_TASK_TIME_LIMIT .env:47`, `CELERY_* HEARTBEAT/PREFETCH/ACKS_LATE`, `FLOWER_USER/PASSWORD .env:121-122`, `CELERY_BEAT_SCHEDULE` `base.py:340` + `common/constants.py:358 CELERY_TIMEOUT/359 MAX_RETRIES` if unused). **Env** also delete `.env.example:34-38 REDIS_HOST/PORT/PASSWORD/REDIS_URL/CACHE_URL`, `43-47 CELERY_*`, `121-122 FLOWER_*` (or keep `REDIS_*`/`CACHE_URL` if you keep Redis cache for other apps).
2. **Tasks** delete every `tasks.py` file: `accounts/tasks.py`, `notifications/tasks.py`, `compliance`/`contacts` if they use tasks. Or keep `tasks.py` but make functions synchronous (remove `@shared_task`, call directly).
3. **Helpers** `accounts/helpers.py create_and_send_otp` → change `transaction.on_commit(lambda: create_and_send_otp(user))` to direct `create_and_send_otp(user)` + `send_verification_email(user.id, ...)` (not `.delay()`).
4. **Live logs** `dashboard/live_logs.py` fallback already handles no-Redis/No-Celery (`try: get_redis_connection else deque`), so it still works sync.
5. **Docker `docker-compose.yml:115`** → delete `celery_worker`, `celery_beat`, `flower` services (3 services). `docker-compose.prod.yml` → delete same 3 services + `flower_data` volume.
6. **Admin** `project/settings/unfold_config.py` → delete `Celery Tasks` group (4 items: Periodic Tasks/Crontabs/Intervals/Clocked).
7. **Requirements `requirements.txt:30-54`** → delete `celery 5.4.0` + `kombu/billiard/vine/amqp/click` + `django-celery-beat/results` + `django-timezone-field/cron_descriptor/tzdata/tzlocal` + `flower`.
8. **Check** `make check && docker compose config > /dev/null` — ensure no `ModuleNotFoundError: celery`.

### Partial — Keep Celery, Drop Beat/Flower Only

- Keep `celery_worker` + `CELERY_*` settings, delete only `celery_beat` service + `django-celery-beat/results` + `FLOWER_*` + `flight` (`flower` service). Live logs + OTP still use `delay()`.
