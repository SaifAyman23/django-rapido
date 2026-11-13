"""
REUSE: Generic FCM push tasks — batched multicast, DB inbox, cleanup.

Django Rapido — notification tasks. Reusable, project-agnostic.

Usage:
    from notifications.tasks import create_notification_task
    create_notification_task.delay(str(user.id), "welcome", "Title", "Body", str(order.id), "order")

    # Or directly:
    from notifications.tasks import notify_welcome
    notify_welcome.delay(str(user.id))
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

try:
    from firebase_admin import messaging

    HAS_FCM = True
except ImportError:
    HAS_FCM = False

from .services import should_notify

logger = logging.getLogger(__name__)
User = get_user_model()

FCM_BATCH_LIMIT = 500


@shared_task
def send_multicast_notifications_task(registration_tokens, title, body, data_payload=None) -> dict:
    """Send to 500-token batches via FCM. REUSE: handles token cleanup on failure."""
    if not HAS_FCM:
        logger.warning("firebase_admin not installed — skipping FCM send")
        return "FCM not configured"
    if not registration_tokens:
        return "No tokens provided"

    total_success = 0
    total_failure = 0
    all_failed_tokens = []

    for i in range(0, len(registration_tokens), FCM_BATCH_LIMIT):
        batch = registration_tokens[i : i + FCM_BATCH_LIMIT]
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data_payload or {},
            tokens=batch,
        )
        try:
            response = messaging.send_each_for_multicast(message)
            total_success += response.success_count
            total_failure += response.failure_count
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        all_failed_tokens.append(batch[idx])
        except Exception as e:
            logger.error(f"FCM multicast batch failed: {e}")
            total_failure += len(batch)

    if all_failed_tokens:
        clean_up_invalid_tokens.delay(all_failed_tokens)

    return f"Sent {total_success} notifications. Failed: {total_failure}"


@shared_task
def clean_up_invalid_tokens(failed_tokens) -> dict:
    """REUSE: Remove stale tokens — app will re-register on next launch."""
    from notifications.models import Device

    deleted_count, _ = Device.objects.filter(token__in=failed_tokens).delete()
    return f"Cleaned {deleted_count} invalid tokens."


@shared_task(bind=True)
def create_notification_task(
    self,
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    related_object_id: Optional[str] = None,
    related_object_type: Optional[str] = None,
) -> dict:
    """Create DB notification + dispatch FCM.

    REUSE: Generic — pass any NotificationType string. Checks should_notify() first.
    Invalidates unread cache notifications:unread:{user_id}.
    """
    from notifications.models import Notification

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"status": "skipped", "reason": "user_not_found"}

    if not should_notify(user):
        return {"status": "skipped", "reason": "notifications_disabled"}

    notification = Notification.objects.create(
        user=user,
        type=notification_type,
        title=title,
        body=body,
        related_object_id=related_object_id,
        related_object_type=related_object_type,
    )

    _invalidate_unread_count_cache(user_id)
    _dispatch_push_notification(
        user, title, body, {"type": notification_type, "related_id": related_object_id or ""}
    )

    return {"status": "created", "notification_id": str(notification.id)}


@shared_task
def cleanup_old_notifications() -> dict:
    """REUSE: Beat weekly — delete >90d notifications."""
    cutoff = timezone.now() - timedelta(days=90)
    from notifications.models import Notification

    deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    logger.info(f"Cleaned {deleted_count} old notifications")
    return {"deleted": deleted_count}


def _dispatch_push_notification(user, title: str, body: str, data: dict) -> dict:
    """Send to user's active devices via multicast task."""
    from notifications.models import Device

    tokens = list(
        Device.objects.filter(user=user, is_active=True, notifications_enabled=True).values_list(
            "token", flat=True
        )
    )
    if not tokens:
        return {"status": "no_tokens"}
    send_multicast_notifications_task.delay(tokens, title, body, data)
    return {"status": "dispatched"}


# ── Example notification tasks — REUSE: copy pattern per event ──


