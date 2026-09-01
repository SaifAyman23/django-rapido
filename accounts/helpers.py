"""
Auth helpers — credentials + OTP.

REUSE: Generic helpers for any project. No role hardcoding.
From ras-elbar-go/backend/accounts/helpers.py (made project-agnostic).
"""

import random
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from .models import OTPRecord


def validate_credentials(email, password):
    """Validate email/password and return user.

    REUSE: This is project-agnostic. If your project has roles
    (e.g. customer/seller/admin), wrap this with an extra check:

        user = validate_credentials(email, password)
        if user.role != "admin":
            raise ValidationError(...)

    Checks: empty, wrong password, SUSPENDED, UNVERIFIED (if applicable).
    """
    User = get_user_model()

    if not email or not password:
        raise serializers.ValidationError({"detail": _("Please fill in all fields")})

    user = User.objects.filter(email=email).first()

    if not user or not user.check_password(password):
        raise serializers.ValidationError({"detail": _("Incorrect email or password")})

    if user.status == User.Status.SUSPENDED:
        raise serializers.ValidationError(
            {"detail": _("Your account has been suspended. Contact support.")}
        )

    if getattr(user, "is_banned", False):
        raise serializers.ValidationError(
            {"detail": _("Your account has been suspended. Contact support.")}
        )

    # REUSE: Gate unverified users if your project requires email verification.
    # Requires CustomUser.is_verified BooleanField. Comment out if not needed.
    if hasattr(user, "is_verified") and hasattr(user, "status"):
        # Only gate if user has a Customer-like role — optional
        role = getattr(user, "role", None)
        # If role field exists and is not staff, require verification
        if (
            role is None
            or role == getattr(User, "Role", None)
            and getattr(User.Role, "CUSTOMER", None) == role
        ):
            if not user.is_verified and user.status == User.Status.UNVERIFIED:
                raise serializers.ValidationError(
                    {"detail": _("Please verify your email before logging in.")}
                )

    return user


# ─────────────────────────────────────────────────────────────────
# OTP helpers — REUSE: Generic email-verification engine
# ─────────────────────────────────────────────────────────────────


def generate_otp():
    """Generate a random 6-digit OTP. REUSE: no dependencies."""
    return str(random.randint(100000, 999999))


def generate_password_reset_token():
    """Generate a 43-char urlsafe token. REUSE: for link-based reset."""
    return secrets.token_urlsafe(32)


def create_and_send_otp(user, otp_type="email_verification", expiry_minutes=10):
    """Create OTPRecord and synchronously send email.

    REUSE: For async email, replace direct call with Celery:
        from .tasks import send_verification_email
        send_verification_email.delay(user.id, user.email, otp)

    expiry_minutes: how long the code stays valid (default 10).
    Returns the created OTPRecord.
    """
    from .tasks import send_verification_email  # lazy import to avoid cycle

    otp = generate_otp()
    otp_record = OTPRecord.objects.create(
        user=user,
        otp=otp,
        type=otp_type,
        expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
    )
    # Sync send — swap to .delay() for Celery
    try:
        send_verification_email(user.id, user.email, otp)
    except Exception:
        # Call directly if Celery not available (e.g. eager mode)
        from .tasks import send_verification_email as sync_send

        sync_send(user.id, user.email, otp)
    return otp_record


def validate_otp(code, purpose=None, max_attempts=5):
    """Validate OTP code. Returns OTPRecord if valid, else raises.

    REUSE: purpose should match OTPType (email_verification/password_reset).
    Locks attempts via F() to prevent race.
    """
    otp_record = (
        OTPRecord.objects.filter(
            otp=code,
            type=purpose or OTPRecord.OTPType.EMAIL_VERIFICATION,
            is_used=False,
            expires_at__gte=timezone.now(),
        )
        .select_related("user")
        .first()
    )
    if not otp_record:
        raise serializers.ValidationError({"code": _("Invalid or expired verification code.")})
    if otp_record.attempts >= max_attempts:
        raise serializers.ValidationError({"code": _("Too many attempts. Request a new code.")})
    OTPRecord.objects.filter(id=otp_record.id).update(attempts=models.F("attempts") + 1)
    otp_record.refresh_from_db()
    return otp_record
