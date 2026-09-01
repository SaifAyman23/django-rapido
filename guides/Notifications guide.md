# Notifications Guide — FCM Push + In-App Inbox (REUSE)

## Overview

Generic engine from ras-elbar-go — no order/deliveryman filtering. Works for any domain.

```
Event → create_notification_task.delay(user_id, type, title, body, related_id, related_type)
      → Notification DB row + invalidate cache + _dispatch_push_notification → send_multicast (500 batch) → cleanup invalid tokens
```

## Models (notifications/models.py)

```python
class NotificationType(models.TextChoices):
    WELCOME = "welcome", "Welcome"
    GENERIC = "generic", "Generic"
    # Add your domain: ORDER_COMPLETED, COMMENT_CREATED, etc.

class Notification(TimestampedModel, UUIDModel):
    user = FK(User, related_name="notifications")
    type = CharField(30, choices=NotificationType)
    title = CharField(255)
    body = TextField
    related_object_id = UUIDField(null/blank)  # REUSE: generic FK to any object
    related_object_type = CharField(Generic)
    is_read = BooleanField(db_index=True)
    # Indexes: (user, is_read, -created_at), (user, type, -created_at)

class Device(TimestampedModel, UUIDModel):
    user = FK(User, related_name="devices")
    token = TextField(unique=True)  # FCM registration token
    device_uuid = CharField(255)  # stable per install: uuid.v4 in secure storage
    platform = CharField(choices=DevicePlatform.android/ios/web)
    is_active, notifications_enabled, last_seen_at, last_token_refresh_at
    # UniqueConstraint(user, device_uuid)
```

## Services

```python
def should_notify(user) -> bool:
    return user.is_active and getattr(user, "notifications_enabled", True)
```

Guard before every send.

## Tasks (notifications/tasks.py)

- `send_multicast_notifications_task(tokens, title, body, data)` — batches 500 via `messaging.MulticastMessage`, retries, collects `failed_tokens` → `clean_up_invalid_tokens.delay`
- `clean_up_invalid_tokens(failed_tokens)` — deletes stale `Device` rows (app re-registers)
- `create_notification_task(user_id, notification_type, title, body, related_id, related_type)` — `should_notify` guard, creates DB row, `cache.delete(f"notifications:unread:{user_id}")`, `_dispatch_push_notification`
- `cleanup_old_notifications()` — deletes `created_at < now()-90d` (weekly Beat)
- `notify_welcome(user_id)` — example pattern, copy per event

FCM requires `firebase-admin` + `GOOGLE_APPLICATION_CREDENTIALS` (`firebase-adminsdk.json`). If not installed, tasks log warning and return `"FCM not configured"`.

## Device Lifecycle

```
POST /api/v1/notifications/devices/  {token, device_uuid, platform}  → update_or_create(user, device_uuid)
POST /api/v1/notifications/devices/unregister/  {device_uuid} → is_active=False
Logout → Device.objects.filter(user=request.user).update(is_active=False)  # in accounts/views.py logout
```

Frontend: store `device_uuid = uuid.v4()` in secure storage, regenerate only on reinstall; refresh `token` on `onTokenRefresh`.

## Views & URLs

```python
# notifications/views.py
class NotificationViewSet(BaseViewSet):
    get_queryset() → filter(user=request.user).order_by("-created_at")
    list() → adds unread_count via get_unread_count(cache 5m)
    retrieve() → marks is_read=True
    mark_read PATCH /notifications/{id}/read/
    mark_all_read POST /notifications/read-all/

class DeviceViewSet(BaseViewSet):
    create POST /devices/ → upsert
    unregister POST /devices/unregister/
```

```python
# notifications/urls.py
router.register(r"", NotificationViewSet)
router.register(r"devices", DeviceViewSet)
# project/urls.py: path(f'{api_prefix}/notifications/', include('notifications.urls'))
```

## Caching

```python
def get_unread_count(user_id): cache.get(f"notifications:unread:{user_id}") or count is_read=False → cache.set 300s
def _invalidate_unread_count_cache(user_id): cache.delete(...)
```