@shared_task(bind=True)
def notify_welcome(self, user_id: str) -> dict:
    """REUSE: Welcome after verification — adapt title/body per project."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"status": "skipped", "reason": "user_not_found"}
    if not should_notify(user):
        return {"status": "skipped", "reason": "notifications_disabled"}
    create_notification_task.delay(user_id, "welcome", _("Welcome!"), _("Thanks for joining."))
    return {"status": "dispatched"}


def _invalidate_unread_count_cache(user_id: str) -> None:
    from django.core.cache import cache

    cache.delete(f"notifications:unread:{user_id}")


def get_unread_count(user_id: str) -> int:
    """REUSE: Cached unread count — TTL 5m."""
    from django.core.cache import cache

    cache_key = f"notifications:unread:{user_id}"
    count = cache.get(cache_key)
    if count is None:
        from notifications.models import Notification

        count = Notification.objects.filter(user_id=user_id, is_read=False).count()
        cache.set(cache_key, count, 300)
    return count


# ---------------------------------------------------------------------------
# Expo Push delivery (QOOT-010) - placeholders with TODO for credentials.
# TODO(creds): set EXPO_ACCESS_TOKEN env var and upload FCM/APNs credentials
# via EAS before enabling real push. Until then send_push is a no-op that
# marks the notification SENT so in-app flow keeps working.
# ---------------------------------------------------------------------------


@shared_task
def send_push(notification_id: str) -> dict:
    """Deliver one notification via Expo Push (placeholder).

    Real implementation: load the notification + active devices, chunk tokens
    into groups of settings.PUSH_CHUNK (100), POST to
    https://exp.host/--/api/v2/push/send with Authorization: Bearer
    <EXPO_ACCESS_TOKEN>, store ticket ids, set delivery_status.
    """
    from notifications.models import Notification

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return {"status": "not_found"}

    # Global mute: still in-app, skip push.
    muted = False
    account_id = (notification.data or {}).get("account_id")
    if account_id:
        from accounts.models import Account

        account = Account.objects.filter(pk=account_id, user=notification.user).first()
        if account is not None:
            profile = account.profile
            muted = bool(getattr(profile, "notifications_muted", False))
    if muted or not should_notify(notification.user):
        notification.delivery_status = "SKIPPED"
        notification.save(update_fields=["delivery_status", "updated_at"])
        return {"status": "skipped_muted"}

    # TODO(creds): replace with real Expo push call.
    # Real implementation steps:
    #   1. Load active devices for notification.user (filter is_active=True).
    #   2. Chunk tokens into groups of settings.PUSH_CHUNK (100).
    #   3. POST to https://exp.host/--/api/v2/push/send with
    #      Authorization: Bearer <EXPO_ACCESS_TOKEN>, body PushMessage list
    #      (title, body, data={type, notification_id, account_id, ...}).
    #   4. Store ticket ids in notification.push_ticket_ids.
    #   5. Set delivery_status = SENT; on DeviceNotRegistered deactivate token;
    #      on error retry 3x with backoff then FAILED.
    notification.delivery_status = "SENT"
    notification.save(update_fields=["delivery_status", "updated_at"])
    return {"status": "sent_placeholder"}


@shared_task
def dispatch_due_notifications() -> dict:
    """Beat (1 min): queue send_push for due PENDING notifications."""
    from notifications.models import Notification

    due = Notification.objects.filter(delivery_status="PENDING", scheduled_at__lte=timezone.now())
    for n in due:
        send_push.delay(str(n.id))
    return {"queued": due.count()}


@shared_task
def check_push_receipts() -> dict:
    """Beat (15 min): deactivate DeviceNotRegistered tokens (placeholder)."""
    # TODO(creds): fetch Expo receipts by push_ticket_ids and deactivate dead tokens.
    return {"status": "placeholder"}


@shared_task
def schedule_meal_reminders() -> dict:
    """Hourly beat: create MEAL_REMINDER notifications for slots with default_time.

    Idempotent per (source=meal:{slot_id}, user, local_date): a beat restart
    never double-sends. Skips slots that already have a logged entry today.
    """
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    from django.utils import timezone

    from meals.models import Meal, MealSlot
    from notifications.models import Notification
    from notifications.services import notify

    created = 0
    slots = MealSlot.objects.filter(is_active=True, default_time__isnull=False).select_related(
        "account", "account__user"
    )
    for slot in slots.iterator():
        account = slot.account
        if account is None or not account.is_active:
            continue
        user = account.user
        if not user.is_active:
            continue
        # timezone from client profile (fallback Cairo)
        tz_name = "Africa/Cairo"
        try:
            tz_name = account.client_profile.timezone
        except ObjectDoesNotExist:
            import logging

            logging.getLogger(__name__).debug("client profile timezone unavailable", exc_info=True)
            try:
                tz_name = account.coach_profile.timezone
            except ObjectDoesNotExist:
                logging.getLogger(__name__).debug(
                    "coach profile timezone unavailable", exc_info=True
                )
        try:
            tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            tz = ZoneInfo("Africa/Cairo")
        now_local = timezone.now().astimezone(tz)
        today = now_local.date()
        scheduled = datetime.combine(today, slot.default_time, tzinfo=tz)
        # only materialize reminders whose time falls in the coming hour
        if scheduled < now_local or scheduled > now_local + timedelta(hours=1):
            continue
        # skip if slot already logged today
        if Meal.objects.filter(account=account, slot=slot, logged_date=today).exists():
            continue
        source = f"meal:{slot.id}"
        # idempotency
        if Notification.objects.filter(
            user=user, type="MEAL_REMINDER", scheduled_at__date=today, data__source=source
        ).exists():
            continue
        notify(
            user,
            type="MEAL_REMINDER",
            title=slot.name or "Meal reminder",
            body=f"Time for {slot.name}",
            data={"slot_id": str(slot.id), "source": source},
            scheduled_at=scheduled,
        )
        created += 1
    return {"created": created}


@shared_task
def schedule_custom_reminders() -> dict:
    """Hourly beat: create CUSTOM_REMINDER notifications for due reminders."""
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    from django.utils import timezone

    from notifications.models import CustomReminder, Notification
    from notifications.services import notify

    created = 0
    for reminder in (
        CustomReminder.objects.filter(is_active=True).select_related("user", "account").iterator()
    ):
        user = reminder.user
        if not user.is_active:
            continue
        account = reminder.account
        tz_name = "Africa/Cairo"
        if account is not None:
            try:
                tz_name = account.client_profile.timezone
            except ObjectDoesNotExist:
                import logging

                logging.getLogger(__name__).debug(
                    "client profile timezone unavailable", exc_info=True
                )
                try:
                    tz_name = account.coach_profile.timezone
                except ObjectDoesNotExist:
                    logging.getLogger(__name__).debug(
                        "coach profile timezone unavailable", exc_info=True
                    )
        try:
            tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            tz = ZoneInfo("Africa/Cairo")
        now_local = timezone.now().astimezone(tz)
        today = now_local.date()
        # weekday index 0=Sat..6=Fri
        weekday_idx = (today.weekday() + 2) % 7
        days = reminder.days_of_week or []
        if days and weekday_idx not in days:
            continue
        scheduled = datetime.combine(today, reminder.time, tzinfo=tz)
        if scheduled < now_local or scheduled > now_local + timedelta(hours=1):
            continue
        source = f"custom:{reminder.id}"
        if Notification.objects.filter(
            user=user, type="CUSTOM_REMINDER", scheduled_at__date=today, data__source=source
        ).exists():
            continue
        notify(
            user,
            type="CUSTOM_REMINDER",
            title=reminder.name,
            body=reminder.name,
            data={"reminder_id": str(reminder.id), "source": source},
            scheduled_at=scheduled,
        )
        created += 1
    return {"created": created}


@shared_task
def schedule_ramadan_water(user_id: str, target_date: str) -> dict:
    """Create one local sunset reminder for a Ramadan day."""
    from datetime import date
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    from astral import LocationInfo
    from astral.sun import sun

    from accounts.models import Account
    from notifications.models import Notification
    from notifications.services import notify

    try:
        user = User.objects.get(pk=user_id, is_active=True)
        day = date.fromisoformat(target_date)
    except (User.DoesNotExist, ValueError):
        return {"status": "skipped", "reason": "invalid_user_or_date"}

    account = Account.objects.filter(user=user, is_active=True).first()
    if account is None:
        return {"status": "skipped", "reason": "account_not_found"}
    profile = account.profile
    if getattr(profile, "fasting_mode", None) != "ramadan":
        return {"status": "skipped", "reason": "ramadan_disabled"}
    if profile.fasting_lat is None or profile.fasting_lon is None:
        return {"status": "skipped", "reason": "location_missing"}

    tz_name = getattr(profile, "timezone", "Africa/Cairo")
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("Africa/Cairo")
        tz_name = "Africa/Cairo"
    location = LocationInfo(
        name=profile.fasting_city or "Qoot",
        region="",
        timezone=tz_name,
        latitude=float(profile.fasting_lat),
        longitude=float(profile.fasting_lon),
    )
    sunset = sun(location.observer, date=day, tzinfo=tz)["sunset"]
    source = f"ramadan:{account.id}:{day.isoformat()}"
    if Notification.objects.filter(user=user, type="REMINDER", data__source=source).exists():
        return {"status": "duplicate"}
    notify(
        user,
        type="REMINDER",
        title="Sunset reminder",
        body="Iftar time is near. Remember to hydrate after sunset.",
        data={"source": source, "account_id": str(account.id)},
        scheduled_at=sunset,
        account=account,
    )
    return {"status": "created", "scheduled_at": sunset.isoformat()}
