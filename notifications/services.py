"""
REUSE: Notification guard — checks if user wants push.

Django Rapido — notification services. Reusable.

Wire: if not should_notify(user): skip send
"""

from django.contrib.auth import get_user_model

User = get_user_model()


def should_notify(user) -> bool:
    """Return False if user opted out (notifications_enabled=False) or inactive."""
    if not user or not user.is_active:
        return False
    return getattr(user, "notifications_enabled", True)


from typing import TYPE_CHECKING

from django.db import transaction


def notify(user, *, type, title, body, data=None, scheduled_at=None, account=None) -> Notification:
    """Sole entry point for creating notifications.

    Inserts the in-app row and, when ``scheduled_at`` is empty/due, queues
    ``send_push`` via ``transaction.on_commit``. Other apps must call this and
    nothing else. Push sending is a placeholder until Expo credentials land
    (see TODO below). ``account`` (if given) is recorded in ``data`` so the
    app can route the push to the right account context.
    """
    from .models import Notification
    from .tasks import send_push

    payload = dict(data or {})
    if account is not None and "account_id" not in payload:
        payload["account_id"] = str(getattr(account, "id", account))

    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        body=body,
        data=payload,
        scheduled_at=scheduled_at,
    )
    if scheduled_at is None:
        transaction.on_commit(lambda: send_push.delay(str(notification.id)))
    return notification
