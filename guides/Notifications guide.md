# Notifications Guide — FCM Push + In-App Inbox — Django Rapido V2.0

> **Brand:** Django Rapido V2.0 — Generic, reusable, project-agnostic.  
> **Scope:** Firebase Cloud Messaging (FCM) push + persistent in-app inbox. No WebSockets — all realtime via FCM.  
> **Decoupling:** No other app imports `notifications.models`. Safe to keep, extend, or delete entirely.

## Table of Contents

1. [What It Offers / When to Skip](#1-what-it-offers--when-to-skip)
2. [Architecture & How It Works](#2-architecture--how-it-works)
3. [File Map — Every Piece file:line](#3-file-map--every-piece-fileline)
4. [Models — Notification Inbox + Device Registry](#4-models--notification-inbox--device-registry)
5. [Services — should_notify Guard](#5-services--should_notify-guard)
6. [Tasks — FCM Batch, Dispatch, Cache, Cleanup](#6-tasks--fcm-batch-dispatch-cache-cleanup)
7. [Device Lifecycle — Register / Refresh / Unregister / Logout](#7-device-lifecycle--register--refresh--unregister--logout)
8. [Views & URLs — Inbox + Device Registry](#8-views--urls--inbox--device-registry)
9. [Serializers](#9-serializers)
10. [Admin — Unfold Inbox + Devices](#10-admin--unfold-inbox--devices)
11. [Caching — Unread Count (5 min)](#11-caching--unread-count-5-min)
12. [How to Use — Send a Notification (Copy-Paste)](#12-how-to-use--send-a-notification-copy-paste)
13. [Setup From Scratch — Zero to Current State](#13-setup-from-scratch--zero-to-current-state)
14. [How to Adjust / Enhance](#14-how-to-adjust--enhance)
15. [Tradeoffs](#15-tradeoffs)
16. [Removal — Full and Partial](#16-removal--full-and-partial)
17. [Verification & Troubleshooting](#17-verification--troubleshooting)

---

## 1. What It Offers / When to Skip

### What It Offers

| Capability | Detail |
|---|---|
| **Dual channel** | Every event creates a persistent DB row (`Notification`) for in-app inbox + optionally fires an FCM push to all active devices. Users who miss the push still see the inbox. |
| **Generic / project-agnostic** | `NotificationType` + `RelatedObjectType` are `TextChoices` you extend. `related_object_id` (`UUIDField`) + `related_object_type` (`CharField`) point at any domain object without FK coupling — `notifications/models.py:40-68`. |
| **Device registry** | One row per `(user, device_uuid)` with `UniqueConstraint` `notifications/models.py:110`, `token` unique `notifications/models.py:85`. Upsert on `device_uuid`, stable across token refreshes. Metadata: `platform`, `device_name/model`, `os_version`, `app_version`, `language`, `timezone` `notifications/models.py:87-93`. |
| **Multicast batch 500** | `FCM_BATCH_LIMIT = 500` `notifications/tasks.py:36` — slices token list and sends `messaging.MulticastMessage` per batch `notifications/tasks.py:52-58` via `messaging.send_each_for_multicast` `notifications/tasks.py:60`. |
| **Stale token cleanup** | Failed tokens per batch collected `notifications/tasks.py:64-66` → `clean_up_invalid_tokens.delay(all_failed_tokens)` `notifications/tasks.py:72` → `Device.objects.filter(token__in=failed_tokens).delete()` `notifications/tasks.py:82`. App re-registers on next launch. |
| **Preference guard** | `should_notify(user)` checks `user.is_active` + `notifications_enabled` `notifications/services.py:14-18` before DB row and before push. Every `notify_*` task calls it. |
| **Cached unread count** | `get_unread_count(user_id)` caches `notifications:unread:{user_id}` for 300s `notifications/tasks.py:176-187`, invalidated on create `notifications/tasks.py:120` and on every read `notifications/views.py:44,54,63`. |
| **Automatic stale cleanup** | `cleanup_old_notifications()` deletes `created_at < now() - 90d` `notifications/tasks.py:128-136` — wire as weekly Celery Beat. |
| **Fully decoupled** | No other app imports `notifications.models`. Verified via codebase grep — `common/` has only generic cache uses. |

### When You DON'T Need It — Skip or Remove

| Scenario | Recommendation |
|---|---|
| **Web-only, no mobile/push** | Keep only the inbox (DB + views). Delete FCM: remove `send_multicast_notifications_task` + `clean_up_invalid_tokens` + `_dispatch_push_notification` from `notifications/tasks.py`, remove `firebase-admin` and `Device` if not needed. See [Partial Removal](#partial--keep-inbox-drop-fcm-push-only). |
| **Email-only notifications** | Use `common/helpers.py:233-290` `send_template_email` / `accounts/notifications.py:22-40` directly. FCM adds Firebase project overhead for no benefit. |
| **High-frequency realtime (< 2s)** | FCM is not WebSockets. For chat, live cursors, typing indicators — use WebSockets (Django Channels) or SSE. FCM delivery is best-effort (seconds to minutes, OS-batched). |
| **Prototype / internal tool** | Inbox without push is enough. Add FCM only when you have a shipped mobile app with token lifecycle. |
| **Strict data residency / no Google** | FCM routes through Google infrastructure. If that violates compliance, use inbox + email or self-hosted push (e.g. ntfy, APNS direct). |
| **You need per-topic broadcast** | Current design is **per-user multicast** (`Device.objects.filter(user=user, is_active=True ...)` `notifications/tasks.py:143-146`). For topic/fanout (e.g. "all sellers"), you need FCM Topics or a separate fanout task — see [Enhance: Topic Broadcast](#147-topic--fanout-broadcast). |

> **Rule of thumb:** If your app has authenticated users who benefit from "you have a new X" after they leave the app — you want this. If notifications are only needed while the user is on-screen — you don't.

---

## 2. Architecture & How It Works

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    Trigger Site                         │
                    │  view / service / signal / management command           │
                    │  create_notification_task.delay(user_id, type,          │
                    │      title, body, related_id, related_type)             │
                    └──────────────────────┬──────────────────────────────────┘
                                           │ Celery (or eager in tests/local)
                                           ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │         create_notification_task  tasks.py:86-125       │
                    │  1. User.objects.get(id=user_id)            :104       │
                    │  2. should_notify(user) guard               :108       │
                    │     → skip if inactive / notifications_enabled=False    │
                    │  3. Notification.objects.create(...)        :111-118   │
                    │  4. _invalidate_unread_count_cache(user_id) :120→170   │
                    │     cache.delete("notifications:unread:{user_id}")      │
                    │  5. _dispatch_push_notification(...)        :121→139   │
                    └──────────────────────┬──────────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────────────────┐
                    │  _dispatch_push_notification  tasks.py:139-151          │
                    │  Device.objects.filter(                                 │
                    │    user=user, is_active=True,                           │
                    │    notifications_enabled=True                            │
                    │  ).values_list("token", flat=True)  :143-146           │
                    │  if no tokens → return {"status":"no_tokens"} :148     │
                    │  else → send_multicast_notifications_task.delay(         │
                    │           tokens, title, body, data) :150               │
                    └──────────────────────┬──────────────────────────────────┘
                                           │ Celery
                                           ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  send_multicast_notifications_task  tasks.py:39-74      │
                    │  for i in range(0, len(tokens), 500):  :52  (FCM_BATCH │
                    │    batch = tokens[i:i+500]              :53  LIMIT=500)│
                    │    MulticastMessage(notification, data,  :54-58         │
                    │                     tokens=batch)                       │
                    │    response = send_each_for_multicast(msg) :60         │
                    │    success_count / failure_count         :61-62         │
                    │    collect failed_tokens per response    :63-66         │
                    │  if failed_tokens:                                      │
                    │    clean_up_invalid_tokens.delay(failed) :72            │
                    └──────────────────────┬──────────────────────────────────┘
                                           │ Celery
                                           ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │  clean_up_invalid_tokens  tasks.py:77-83                │
                    │  Device.objects.filter(token__in=failed).delete() :82  │
                    │  App re-registers token on next launch via              │
                    │  POST /api/v1/notifications/devices/  views.py:78-102  │
                    └─────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────────┐
  │  Inbox Read Path                                                         │
  │  GET /api/v1/notifications/          → NotificationViewSet.list :28-35   │
  │    super().list() + get_unread_count(user_id) :34  → cache 5 min         │
  │  GET /api/v1/notifications/{id}/     → retrieve :37-45 marks is_read     │
  │  PATCH /notifications/{id}/read/     → mark_read :47-56                  │
  │  POST /notifications/read-all/       → mark_all_read :58-65              │
  │  Each invalidates cache  tasks.py:170-173                                │
  └──────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────────┐
  │  Stale Cleanup (Beat Weekly)                                              │
  │  cleanup_old_notifications()  tasks.py:128-136                             │
  │    cutoff = now() - 90d  :131                                             │
  │    Notification.objects.filter(created_at__lt=cutoff).delete() :134      │
  └──────────────────────────────────────────────────────────────────────────┘
```

**Key invariants:**

- **Inbox is source of truth.** Push is best-effort; inbox is durable. Even if FCM is unconfigured (`HAS_FCM = False` `tasks.py:28-29`), the DB row is still created — push logs `warning` and returns `"FCM not configured"` `tasks.py:42-44`.
- **Token lifecycle is client-driven.** Backend never generates tokens. Client stores `device_uuid = uuid.v4()` in secure storage (regenerated only on reinstall) and upserts on every launch + on `onTokenRefresh`.
- **One device = one row.** `UniqueConstraint(user, device_uuid)` `models.py:110` + `token` unique `models.py:85`. `update_or_create(user, device_uuid)` `views.py:87-97` handles token rotation without duplicates.
- **Cache is per-user, TTL 300s.** `notifications:unread:{user_id}` `tasks.py:180` — `cache.get` → `count` → `cache.set(..., 300)` `tasks.py:181-186`. Invalidation on every write path.

---

## 3. File Map — Every Piece file:line

| File | Lines | What |
|---|---|---|
| `notifications/models.py:21-30` | `NotificationType` | `TextChoices` — `WELCOME`, `GENERIC` + commented domain examples. Extend here. |
| `notifications/models.py:33-38` | `RelatedObjectType` | `ORDER` / `USER` / `GENERIC` — extend per project. |
| `notifications/models.py:41-68` | `Notification` | `TimestampedModel + UUIDModel`, FK `user` `models.py:48`, `type/title/body` `49-51`, `related_object_id/type` `52-55`, `is_read` `56`, indexes `(user,is_read,-created_at)` + `(user,type,-created_at)` `61-64`, `__str__` `66-67`. |
| `notifications/models.py:70-73` | `DevicePlatform` | `android/ios/web`. |
| `notifications/models.py:76-114` | `Device` | `TimestampedModel + UUIDModel`, FK `user` `84`, `token` unique `85`, `device_uuid` `86`, `platform` `87`, metadata `88-93`, `notifications_enabled` `94`, `is_active` `95-97`, `last_seen_at/refresh_at` `98-99`, ordering + indexes + `UniqueConstraint(user, device_uuid)` `101-111`, `__str__` `113-114`. |
| `notifications/services.py:14-18` | `should_notify(user)` | Guard: `user.is_active` + `getattr(user, notifications_enabled, True)` `services.py:16-18`. |
| `notifications/services.py:1-7` | Module doc | `Wire: if not should_notify(user): skip send`. |
| `notifications/tasks.py:24-29` | `HAS_FCM` | `try: from firebase_admin import messaging` → `HAS_FCM True/False`. |
| `notifications/tasks.py:36` | `FCM_BATCH_LIMIT` | `500` — FCM hard limit. |
| `notifications/tasks.py:39-74` | `send_multicast_notifications_task` | Batch 500 `52-53`, `MulticastMessage` `54-58`, `send_each_for_multicast` `60`, success/failure counts `61-62`, collect `failed_tokens` `63-66`, `clean_up_invalid_tokens.delay` `72`, return summary `74`. |
| `notifications/tasks.py:77-83` | `clean_up_invalid_tokens` | `Device.objects.filter(token__in=failed_tokens).delete()` `82`. |
| `notifications/tasks.py:86-125` | `create_notification_task` | Main entry: `User.objects.get` `104`, `should_notify` guard `108`, `Notification.objects.create` `111-118`, `_invalidate_unread_count_cache` `120`, `_dispatch_push_notification` `121-123`, return `notification_id` `125`. |
| `notifications/tasks.py:128-136` | `cleanup_old_notifications` | `cutoff = now() - 90d` `131`, `filter(created_at__lt=cutoff).delete()` `134`. |
| `notifications/tasks.py:139-151` | `_dispatch_push_notification` | `Device.filter(user, is_active, notifications_enabled).values_list(token)` `143-146`, `send_multicast.delay` `150`. |
| `notifications/tasks.py:157-167` | `notify_welcome` | Example pattern — `should_notify` guard `164`, delegates to `create_notification_task.delay` `166`. Copy per event. |
| `notifications/tasks.py:170-173` | `_invalidate_unread_count_cache` | `cache.delete(f"notifications:unread:{user_id}")` `173`. |
| `notifications/tasks.py:176-187` | `get_unread_count` | `cache.get` `181` → `Notification.filter(user_id, is_read=False).count()` `185` → `cache.set(..., 300)` `186`. |
| `notifications/views.py:18-65` | `NotificationViewSet` | `IsAuthenticated` `22`, `filter(user=request.user).order_by(-created_at)` `24-26`, `list` + `unread_count` `28-35`, `retrieve` marks read `37-45`, `mark_read` `47-56`, `mark_all_read` `58-65`. |
| `notifications/views.py:68-111` | `DeviceViewSet` | `IsAuthenticated` `72`, `filter(user=request.user)` `74-76`, `create` upsert `78-102` (`token+device_uuid required` `80-85`, `update_or_create(user, device_uuid)` `87-97`, `is_active=True + last_seen_at/refresh_at=now()` `94-96`), `unregister` `104-111` (`filter(...).update(is_active=False)` `110`). |
| `notifications/serializers.py:11-26` | `NotificationSerializer` | `ModelSerializer` for `Notification`, fields `16-25`, `read_only id/created_at` `26`. |
| `notifications/serializers.py:29-44` | `DeviceSerializer` | `ModelSerializer` for `Device`, fields `34-43`, `read_only id/created_at` `44`. |
| `notifications/serializers.py:47-53` | `DeviceRegisterSerializer` | Explicit `token/device_uuid/platform/device_name` validation — not wired in viewset (view uses raw `request.data`), keep for docs/custom validation. |
| `notifications/urls.py:8-12` | Router | `router.register("", NotificationViewSet)` `9`, `router.register("devices", DeviceViewSet)` `10`, `path("", include(router.urls))` `12`. |
| `notifications/admin.py:10-14` | `NotificationAdmin` | `BaseAdmin`, `list_display [user,type,title,is_read,created_at]` `12`, `list_filter [type,is_read]` `13`, `search_fields [user__email,title,body]` `14`. |
| `notifications/admin.py:17-28` | `DeviceAdmin` | `BaseAdmin`, `list_display [user,platform,device_uuid,is_active,notifications_enabled,last_seen_at]` `19-26`, `list_filter [platform,is_active]` `27`, `search_fields [user__email,token,device_uuid]` `28`. |
| `project/settings/base.py:68` | `INSTALLED_APPS` | `"notifications"` — inbox + FCM. |
| `project/settings/base.py:303-315` | `CACHES` | `django_redis.cache.RedisCache`, `LOCATION = os.getenv("CACHE_URL", "redis://:redis_password@redis:6379/1")` `307`, `CONNECTION_POOL_KWARGS max_connections 50` `310`. Required for `notifications:unread:{user_id}` `tasks.py:180`. |
| `project/settings/base.py:322-340` | `CELERY_*` | Broker/result `redis://:redis_password@redis:6379/0` `323-324`, eager in tests `33-41` + `local.py:28-29`. |
| `project/settings/base.py:345-351` | `CELERY_BEAT_SCHEDULE` | Empty stub — add `cleanup_old_notifications` here (see Setup Step 8). |
| `project/settings/base.py:515-519` | `GOOGLE_APPLICATION_CREDENTIALS` | Commented `os.getenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.join(BASE_DIR, "firebase-adminsdk.json"))` `516-519` — uncomment when enabling FCM. |
| `project/urls.py:41-43` | URL mount | `path(f"{api_prefix}/notifications/", include("notifications.urls"))` `41-43` where `api_prefix = "api/v1"` `27`. Final routes: `/api/v1/notifications/` + `/api/v1/notifications/devices/`. |
| `project/settings/unfold_config.py:366-379` | Sidebar | `Notifications` collapsible group `366`, `User Notifications → admin:notifications_notification_changelist` `368-372`, `Devices → admin:notifications_device_changelist` `374-378`. |
| `.env.example:85` | Env | `# GOOGLE_APPLICATION_CREDENTIALS=./firebase-adminsdk.json` `85`. |
| `requirements.txt:11` | Dependency | `firebase-admin==7.4.0` `11` (+ transitive `requests` `72`). |
| `common/models.py:378-476` | `CustomUser` | `email USERNAME_FIELD` `438-440`, `is_verified/verified_at/status` `398-414` — `should_notify` checks `is_active` on this model. No `notifications_enabled` field on user — guard defaults to `True` via `getattr`. Add per-user toggle here if needed (see Enhance). |
| `accounts/notifications.py:43-51` | `should_notify` (alt) | Thin re-export variant checking `notification_preferences` dict (`email_enabled`). Different from `notifications/services.py:14-18` which checks `notifications_enabled` bool. Use `notifications.services.should_notify` for push; `accounts.notifications.should_notify` for email. |
| `accounts/views.py:292-306` | `logout` | Blacklists refresh token + `clear_token_cookies`. Current file does **not** deactivate `Device` — add if you want logout to mute push (see Device Lifecycle). |

---

## 4. Models — Notification Inbox + Device Registry

### Notification — `notifications/models.py:41-68`

```python
# notifications/models.py:21-38 — extend these first
class NotificationType(models.TextChoices):
    WELCOME = "welcome", _("Welcome")
    GENERIC = "generic", _("Generic")
    # Add per project:
    # ORDER_SUBMITTED = "order_submitted", _("Order Submitted")
    # ORDER_COMPLETED = "order_completed", _("Order Completed")
    # COMMENT_CREATED = "comment_created", _("New Comment")

class RelatedObjectType(models.TextChoices):
    ORDER = "order", _("Order")
    USER = "user", _("User")
    GENERIC = "generic", _("Generic")

# notifications/models.py:41-68
class Notification(TimestampedModel, UUIDModel):  # MRO: TimestampedModel first
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")  # :48
    type = models.CharField(max_length=30, choices=NotificationType.choices)                # :49
    title = models.CharField(max_length=255)                                                # :50
    body = models.TextField()                                                               # :51
    related_object_id = models.UUIDField(null=True, blank=True)                             # :52 generic FK
    related_object_type = models.CharField(                                                 # :53-55
        max_length=50, choices=RelatedObjectType.choices, null=True, blank=True
    )
    is_read = models.BooleanField(default=False, db_index=True)                             # :56

    class Meta:                                                                             # :58-64
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),  # inbox + unread
            models.Index(fields=["user", "type", "-created_at"]),     # per-type feed
        ]

    def __str__(self):  # :66-67
        return f"{self.user.email} - {self.title}"
```

**Conventions:**
- Inherits `TimestampedModel + UUIDModel` from `common/models.py:163-199` — UUID PK, `created_at/updated_at` indexed, ordering `-created_at`.
- `related_object_id/type` is a generic pointer — no FK to domain models. Keeps `notifications` decoupled from `orders`, `catalog`, etc.
- Add a new type: extend `NotificationType`, run `makemigrations` only if you add DB constraints — `TextChoices` alone needs no migration.

### Device — `notifications/models.py:70-114`

```python
# notifications/models.py:70-73
class DevicePlatform(models.TextChoices):
    ANDROID = "android", "Android"
    IOS = "ios", "iOS"
    WEB = "web", "Web"

# notifications/models.py:76-114
class Device(TimestampedModel, UUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")  # :84
    token = models.TextField(unique=True)                                              # :85 FCM registration token
    device_uuid = models.CharField(max_length=255)                                     # :86 stable per install
    platform = models.CharField(max_length=20, choices=DevicePlatform.choices)         # :87
    device_name = models.CharField(max_length=255, blank=True)                         # :88
    device_model = models.CharField(max_length=255, blank=True)                        # :89
    os_version = models.CharField(max_length=50, blank=True)                           # :90
    app_version = models.CharField(max_length=50, blank=True)                          # :91
    language = models.CharField(max_length=10, blank=True)                             # :92
    timezone = models.CharField(max_length=100, blank=True)                            # :93
    notifications_enabled = models.BooleanField(default=True)                           # :94 per-device kill switch
    is_active = models.BooleanField(default=True,                                       # :95-97
        help_text="Whether this token should receive notifications.")
    last_seen_at = models.DateTimeField(null=True, blank=True)                         # :98
    last_token_refresh_at = models.DateTimeField(null=True, blank=True)                # :99

    class Meta:  # :101-111
        ordering = ["-last_seen_at", "-created_at"]
        indexes = [
            models.Index(fields=["user"]),         # :104
            models.Index(fields=["platform"]),     # :105
            models.Index(fields=["is_active"]),    # :106
            models.Index(fields=["last_seen_at"]), # :107
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "device_uuid"],  # :110
                                    name="unique_user_device"),
        ]
```

**Why `device_uuid` + `token`?** `device_uuid` is app-generated (`uuid.v4()` in secure storage, survives token refresh, dies on reinstall). `token` is Firebase-generated and rotates. `update_or_create(user, device_uuid)` `views.py:87` lets you rotate `token` without creating duplicates, and `UniqueConstraint` prevents one install registering twice.

---

## 5. Services — should_notify Guard

### `notifications/services.py:1-18` (Push guard)

```python
# notifications/services.py:14-18
def should_notify(user) -> bool:
    """Return False if user opted out (notifications_enabled=False) or inactive."""
    if not user or not user.is_active:
        return False
    return getattr(user, "notifications_enabled", True)
```

- `user.is_active` covers `CustomUser.is_active` (`common/models.py:378` via `AbstractUser`).
- `notifications_enabled` is **not** a field on `CustomUser` today — `getattr(..., True)` defaults to opted-in. The flag lives on `Device.notifications_enabled` `models.py:94` for per-device mute. For per-user mute, add `CustomUser.notifications_enabled` or a `NotificationPreference` model (see [Enhance](#145-per-user-preference--opt-inout)).
- Called in `create_notification_task` `tasks.py:108` and `notify_welcome` `tasks.py:164` before any DB write.

### `accounts/notifications.py:43-51` (Email guard — different)

```python
# accounts/notifications.py:43-51
def should_notify(recipient_user) -> bool:
    if not recipient_user or not recipient_user.is_active:
        return False
    if hasattr(recipient_user, "notification_preferences"):
        prefs = recipient_user.notification_preferences
        if prefs is not None and prefs.get("email_enabled") is False:
            return False
    return True
```

- Checks `notification_preferences` JSON dict (`email_enabled`). Used by `accounts/tasks.py:65-67` for welcome email.
- **Do not confuse the two.** Push → `notifications.services.should_notify`. Email → `accounts.notifications.should_notify`. Consolidate only if you add a unified `CustomUser.notifications_enabled`.

---

## 6. Tasks — FCM Batch, Dispatch, Cache, Cleanup

### `notifications/tasks.py:36` — Batch limit

```python
FCM_BATCH_LIMIT = 500  # tasks.py:36 — FCM hard limit per MulticastMessage
```

### `notifications/tasks.py:39-74` — Multicast send

```python
# notifications/tasks.py:39-74
@shared_task
def send_multicast_notifications_task(registration_tokens, title, body, data_payload=None):
    if not HAS_FCM:  # :42-44
        logger.warning("firebase_admin not installed — skipping FCM send")
        return "FCM not configured"
    if not registration_tokens:  # :45-46
        return "No tokens provided"

    total_success = 0  # :48-50
    total_failure = 0
    all_failed_tokens = []

    for i in range(0, len(registration_tokens), FCM_BATCH_LIMIT):  # :52
        batch = registration_tokens[i : i + FCM_BATCH_LIMIT]       # :53
        message = messaging.MulticastMessage(                      # :54-58
            notification=messaging.Notification(title=title, body=body),
            data=data_payload or {},
            tokens=batch,
        )
        try:
            response = messaging.send_each_for_multicast(message)  # :60
            total_success += response.success_count                # :61
            total_failure += response.failure_count                # :62
            if response.failure_count > 0:                         # :63-66
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        all_failed_tokens.append(batch[idx])
        except Exception as e:                                     # :67-69
            logger.error(f"FCM multicast batch failed: {e}")
            total_failure += len(batch)

    if all_failed_tokens:                                          # :71-72
        clean_up_invalid_tokens.delay(all_failed_tokens)

    return f"Sent {total_success} notifications. Failed: {total_failure}"  # :74
```

- `HAS_FCM` is `try: from firebase_admin import messaging` `tasks.py:24-29` — graceful degrade when `firebase-admin` missing or `GOOGLE_APPLICATION_CREDENTIALS` unset.
- `data_payload` must be `Dict[str, str]` — FCM `data` values must be strings. Current call passes `{"type": notification_type, "related_id": related_object_id or ""}` `tasks.py:122`. Add more keys there if needed.
- Failures are per-token; partial batch success is normal. Invalid tokens are deleted async.

### `notifications/tasks.py:77-83` — Stale token cleanup

```python
# notifications/tasks.py:77-83
@shared_task
def clean_up_invalid_tokens(failed_tokens):
    """REUSE: Remove stale tokens — app will re-register on next launch."""
    from notifications.models import Device
    deleted_count, _ = Device.objects.filter(token__in=failed_tokens).delete()  # :82
    return f"Cleaned {deleted_count} invalid tokens."
```

- Deletes by `token` (unique) — not by `device_uuid`. One bad token → one row deleted; device re-registers on next app open via `POST /devices/` `views.py:78-102`.

### `notifications/tasks.py:86-125` — Create + dispatch (main entry)

```python
# notifications/tasks.py:86-125
@shared_task(bind=True)
def create_notification_task(
    self,
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    related_object_id: Optional[str] = None,
    related_object_type: Optional[str] = None,
):
    from notifications.models import Notification

    try:
        user = User.objects.get(id=user_id)  # :104
    except User.DoesNotExist:                # :105-106
        return {"status": "skipped", "reason": "user_not_found"}

    if not should_notify(user):              # :108-109
        return {"status": "skipped", "reason": "notifications_disabled"}

    notification = Notification.objects.create(  # :111-118
        user=user,
        type=notification_type,
        title=title,
        body=body,
        related_object_id=related_object_id,
        related_object_type=related_object_type,
    )

    _invalidate_unread_count_cache(user_id)  # :120
    _dispatch_push_notification(              # :121-123
        user, title, body, {"type": notification_type, "related_id": related_object_id or ""}
    )

    return {"status": "created", "notification_id": str(notification.id)}  # :125
```

- `bind=True` gives `self.retry` access — not currently used but available for retry logic.
- Validates `should_notify` **before** DB create — no inbox row if muted.
- `notification_type` is a plain string — caller can pass any `NotificationType` value without importing the enum.
- `related_object_id` is `Optional[str]` UUID string — cast with `str(obj.id)` at call site.

### `notifications/tasks.py:139-151` — Push dispatch

```python
# notifications/tasks.py:139-151
def _dispatch_push_notification(user, title: str, body: str, data: dict):
    from notifications.models import Device
    tokens = list(
        Device.objects.filter(user=user, is_active=True, notifications_enabled=True)  # :143-146
            .values_list("token", flat=True)
    )
    if not tokens:  # :148-149
        return {"status": "no_tokens"}
    send_multicast_notifications_task.delay(tokens, title, body, data)  # :150
    return {"status": "dispatched"}  # :151
```

- `is_active=True` filtered — flipped `False` on `unregister` `views.py:110` or logout (if you add it).
- `notifications_enabled=True` — per-device opt-out `models.py:94`.

### `notifications/tasks.py:157-167` — Example pattern

```python
# notifications/tasks.py:157-167
@shared_task(bind=True)
def notify_welcome(self, user_id: str):
    try:
        user = User.objects.get(id=user_id)  # :161
    except User.DoesNotExist:                # :162-163
        return {"status": "skipped", "reason": "user_not_found"}
    if not should_notify(user):              # :164-165
        return {"status": "skipped", "reason": "notifications_disabled"}
    create_notification_task.delay(user_id, "welcome", _("Welcome!"), _("Thanks for joining."))  # :166
    return {"status": "dispatched"}          # :167
```

- **REUSE:** Copy this shape for every domain event — `notify_order_shipped`, `notify_comment_created`, etc.

### `notifications/tasks.py:128-136` — Stale inbox cleanup

```python
# notifications/tasks.py:128-136
@shared_task
def cleanup_old_notifications():
    cutoff = timezone.now() - timedelta(days=90)  # :131
    from notifications.models import Notification
    deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff).delete()  # :134
    logger.info(f"Cleaned {deleted_count} old notifications")  # :135
    return {"deleted": deleted_count}  # :136
```

- Weekly Beat job. 90-day retention — tune to your needs.

---

## 7. Device Lifecycle — Register / Refresh / Unregister / Logout

```
App install
  │
  ├─ generate device_uuid = uuid.v4() → secure storage (Keychain/Keystore, survives update, dies on reinstall)
  ├─ FirebaseMessaging.getToken() → token
  ├─ POST /api/v1/notifications/devices/  {token, device_uuid, platform}  views.py:78-102
  │     → Device.objects.update_or_create(user, device_uuid, defaults={token, platform, is_active=True,
  │                                   last_seen_at=now(), last_token_refresh_at=now()})
  │
  ├─ onTokenRefresh (token rotated by OS/FCM)
  │     → POST /api/v1/notifications/devices/  {token: newToken, device_uuid: sameUuid}
  │     → same upsert → token column updated, last_token_refresh_at bumped
  │
  ├─ app foreground / periodic heartbeat
  │     → POST /api/v1/notifications/devices/  {token, device_uuid}  (refresh last_seen_at)
  │
  ├─ user toggles "mute this device"
  │     → PATCH device or direct update: Device.objects.filter(...).update(notifications_enabled=False)
  │     → _dispatch excludes notifications_enabled=False  tasks.py:144
  │
  ├─ POST /api/v1/notifications/devices/unregister/  {device_uuid}  views.py:104-111
  │     → Device.objects.filter(user, device_uuid).update(is_active=False)  views.py:110
  │
  └─ logout
        → POST /api/v1/users/logout/  accounts/views.py:292-306  (currently does NOT deactivate devices)
        → optionally add: Device.objects.filter(user=request.user).update(is_active=False)
        → also clear local token + device_uuid? Keep device_uuid for re-login on same install.
```

**Frontend contract (copy-paste):**

```javascript
// React Native / Flutter / Web — register on login + onTokenRefresh
import { Platform } from 'react-native';
import messaging from '@react-native-firebase/messaging';
import * as SecureStore from 'expo-secure-store'; // or react-native-keychain

async function getDeviceUUID() {
  let uuid = await SecureStore.getItemAsync('device_uuid');
  if (!uuid) {
    uuid = crypto.randomUUID(); // uuid.v4()
    await SecureStore.setItemAsync('device_uuid', uuid);
  }
  return uuid;
}

async function registerDevice(accessToken) {
  const device_uuid = await getDeviceUUID();
  const token = await messaging().getToken();
  await fetch('/api/v1/notifications/devices/', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token,
      device_uuid,
      platform: Platform.OS, // 'android' | 'ios' | 'web'
      device_name: Platform.OS === 'ios' ? 'iPhone' : 'Android',
    }),
  });
  // listen for refresh
  messaging().onTokenRefresh(async (newToken) => {
    await fetch('/api/v1/notifications/devices/', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: newToken, device_uuid, platform: Platform.OS }),
    });
  });
}

// On logout — deactivate, keep device_uuid for next login on same install
async function unregisterDevice(accessToken) {
  const device_uuid = await SecureStore.getItemAsync('device_uuid');
  await fetch('/api/v1/notifications/devices/unregister/', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_uuid }),
  });
}
```

**Backend logout hook (optional — add if you want logout to mute push):**

```python
# accounts/views.py:292-306 — inside UserViewSet.logout after token blacklist
from notifications.models import Device
Device.objects.filter(user=request.user).update(is_active=False)
```

---

## 8. Views & URLs — Inbox + Device Registry

### NotificationViewSet — `notifications/views.py:18-65`

```python
# notifications/views.py:18-65
class NotificationViewSet(BaseViewSet):  # :18
    serializer_class = NotificationSerializer  # :21
    permission_classes = [IsAuthenticated]     # :22

    def get_queryset(self):  # :24-26
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

    def list(self, request, *args, **kwargs):  # :28-35
        from .tasks import get_unread_count  # :31
        response = super().list(request, *args, **kwargs)  # :33 paginated via StandardPagination
        response.data["unread_count"] = get_unread_count(str(request.user.id))  # :34
        return response

    def retrieve(self, request, *args, **kwargs):  # :37-45
        obj = self.get_object()  # :39
        obj.is_read = True  # :40
        obj.save(update_fields=["is_read"])  # :41
        from .tasks import _invalidate_unread_count_cache  # :42
        _invalidate_unread_count_cache(str(request.user.id))  # :44
        return super().retrieve(request, *args, **kwargs)  # :45

    @action(detail=True, methods=["patch"], url_path="read")  # :47
    def mark_read(self, request, pk=None):  # :48-56
        obj = self.get_object()  # :50
        obj.is_read = True  # :51
        obj.save(update_fields=["is_read"])  # :52
        from .tasks import _invalidate_unread_count_cache  # :53
        _invalidate_unread_count_cache(str(request.user.id))  # :55
        return Response({"is_read": True})  # :56

    @action(detail=False, methods=["post"], url_path="read-all")  # :58
    def mark_all_read(self, request):  # :59-65
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)  # :61
        from .tasks import _invalidate_unread_count_cache  # :62
        _invalidate_unread_count_cache(str(request.user.id))  # :64
        return Response({"marked": True})  # :65
```

- Inherits `BaseViewSet` from `common/views.py` — envelope `{"error": {"code": "...", "message": "..."}}`, `SENSITIVE_LOG_KEYS` scrubbing, `perform_*` hooks.
- `get_queryset` scopes to `request.user` — no cross-user leak.
- `list` injects `unread_count` from cache (5 min) — no extra `COUNT(*)` on hot path.
- `retrieve` auto-marks read — useful for detail navigation; `mark_read` for explicit action.

### DeviceViewSet — `notifications/views.py:68-111`

```python
# notifications/views.py:68-111
class DeviceViewSet(BaseViewSet):  # :68
    serializer_class = DeviceSerializer  # :71
    permission_classes = [IsAuthenticated]  # :72

    def get_queryset(self):  # :74-76
        return Device.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):  # :78-102
        token = request.data.get("token")  # :80
        device_uuid = request.data.get("device_uuid")  # :81
        if not token or not device_uuid:  # :82-85
            return Response({"error": "token and device_uuid required"}, status=400)

        device, created = Device.objects.update_or_create(  # :87-97
            user=request.user,
            device_uuid=device_uuid,
            defaults={
                "token": token,
                "platform": request.data.get("platform", "web"),  # :92
                "device_name": request.data.get("device_name", ""),  # :93
                "is_active": True,  # :94 re-activates if previously unregistered
                "last_seen_at": timezone.now(),  # :95
                "last_token_refresh_at": timezone.now(),  # :96
            },
        )
        return Response(DeviceSerializer(device).data,  # :99-102
            status=201 if created else 200)

    @action(detail=False, methods=["post"], url_path="unregister")  # :104
    def unregister(self, request):  # :105-111
        device_uuid = request.data.get("device_uuid")  # :107
        if not device_uuid:  # :108-109
            return Response({"error": "device_uuid required"}, status=400)
        Device.objects.filter(user=request.user, device_uuid=device_uuid).update(is_active=False)  # :110
        return Response({"deactivated": True})  # :111
```

### URLs — `notifications/urls.py:1-12` + `project/urls.py:27,41-43`

```python
# notifications/urls.py:8-12
router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notification")   # :9
router.register(r"devices", DeviceViewSet, basename="device")       # :10
urlpatterns = [path("", include(router.urls))]                       # :12

# project/urls.py:27,41-43
api_prefix = "api/v1"  # :27
path(f"{api_prefix}/notifications/", include("notifications.urls"), name="notifications"),  # :41-43
```

**Final routes (DefaultRouter):**

| Method | Path | View | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/notifications/` | `NotificationViewSet.list` `views.py:28` | Paginated inbox + `unread_count` |
| `GET` | `/api/v1/notifications/{id}/` | `retrieve` `views.py:37` | Detail + auto-mark read |
| `PATCH` | `/api/v1/notifications/{id}/read/` | `mark_read` `views.py:47` | Mark single read |
| `POST` | `/api/v1/notifications/read-all/` | `mark_all_read` `views.py:58` | Mark all read |
| `GET` | `/api/v1/notifications/devices/` | `DeviceViewSet.list` | List own devices |
| `POST` | `/api/v1/notifications/devices/` | `create` `views.py:78` | Upsert device |
| `POST` | `/api/v1/notifications/devices/unregister/` | `unregister` `views.py:104` | Deactivate device |
| `GET` | `/api/admin/notifications/notification/` | `NotificationAdmin` `admin.py:10` | Unfold admin inbox |
| `GET` | `/api/admin/notifications/device/` | `DeviceAdmin` `admin.py:17` | Unfold admin devices |

> All inbox/device endpoints require `IsAuthenticated` — `views.py:22,72`. No public access.

---

## 9. Serializers

```python
# notifications/serializers.py:11-26
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id","type","title","body","related_object_id","related_object_type","is_read","created_at"]  # :16-25
        read_only_fields = ["id", "created_at"]  # :26

# notifications/serializers.py:29-44
class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["id","token","device_uuid","platform","device_name","is_active","notifications_enabled","last_seen_at"]  # :34-43
        read_only_fields = ["id", "created_at"]  # :44 — Device view uses manual create, not serializer.save()

# notifications/serializers.py:47-53 — explicit validation (not wired, for reuse)
class DeviceRegisterSerializer(serializers.Serializer):
    token = serializers.CharField()  # :50
    device_uuid = serializers.CharField()  # :51
    platform = serializers.ChoiceField(choices=["android", "ios", "web"])  # :52
    device_name = serializers.CharField(required=False, allow_blank=True, default="")  # :53
```

- Serializers are intentionally thin — business logic lives in tasks/services.
- `DeviceSerializer` exposes `token` — consider `write_only` if you don't want clients listing raw tokens.

---

## 10. Admin — Unfold Inbox + Devices

```python
# notifications/admin.py:10-14
@admin.register(Notification)
class NotificationAdmin(BaseAdmin):  # must inherit BaseAdmin (common/unfold_admin_bases.py)
    list_display = ["user", "type", "title", "is_read", "created_at"]  # :12
    list_filter = ["type", "is_read"]  # :13
    search_fields = ["user__email", "title", "body"]  # :14

# notifications/admin.py:17-28
@admin.register(Device)
class DeviceAdmin(BaseAdmin):
    list_display = ["user","platform","device_uuid","is_active","notifications_enabled","last_seen_at"]  # :19-26
    list_filter = ["platform", "is_active"]  # :27
    search_fields = ["user__email", "token", "device_uuid"]  # :28
```

**Unfold sidebar** `project/settings/unfold_config.py:366-379`:

```python
# unfold_config.py:366-379
{
    "title": _("Notifications"),
    "collapsible": True,
    "items": [
        {"title": _("User Notifications"), "icon": "notifications",
         "link": reverse_lazy("admin:notifications_notification_changelist")},  # :370-372
        {"title": _("Devices"), "icon": "devices",
         "link": reverse_lazy("admin:notifications_device_changelist")},       # :374-378
    ],
},
```

> Every `admin.ModelAdmin` **must** inherit from `BaseAdmin` (or `ReadOnlyAdmin`/`SoftDeleteAdmin`) to enable Unfold theming. Never subclass raw `admin.ModelAdmin` — see `AGENTS.md §3.4`.

---

## 11. Caching — Unread Count (5 min)

```python
# notifications/tasks.py:170-187
def _invalidate_unread_count_cache(user_id: str):  # :170-173
    from django.core.cache import cache
    cache.delete(f"notifications:unread:{user_id}")  # :173

def get_unread_count(user_id: str) -> int:  # :176-187
    from django.core.cache import cache
    cache_key = f"notifications:unread:{user_id}"  # :180
    count = cache.get(cache_key)  # :181
    if count is None:  # :182
        from notifications.models import Notification
        count = Notification.objects.filter(user_id=user_id, is_read=False).count()  # :185
        cache.set(cache_key, count, 300)  # :186 — 5 minutes
    return count  # :187
```

- **Backend:** `django_redis.cache.RedisCache` `project/settings/base.py:303-315` at `CACHE_URL` `redis://:redis_password@redis:6379/1` `.env.example:34`.
- **Invalidation:** `create_notification_task` `tasks.py:120`, `retrieve` `views.py:44`, `mark_read` `views.py:55`, `mark_all_read` `views.py:64`.
- **Hit path:** `NotificationViewSet.list` `views.py:34` injects `unread_count` without extra `COUNT(*)` when cached.
- **Per-user key:** `notifications:unread:{user_id}` — safe to keep with shared Redis. Never cache user-specific data under a shared key.
- **If you drop Redis:** Follow `guides/Settings guide.md` Redis removal → fallback to `LocMemCache`; unread count still works (per-process, no cross-worker share) — acceptable for small deploys.

---

## 12. How to Use — Send a Notification (Copy-Paste)

### 12.1 Trigger from any view / service / management command

```python
from notifications.tasks import create_notification_task

# After any domain event — order created, comment posted, payment received:
create_notification_task.delay(
    user_id=str(user.id),
    notification_type="generic",  # or "welcome" — extend NotificationType for your domain
    title="Order confirmed",
    body=f"Your order #{order.id} is confirmed",
    related_id=str(order.id),       # UUID string of the related object
    related_type="order",           # must be a RelatedObjectType value or your custom string
)
# → creates Notification row (if should_notify) + invalidates cache + dispatches FCM to all active devices (500 batch)
#   Gracefully handles missing user / muted user / no devices / missing firebase-admin.
```

### 12.2 Trigger via signal (prefer service call; signals only for cross-app)

```python
# e.g. orders/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.tasks import create_notification_task

@receiver(post_save, sender=Order)
def notify_order_created(sender, instance, created, **kwargs):
    if created:
        create_notification_task.delay(
            str(instance.user_id),
            "generic",  # or "order_submitted" after you extend NotificationType
            "Order created",
            f"Order {instance.id} received",
            str(instance.id),
            "order",
        )
```

> Signals must be short + idempotent. If you can call the service directly from the view, prefer that over signals — `AGENTS.md §3.3`.

### 12.3 Check unread count (cached 5 min)

```python
from notifications.tasks import get_unread_count

count = get_unread_count(str(request.user.id))  # cache key "notifications:unread:{user_id}" tasks.py:180
```

### 12.4 Add a new notification type (no migration if TextChoices only)

```python
# notifications/models.py:21-30
class NotificationType(models.TextChoices):
    WELCOME = "welcome", _("Welcome")
    GENERIC = "generic", _("Generic")
    ORDER_SHIPPED = "order_shipped", _("Order Shipped")  # <-- add
    PAYMENT_RECEIVED = "payment_received", _("Payment Received")

# Dispatch:
create_notification_task.delay(str(user.id), "order_shipped", "Shipped!", f"Order {order.id} shipped", str(order.id), "order")
```

### 12.5 Copy-paste a domain-specific wrapper

```python
# notifications/tasks.py:157-167 — copy this shape per event
from celery import shared_task
from django.utils.translation import gettext_lazy as _
from notifications.tasks import create_notification_task
from notifications.services import should_notify
from django.contrib.auth import get_user_model
User = get_user_model()

@shared_task(bind=True)
def notify_order_shipped(self, user_id: str, order_id: str):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"status": "skipped", "reason": "user_not_found"}
    if not should_notify(user):
        return {"status": "skipped", "reason": "notifications_disabled"}
    create_notification_task.delay(
        user_id, "order_shipped",
        _("Order shipped!"), _("Your order is on the way."),
        order_id, "order",
    )
    return {"status": "dispatched"}
```

---

## 13. Setup From Scratch — Zero to Current State

> Follow in order. Each step is copy-paste. Assumes you start with **no notifications app**.

### Step 1 — Install dependencies

```bash
pip install firebase-admin==7.4.0
# firebase-admin pulls google-auth, requests, etc.
# Already pinned in requirements.txt:11 — if you start fresh, add it there:
# requirements.txt
# firebase-admin==7.4.0  # [NEEDED] FCM push (notifications/tasks.py)
```

### Step 2 — Create a Firebase project + service account

1. Go to https://console.firebase.google.com → Create project (or reuse).
2. Project Settings → Service accounts → Generate new private key → downloads `firebase-adminsdk.json`.
3. Place file at repo root: `./firebase-adminsdk.json` (or any path — env points to it).
4. **Never commit** this JSON. Add to `.gitignore`:
   ```
   firebase-adminsdk.json
   ```

### Step 3 — Env (`/.env` + `/.env.example:85`)

```bash
# .env.example:85 — uncomment and set in your .env
GOOGLE_APPLICATION_CREDENTIALS=./firebase-adminsdk.json

# Redis cache (already in .env.example:38) — required for unread cache tasks.py:180
CACHE_URL=redis://:redis_password@redis:6379/1
CELERY_BROKER_URL=redis://:redis_password@redis:6379/0
CELERY_RESULT_BACKEND=redis://:redis_password@redis:6379/0
```

### Step 4 — Settings: enable Firebase credential (`project/settings/base.py:515-519`)

```python
# project/settings/base.py:515-519 — uncomment this block
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(BASE_DIR, "firebase-adminsdk.json"),
)
```

> This is read by `firebase_admin` SDK automatically via `GOOGLE_APPLICATION_CREDENTIALS` env var — the Django setting is for documentation + to set a default path.

### Step 5 — Settings: register app (`project/settings/base.py:60-68`)

```python
# project/settings/base.py:60-68
INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.inlines",
    "accounts",
    "common",
    "notifications",  # <-- add  base.py:68  REUSE: FCM + in-app inbox (generic)
    "compliance",
    "contacts",
    "modeltranslation",
    # ... rest
]
```

### Step 6 — Create the app (8 files)

```bash
python manage.py startapp notifications
# Replace generated files with the current implementation:
# notifications/models.py      — Notification + Device (see §4)
# notifications/services.py    — should_notify (see §5)
# notifications/tasks.py       — all tasks (see §6)
# notifications/views.py       — NotificationViewSet + DeviceViewSet (see §8)
# notifications/serializers.py — NotificationSerializer + DeviceSerializer (see §9)
# notifications/urls.py        — router (see §8)
# notifications/admin.py       — NotificationAdmin + DeviceAdmin (see §10)
# notifications/__init__.py    — empty (or celery app import if needed)
```

> Copy exact contents from the current repo — they are generic and project-agnostic.

### Step 7 — Wire URLs (`project/urls.py:27,41-43`)

```python
# project/urls.py:27,41-43
api_prefix = "api/v1"  # :27

urlpatterns = [
    # ...
    path(f"{api_prefix}/notifications/", include("notifications.urls"), name="notifications"),  # :41-43 REUSE
    # ...
]
```

### Step 8 — Wire Unfold sidebar (`project/settings/unfold_config.py:366-379`)

```python
# project/settings/unfold_config.py:366-379 — add inside UNFOLD["SIDEBAR"]["navigation"]
{
    "title": _("Notifications"),
    "collapsible": True,
    "items": [
        {"title": _("User Notifications"), "icon": "notifications",
         "link": reverse_lazy("admin:notifications_notification_changelist")},
        {"title": _("Devices"), "icon": "devices",
         "link": reverse_lazy("admin:notifications_device_changelist")},
    ],
},
```

### Step 9 — Cache + Celery (already configured — verify)

```python
# project/settings/base.py:303-315 — already present
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("CACHE_URL", "redis://:redis_password@redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
    }
}

# project/settings/base.py:345-351 — add Beat entry for weekly cleanup
CELERY_BEAT_SCHEDULE = {
    "cleanup-old-notifications": {
        "task": "notifications.tasks.cleanup_old_notifications",  # tasks.py:128
        "schedule": 604800.0,  # 7 days in seconds (or use crontab)
        # Alternative with crontab:
        # "schedule": crontab(hour=3, minute=0, day_of_week="monday"),
    },
}
# Requires: from celery.schedules import crontab
```

### Step 10 — Migrate

```bash
python manage.py makemigrations notifications
python manage.py migrate
# Creates: notifications_notification + notifications_device
# Indexes: (user,is_read,-created_at), (user,type,-created_at)  models.py:61-64
#          (user), (platform), (is_active), (last_seen_at)      models.py:103-107
# Constraint: unique_user_device (user, device_uuid)              models.py:110
```

### Step 11 — Verify without Firebase (inbox-only smoke test)

```bash
# With TESTING=True or CELERY_TASK_ALWAYS_EAGER=True (project/settings/local.py:28-29),
# tasks run synchronously — no worker needed.

python manage.py shell
>>> from notifications.tasks import create_notification_task, get_unread_count
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> u = User.objects.first()
>>> create_notification_task(str(u.id), "welcome", "Hello", "Welcome to Rapido")
{'status': 'created', 'notification_id': '...'}
>>> get_unread_count(str(u.id))
1
```

### Step 12 — Verify with Firebase (push smoke test)

```bash
# 1. Ensure firebase-adminsdk.json exists and env points to it:
echo $GOOGLE_APPLICATION_CREDENTIALS  # or check .env

# 2. Start infra:
docker compose up -d redis celery_worker celery_beat  # or your compose names

# 3. Register a device via API (get a real FCM token from your app):
curl -X POST http://localhost:8000/api/v1/notifications/devices/ \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"token":"<FCM_TOKEN>","device_uuid":"<uuid.v4>","platform":"android"}'
# → 201 {"id":"...","token":"...","platform":"android","is_active":true, ...}  views.py:99-102

# 4. Trigger:
python manage.py shell -c "from notifications.tasks import create_notification_task; create_notification_task.delay(str(User.objects.first().id), 'generic', 'Test', 'Hello push', None, None)"

# 5. Check worker logs for: "Sent 1 notifications. Failed: 0"  tasks.py:74
# 6. Check device receives push; check inbox:
curl http://localhost:8000/api/v1/notifications/ -H "Authorization: Bearer <access>"
# → {"count":1,"results":[...],"unread_count":1}  views.py:28-34
```

### Step 13 — Frontend wiring

- Store `device_uuid` in secure storage (`uuid.v4()` once) — see [Device Lifecycle](#7-device-lifecycle--register--refresh--unregister--logout).
- Call `POST /devices/` on login + on `onTokenRefresh`.
- Call `POST /devices/unregister/` on logout.
- Listen for `data.type` / `data.related_id` in push payload to deep-link.

### Step 14 — Check

```bash
make check          # black, isort, flake8, mypy
make test           # pytest — should_notify + inbox + device tests
docker compose config > /dev/null  # validates compose
```

---

## 14. How to Adjust / Enhance

### 14.1 Add a new notification type

```python
# notifications/models.py:21-30
class NotificationType(models.TextChoices):
    WELCOME = "welcome", _("Welcome")
    GENERIC = "generic", _("Generic")
    ORDER_SUBMITTED = "order_submitted", _("Order Submitted")  # new
    ORDER_SHIPPED = "order_shipped", _("Order Shipped")        # new
    PAYMENT_RECEIVED = "payment_received", _("Payment Received") # new

# No migration needed for TextChoices alone. If you add DB check constraints, makemigrations.

# Dispatch anywhere:
create_notification_task.delay(
    str(user.id), "order_shipped",
    "Order shipped!", f"Order {order.id} is on the way",
    str(order.id), "order",
)

# Optional: typed wrapper per event (copy notify_welcome pattern tasks.py:157-167)
@shared_task(bind=True)
def notify_order_shipped(self, user_id: str, order_id: str, tracking_url: str = ""):
    from django.contrib.auth import get_user_model
    from notifications.services import should_notify
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"status": "skipped", "reason": "user_not_found"}
    if not should_notify(user):
        return {"status": "skipped", "reason": "notifications_disabled"}
    create_notification_task.delay(
        user_id, "order_shipped", _("Shipped!"), _("Tracking: ") + tracking_url,
        order_id, "order",
    )
    return {"status": "dispatched"}
```

### 14.2 Change FCM batch size

```python
# notifications/tasks.py:36
FCM_BATCH_LIMIT = 500  # REUSE: easy global to tune — max 500 per FCM spec. Lower to 100 if you hit timeouts.

# Or make it a setting:
# project/settings/base.py
FCM_BATCH_LIMIT = int(os.getenv("FCM_BATCH_LIMIT", "500"))

# notifications/tasks.py:36,52
from django.conf import settings
FCM_BATCH_LIMIT = getattr(settings, "FCM_BATCH_LIMIT", 500)
# for i in range(0, len(tokens), FCM_BATCH_LIMIT):  # :52
```

> Keep `FCM_BATCH_LIMIT ≤ 500` — Firebase rejects larger `MulticastMessage`. For very large audiences (10k+ tokens), the loop `tasks.py:52-72` naturally chunks.

### 14.3 Disable FCM, keep inbox only

**Use when:** web-only, email-only, or you want to defer Firebase setup.

```python
# Option A — fastest: uninstall firebase-admin (tasks.py:24-29 graceful degrade)
pip uninstall firebase-admin
# tasks.py:42-44 logs "FCM not configured" and inbox still works. No code change.

# Option B — keep package, skip push per call
# notifications/tasks.py:86-125 — remove the _dispatch line
#   _dispatch_push_notification(user, title, body, {...})  # :121 delete this
# Keep: Notification.objects.create + cache invalidation.

# Option C — surgical: delete only push tasks
# Delete from notifications/tasks.py: send_multicast_notifications_task (39-74)
#                              + clean_up_invalid_tokens (77-83)
#                              + _dispatch_push_notification (139-151)
# Keep: create_notification_task (without dispatch) + cleanup_old_notifications + get_unread_count
# Also optionally delete Device model + DeviceViewSet + DeviceAdmin if no push at all.

# After any option, you can keep Device for future or drop it:
# If dropping Device: delete notifications/models.py:70-114 Device + DevicePlatform,
#   delete DeviceViewSet views.py:68-111, DeviceSerializer serializers.py:29-53,
#   delete router.register("devices") urls.py:10, update admin unfold_config.py:366-379.
```

### 14.4 Add APNS-specific payload (iOS badge, sound, priority)

FCM abstracts APNS — you send via `firebase_admin.messaging` and Firebase translates to APNS. Current `MulticastMessage` `tasks.py:54-58` sends only `notification` + `data`. Extend for APNS:

```python
# notifications/tasks.py:54-58 — enhance send_multicast_notifications_task
from firebase_admin import messaging

# Per-batch, build APNS config:
apns = messaging.APNSConfig(
    payload=messaging.APNSPayload(
        aps=messaging.Aps(
            badge=1,              # or compute unread count
            sound="default",
            category="ORDER_SHIPPED",
            thread_id="order-updates",
            mutable_content=True,  # for Notification Service Extension
        ),
    ),
    headers={"apns-priority": "10"},  # 10 immediate, 5 power-efficient
)
android = messaging.AndroidConfig(
    priority="high",
    notification=messaging.AndroidNotification(
        channel_id="orders",
        priority="high",
    ),
)
message = messaging.MulticastMessage(
    notification=messaging.Notification(title=title, body=body),
    data=data_payload or {},
    apns=apns,
    android=android,
    tokens=batch,
)
```

> For `data`-only silent pushes (no banner), omit `notification` and set `apns.payload.aps.content_available = True`.

### 14.5 Per-user preference / opt-in-out

**Current:** `should_notify` defaults to `True` `services.py:18`, per-device `Device.notifications_enabled` `models.py:94`. Add per-user toggle:

```python
# Option A — simplest: add field to CustomUser
# common/models.py:378 (inside CustomUser)
notifications_enabled = models.BooleanField(default=True, help_text=_("Master push toggle"))

# notifications/services.py:14-18 — already reads this via getattr:
# return getattr(user, "notifications_enabled", True)  # works immediately

# Option B — granular per-type preferences
# common/models.py or notifications/models.py
class NotificationPreference(TimestampedModel, UUIDModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_prefs")
    preferences = models.JSONField(default=dict)  # {"order_shipped": True, "marketing": False}
    # Or explicit booleans:
    # order_updates = models.BooleanField(default=True)
    # marketing = models.BooleanField(default=False)

# notifications/services.py — extend guard:
def should_notify(user, notification_type: str = None) -> bool:
    if not user or not user.is_active:
        return False
    if getattr(user, "notifications_enabled", True) is False:
        return False
    if notification_type and hasattr(user, "notification_prefs"):
        prefs = user.notification_prefs.preferences
        if prefs.get(notification_type) is False:
            return False
        if prefs.get("all") is False:
            return False
    return True

# Expose toggle endpoint:
# notifications/views.py — add to NotificationViewSet or new PreferenceViewSet
@action(detail=False, methods=["patch"], url_path="preferences")
def update_preferences(self, request):
    prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
    prefs.preferences.update(request.data)
    prefs.save(update_fields=["preferences"])
    return Response(prefs.preferences)

@action(detail=False, methods=["get"], url_path="preferences")
def get_preferences(self, request):
    prefs = getattr(request.user, "notification_prefs", None)
    return Response(prefs.preferences if prefs else {})
```

### 14.6 Change inbox retention (90-day cleanup)

```python
# notifications/tasks.py:128-136 — tune cutoff
@shared_task
def cleanup_old_notifications(days: int = 90):  # make param
    cutoff = timezone.now() - timedelta(days=days)  # :131
    from notifications.models import Notification
    deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff).delete()  # :134
    return {"deleted": deleted_count}

# Wire with arg via Beat:
# project/settings/base.py:345-351
CELERY_BEAT_SCHEDULE = {
    "cleanup-old-notifications": {
        "task": "notifications.tasks.cleanup_old_notifications",
        "schedule": crontab(hour=3, minute=0, day_of_week="monday"),
        "kwargs": {"days": 30},  # keep 30 days instead of 90
    },
}

# Or retention per type:
# Notification.objects.filter(created_at__lt=cutoff, type="generic").delete()
# Keep "order_shipped" longer than "generic".
```

### 14.7 Topic / fanout broadcast (all users, all sellers, etc.)

Current design is **per-user** (`Device.filter(user=user)` `tasks.py:143`). For broadcast:

```python
# Option A — FCM Topics (client subscribes to topic, server sends to topic)
from firebase_admin import messaging
messaging.subscribe_to_topic(tokens, "all-sellers")  # on register
messaging.send(messaging.Message(
    notification=messaging.Notification(title=title, body=body),
    topic="all-sellers",
    data=data_payload,
))

# Option B — fanout task (no topic, iterate users)
@shared_task
def broadcast_notification(title: str, body: str, notification_type: str = "generic"):
    from django.contrib.auth import get_user_model
    from notifications.tasks import create_notification_task
    User = get_user_model()
    for user_id in User.objects.filter(is_active=True).values_list("id", flat=True).iterator():
        create_notification_task.delay(str(user_id), notification_type, title, body)
    # For large audiences, chunk with celery group or use FCM topics instead.
```

### 14.8 Rich payload — deep links, images, actions

```python
# notifications/tasks.py:121-123 — extend data payload
_dispatch_push_notification(
    user, title, body, {
        "type": notification_type,
        "related_id": related_object_id or "",
        "related_type": related_object_type or "",
        "deep_link": f"rapido://order/{related_object_id}",  # client routes on this
        "image": "https://cdn.example.com/order-shipped.jpg",
        "action": "VIEW_ORDER",
        "unread_count": str(get_unread_count(str(user.id))),  # for badge
    }
)
# Reminder: all data values must be strings for FCM.
```

### 14.9 Silent / background push

```python
# For iOS content-available or Android data-only:
from firebase_admin import messaging
message = messaging.MulticastMessage(
    data={"type": "sync", "related_id": order_id},  # no notification field
    apns=messaging.APNSConfig(payload=messaging.APNSPayload(
        aps=messaging.Aps(content_available=True)
    )),
    android=messaging.AndroidConfig(priority="high"),
    tokens=batch,
)
# Client handles in background via onBackgroundMessage.
```

### 14.10 Scheduled / delayed notification

```python
# Celery ETA / countdown
from datetime import timedelta
create_notification_task.apply_async(
    args=[str(user.id), "generic", "Reminder", "Your order is still pending"],
    countdown=3600,  # 1 hour
    # or eta=datetime(2026, 9, 9, 10, 0, tzinfo=timezone.utc)
)

# Or Beat periodic: add to CELERY_BEAT_SCHEDULE with crontab.
```

### 14.11 Security hardening

- **Never expose `is_staff` / `is_superuser` via notification APIs** — `NotificationViewSet` scopes to `request.user` `views.py:25`, not admin.
- **Throttle device registration** — add `AuthRateThrottle` / `ScopedRateThrottle` to `DeviceViewSet.create` if abused.
- **Validate `platform`** — restrict to `DevicePlatform.choices` `models.py:87`; current `views.py:92` defaults to `"web"` but doesn't validate — add check or use `DeviceRegisterSerializer` `serializers.py:47-53`.
- **No secrets in push** — FCM payload is not encrypted end-to-end; never send passwords, tokens, or PII in `data_payload`.

---

## 15. Tradeoffs

| Decision | Benefit | Cost |
|---|---|---|
| **Inbox + FCM dual channel** | Reliable (inbox survives push miss) + realtime (push). | Two writes per event (DB + FCM). |
| **FCM `MulticastMessage` batch 500** `tasks.py:36,52` | One API call per 500 tokens, minimal latency. | Failed tokens require second task `clean_up_invalid_tokens` `tasks.py:72`. |
| **`clean_up_invalid_tokens` deletes row** `tasks.py:82` | Stale tokens auto-healed; app re-registers. | Brief gap where device muted until next launch. |
| **Cache unread count 5 min** `tasks.py:186` | Avoids `COUNT(*) where is_read=False` on every list. List is paginated `views.py:33` with single cached int. | Count is eventually consistent (≤ 5 min stale). Invalidation on writes `tasks.py:120,170` mitigates. |
| **Generic `related_object_id` (UUID string)** `models.py:52` | Zero coupling — `notifications` never imports domain models. `AGENTS.md §3.1` compliant. | No DB FK integrity; orphaned `related_object_id` if domain object deleted. |
| **Per-user device filter** `tasks.py:143` | Notification reaches all devices a user owns (phone + tablet). | Broadcast to many users requires fanout or FCM Topics (see 14.7). |
| **`should_notify` before DB create** `tasks.py:108` | Muted user creates zero rows — no inbox spam. | If user wanted inbox but not push, they'd get neither — split guard if needed (see 14.5 Option B). |
| **90-day auto-delete** `tasks.py:131` | Caps table growth; inbox stays fast. Indexes `models.py:61-64` keep queries cheap. | Old notifications gone — archive to cold storage first if compliance requires. |
| **Celery async dispatch** `tasks.py:150` | View/service never blocks on FCM network. Eager in tests `base.py:39-41` + `local.py:28-29` keeps tests sync. | Requires Redis + worker + beat — extra infra. Pure inbox still works without worker (tasks eager). |
| **Single `GOOGLE_APPLICATION_CREDENTIALS` file** `base.py:516` | Simple setup, one service account. | One Firebase project per environment — use separate service accounts for staging/prod. |
| **No WebSockets** | Simpler infra (no Channels, no connection scaling). | Sub-second realtime not possible — FCM latency is seconds + OS batching. |
| **Unfold `BaseAdmin` mandatory** `admin.py:11,18` | Consistent theming + `badges` + `image_tag` helpers. | Must not use raw `admin.ModelAdmin` — see `AGENTS.md §4.8`. |

---

## 16. Removal — Full and Partial

> Fully decoupled — no other app imports `notifications.models`. Safe to delete entirely. Verified: `common/` only has generic cache (`common/decorators.py:6 cache_result`, `common/middleware.py:175 RateLimit`, `common/permissions.py:11 cache`) — none notification-specific.

### Full Removal (drop FCM + inbox)

1. **Settings `project/settings/base.py:68` + `506-519`** → delete `"notifications"` from `INSTALLED_APPS` `base.py:68` + delete `GOOGLE_APPLICATION_CREDENTIALS` block `base.py:515-519` (`os.getenv(..., os.path.join(BASE_DIR, "firebase-adminsdk.json"))`). Keep `CACHES` `base.py:303-315` (`CACHE_URL` `.env.example:38` `redis://:redis_password@redis:6379/1`) only if you keep other cache features (`common.decorators.cache_result`, `common.middleware.RateLimit`). If you drop Redis entirely, switch to `LocMemCache` per `Settings guide.md` Redis removal.

2. **URLs `project/urls.py:41-43`** → delete `path(f'{api_prefix}/notifications/', include('notifications.urls'))` `urls.py:41-43`.

3. **Delete app** → delete entire `notifications/` folder (8 files: `models.py` `114 lines`, `services.py` `18`, `tasks.py` `187`, `views.py` `111`, `serializers.py` `53`, `urls.py` `12`, `admin.py` `28`, `__init__.py`).

4. **Admin `project/settings/unfold_config.py:366-379`** → delete `Notifications` collapsible group (2 items: `User Notifications` `unfold_config.py:370-372` + `Devices` `374-378`).

5. **Common** → no `common/` import of `notifications` exists (verified grep — `cache` in `common/decorators.py:6`, `common/middleware.py:175`, `common/permissions.py:11` are generic, not notifications-specific — keep). Notifications-specific cache keys `notifications:unread:{user_id}` `tasks.py:170,180` are deleted with app.

6. **Accounts** → `accounts/views.py:292-306` does not currently reference `Device` (no `Device.objects.filter(...).update(is_active=False)` in logout) — nothing to delete. If you added the optional logout hook (Step 7 / 14.5), remove it. `accounts/tasks.py:65` `from accounts.notifications import should_notify` is email-specific — keep. `common/helpers.py:233-290` `send_template_email` etc. are generic — keep.

7. **Requirements `requirements.txt:11`** → delete `firebase-admin==7.4.0` `11` (+ keep `requests` `72` if `accounts` social or other HTTP — it is also transitive for `firebase-admin` but widely used).

8. **Env `.env.example:85`** → delete `# GOOGLE_APPLICATION_CREDENTIALS=./firebase-adminsdk.json` `85`. If you drop Redis cache entirely, also handle `CACHE_URL` `.env.example:38` (`redis://:redis_password@redis:6379/1`) per `Settings guide.md` — replace with `LocMemCache` URL or remove. Keep `REDIS_*` + `CELERY_BROKER_URL` `43-44` only if Celery stays.

9. **DB** → `python manage.py migrate` will not delete tables — run `python manage.py migrate notifications zero` **before** deleting folder, or manually:
   ```sql
   DROP TABLE IF EXISTS notifications_notification, notifications_device;
   ```

10. **Check** →
    ```bash
    make check && docker compose config > /dev/null
    # Ensure no ModuleNotFoundError: notifications
    python manage.py check
    ```

### Partial — Keep Inbox, Drop FCM Push Only

Keep inbox, lose push — smallest change, no migration:

```python
# Keep: notifications/models.py (Notification) + notifications/views.py (NotificationViewSet)
#        notifications/serializers.py (NotificationSerializer) + notifications/admin.py (NotificationAdmin)
#        project/settings/base.py CACHES (for unread cache)

# In notifications/tasks.py — delete:
#   send_multicast_notifications_task  tasks.py:39-74
#   clean_up_invalid_tokens           tasks.py:77-83
#   _dispatch_push_notification       tasks.py:139-151
# In create_notification_task tasks.py:86-125 — delete line :121-123:
#   _dispatch_push_notification(user, title, body, {...})
# Keep: Notification.objects.create + cache invalidation.

# Optional: keep Device model + DeviceViewSet only if you need device registry for future APNS/other push.
# Else delete:
#   notifications/models.py:70-114 Device + DevicePlatform
#   notifications/views.py:68-111 DeviceViewSet
#   notifications/serializers.py:29-53 DeviceSerializer + DeviceRegisterSerializer
#   notifications/urls.py:10 router.register("devices")
#   notifications/admin.py:17-28 DeviceAdmin
#   unfold_config.py:374-378 Devices item
#   Run: python manage.py makemigrations notifications && python manage.py migrate
```

After either removal, run:

```bash
make check-format && make test
```

---

## 17. Verification & Troubleshooting

### Quick checks

```bash
# App loads without notifications
python manage.py check

# Migrations clean
python manage.py makemigrations --dry-run --check

# Tests (should_notify + inbox)
pytest tests/ -k "notification or should_notify" -v  # tests/test_smoke.py:50-58

# Cache reachable
python manage.py shell -c "from django.core.cache import cache; cache.set('ping','pong',10); print(cache.get('ping'))"
# → pong

# Beat sees the job
celery -A project beat --dry-run  # or check admin:django_celery_beat_periodictask_changelist  unfold_config.py:517-519
```

### Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `FCM not configured` in logs `tasks.py:43` | `firebase-admin` not installed or `GOOGLE_APPLICATION_CREDENTIALS` not set | `pip install firebase-admin` + set `GOOGLE_APPLICATION_CREDENTIALS=./firebase-adminsdk.json` `.env.example:85` + restart worker |
| `firebase_admin not installed — skipping` `tasks.py:43` | `HAS_FCM = False` `tasks.py:28` | Same as above — inbox still works, push skipped |
| `No tokens provided` `tasks.py:46` | User has no active `Device` rows | Client must `POST /devices/` `views.py:78` after login. Check `Device.objects.filter(user=user, is_active=True)` `tasks.py:143` |
| `Sent 0 notifications. Failed: N` `tasks.py:74` | Tokens invalid/expired | `clean_up_invalid_tokens` `tasks.py:72` deletes them; client re-registers on next launch |
| `unread_count` stale | Cache 300s `tasks.py:186` | Normal — invalidated on writes `tasks.py:170,173`. For immediate consistency, call `_invalidate_unread_count_cache` manually or reduce TTL |
| `unique_user_device` constraint error | Duplicate `(user, device_uuid)` `models.py:110` | Use `update_or_create` `views.py:87` — never raw `create`. Ensure `device_uuid` is stable per install |
| `ModuleNotFoundError: notifications` after removal | Forgot to remove `INSTALLED_APPS` `base.py:68` or `project/urls.py:41` | Remove both + `unfold_config.py:366-379` |
| `ImproperlyConfigured: Token has wrong type` | Using refresh token as access | Refresh via `POST /api/v1/users/token/refresh/` with `refresh_token` cookie `accounts/views.py:52-70` |

### Where to look

- **Worker logs:** `docker compose logs celery_worker -f` — look for `Sent X notifications` `tasks.py:74` / `Cleaned N invalid tokens` `tasks.py:83` / `Cleaned N old notifications` `tasks.py:135`.
- **Admin:** Unfold → Notifications → User Notifications (`admin:notifications_notification_changelist` `unfold_config.py:371`) + Devices (`admin:notifications_device_changelist` `378`) — inspect `is_read`, `is_active`, `last_seen_at` `admin.py:12,24`.
- **Cache:** `redis-cli -n 1 keys "notifications:unread:*"` — per-user unread keys `tasks.py:180`.
- **DB:** `Notification.objects.filter(user=user, is_read=False).count()` vs `get_unread_count(str(user.id))` `tasks.py:176` — counts must converge after cache expiry.

---

> **Django Rapido V2.0** — Notifications are generic infrastructure. Extend `NotificationType` `models.py:21-30`, copy `notify_welcome` `tasks.py:157-167` per domain event, and dispatch via `create_notification_task.delay` `tasks.py:86` from any view/service/signal. Inbox always; push when devices exist.