"""
Generic OTP + password-reset models for email verification.

REUSE: This module is project-agnostic. Any project needing email
verification or password-reset via OTP/token can copy it verbatim.
No role-specific logic. From ras-elbar-go/backend/accounts/models.py

Usage:
    from accounts.helpers import create_and_send_otp, validate_otp
    otp_record = create_and_send_otp(user, otp_type="email_verification")
    otp_record = validate_otp(code, purpose="email_verification")

Expiry: 10 minutes default, max_attempts 5.
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import TimestampedModel, UUIDModel

User = get_user_model()


class OTPRecord(TimestampedModel, UUIDModel):
    """One-time code for email verification or password reset.

    REUSE: Works with any CustomUser. Type field lets you reuse the
    same table for multiple flows (email_verify, password_reset, etc.).
    Index on (otp, type, expires_at) is handled at query time.
    """

    class OTPType(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", _("Email Verification")
        PASSWORD_RESET = "password_reset", _("Password Reset")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_records")
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    type = models.CharField(max_length=20, choices=OTPType.choices)
    attempts = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("OTP Record")
        verbose_name_plural = _("OTP Records")
        indexes = [
            models.Index(fields=["otp", "type", "expires_at"]),
            models.Index(fields=["user", "type"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.otp} ({self.type})"


class PasswordResetToken(TimestampedModel, UUIDModel):
    """Long-lived token for password reset link (alternative to OTP).

    REUSE: Use this when you want a clickable link instead of a 6-digit code.
    Generate via helpers.generate_password_reset_token() which uses
    secrets.token_urlsafe(32) → 43 chars, store max 256.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.CharField(max_length=256, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(
        default=0, help_text=_("Consecutive reset attempts using this token")
    )

    class Meta:
        verbose_name = _("Password Reset Token")
        verbose_name_plural = _("Password Reset Tokens")

    def __str__(self):
        return f"{self.user.email} - {self.id}"