Called on create/mark_read.

## Setup

1. `pip install firebase-admin` (already in `requirements.txt:10`)
2. `.env`: `GOOGLE_APPLICATION_CREDENTIALS=./firebase-adminsdk.json`
3. `INSTALLED_APPS += ["notifications"]` (already)
4. `python manage.py makemigrations notifications && migrate`
5. Beat: `cleanup_old_notifications` weekly (add to `CELERY_BEAT_SCHEDULE`)

See `docs/examples/state_machine.md` for event dispatch pattern.

---

## Removal — How to Remove This Feature

> Fully decoupled — no other app imports `notifications.models`. Safe to delete entirely.

### Full Removal (drop FCM + inbox)

1. **Settings `project/settings/base.py`** → delete `notifications` from `INSTALLED_APPS` `base.py:62` + delete `GOOGLE_APPLICATION_CREDENTIALS` commented block `base.py:506-511` (`os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ...)`), keep `CACHES` (`base.py:292-310` `CACHE_URL .env.example:34` `redis://.../1`) **only if** you keep other cache features (`notifications:unread:{user_id}` cache 300s for `get_unread_count` `notifications/tasks.py:180-186` + `_invalidate_unread_count_cache` `notifications/tasks.py:171` uses `django.core.cache` via `CACHE_URL` — if you drop Redis entirely, switch to `LocMemCache` per `Settings guide.md` Redis removal).
2. **URLs `project/urls.py`** → delete `path(f'{api_prefix}/notifications/', include('notifications.urls'))` + `import notifications` (if any).
3. **Delete app** `notifications/` entire folder (8 files: `models.py`, `services.py`, `tasks.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`, `__init__.py`).
4. **Admin** `project/settings/unfold_config.py` → delete `Notifications` collapsible group (2 items: `User Notifications` + `Devices`).
5. **Common** No `common/` import of `notifications` exists (verified `common/` grep — `cache` in `common/decorators.py 6 cache_result`, `common/pagination.py 13`, `common/middleware.py 175 RateLimit cache.get/set`, `common/permissions.py 11 cache` are generic, not notifications-specific — keep). Notifications-specific cache is `notifications/tasks.py:171,178` `cache.delete/get/set f"notifications:unread:{user_id}"` — deleted with app.
6. **Accounts** `accounts/views.py` → delete `Device` usage if present (logout `Device.objects.filter(user=request.user).update(is_active=False)` + `accounts/tasks.py:67 from accounts.notifications import should_notify` guard) — keep if you already removed `Device` model. `common/helpers.py` has no notification import.
7. **Requirements** `requirements.txt:10` → delete `firebase-admin==7.4.0` (+ `requests` transitive if not needed elsewhere — keep if `accounts` social or other HTTP).
8. **Env** `.env.example:85` → delete `# GOOGLE_APPLICATION_CREDENTIALS=./firebase-adminsdk.json` + if you drop Redis cache entirely, also delete `CACHE_URL` `.env.example:34` (`redis://:redis_password@redis:6379/1`) or replace with `locmem://` (see Settings guide Redis removal). Keep `REDIS_*` + `CELERY_BROKER_URL` only if Celery stays.
9. **DB** `python manage.py migrate` will not delete tables — run `python manage.py migrate notifications zero` **before** deleting folder, or manually `DROP TABLE notifications_notification, notifications_device`.
10. **Check** `make check && docker compose config > /dev/null` — ensure no `ModuleNotFoundError: notifications`.

### Partial — Keep Inbox, Drop FCM Push Only

- Keep `notifications/models.py` + `views.py` + `admin.py` (inbox still works).
- In `notifications/tasks.py` → delete `send_multicast_notifications_task` + `clean_up_invalid_tokens` + `_dispatch_push_notification`, keep `create_notification_task` but remove the `_dispatch_push_notification` call (keep DB row + cache invalidate only).
- Keep `Device` model only if you need device registry for other push (e.g. APNS) — else delete `Device` model and `DeviceViewSet`.

After removal, run `make check-format && make test`.
