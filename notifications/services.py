"""
REUSE: Notification guard — checks if user wants push.

From ras-elbar-go/backend/notifications/services.py

Wire: if not should_notify(user): skip send
"""

from django.contrib.auth import get_user_model

User = get_user_model()


def should_notify(user) -> bool:
    """Return False if user opted out (notifications_enabled=False) or inactive."""
    if not user or not user.is_active:
        return False
    return getattr(user, "notifications_enabled", True)
