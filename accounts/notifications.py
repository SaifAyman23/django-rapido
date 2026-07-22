"""
Notification helpers — email delivery and preference checks.

All email-sending implementations live in common.helpers;
this module provides a thin re-export layer plus should_notify().
"""

import logging
from typing import List

from django.conf import settings
from django.contrib.auth import get_user_model

from common.helpers import (
    send_template_email as _send_template_email,
    send_password_reset_email as _send_password_reset_email,
    send_verification_email as _send_verification_email,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def send_template_email(
    subject: str,
    template_name: str,
    context: dict,
    recipient_list: List[str],
    from_email=None,
) -> bool:
    """Send an HTML email using a Django template."""
    return _send_template_email(subject, template_name, context, recipient_list, from_email)


def send_verification_email(user, token: str, base_url: str) -> bool:
    """Send email verification link."""
    return _send_verification_email(user, token, base_url)


def send_password_reset_email(user, base_url: str) -> bool:
    """Send password reset link."""
    return _send_password_reset_email(user, base_url)


def should_notify(recipient_user) -> bool:
    """Check if the user has enabled email notifications."""
    if not recipient_user or not recipient_user.is_active:
        return False
    if hasattr(recipient_user, "notification_preferences"):
        prefs = recipient_user.notification_preferences
        if prefs is not None and prefs.get("email_enabled") is False:
            return False
    return True
