"""
REUSE: Generic FCM push tasks — batched multicast, DB inbox, cleanup.

From ras-elbar-go/backend/notifications/tasks.py — made project-agnostic.

Usage:
    from notifications.tasks import create_notification_task
    create_notification_task.delay(str(user.id), "welcome", "Title", "Body", str(order.id), "order")

    # Or directly:
    from notifications.tasks import notify_welcome
    notify_welcome.delay(str(user.id))
"""

import logging
from datetime import timedelta
from typing import Optional

from celery import shared_task
from django.contrib.auth import get_user_model
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
def send_multicast_notifications_task(registration_tokens, title, body, data_payload=None):
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
def clean_up_invalid_tokens(failed_tokens):
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
):
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
def cleanup_old_notifications():
    """REUSE: Beat weekly — delete >90d notifications."""
    cutoff = timezone.now() - timedelta(days=90)
    from notifications.models import Notification

    deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    logger.info(f"Cleaned {deleted_count} old notifications")
    return {"deleted": deleted_count}


def _dispatch_push_notification(user, title: str, body: str, data: dict):
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
def notify_welcome(self, user_id: str):
    """REUSE: Welcome after verification — adapt title/body per project."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"status": "skipped", "reason": "user_not_found"}
    if not should_notify(user):
        return {"status": "skipped", "reason": "notifications_disabled"}
    create_notification_task.delay(user_id, "welcome", _("Welcome!"), _("Thanks for joining."))
    return {"status": "dispatched"}


def _invalidate_unread_count_cache(user_id: str):
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
