"""
Generic OTP + password-reset models for email verification.

Django Rapido — OTP & password-reset models. Reusable, project-agnostic — copy verbatim for any email verification flow.
No role-specific logic.

Usage:
    from accounts.helpers import create_and_send_otp, validate_otp
    otp_record = create_and_send_otp(user, otp_type="email_verification")
    otp_record = validate_otp(code, purpose="email_verification")

Expiry: 10 minutes default, max_attempts 5.
"""

from django.conf import settings
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


class Account(TimestampedModel, UUIDModel):
    """A role-specific account owned by one Django User.

    The Account — not the User — is the authorization and data boundary.
    Role is immutable after creation; creating another role means creating
    another Account for the same User (QOOT-001 §2.3). The same role may be
    created more than once; each Account has its own login email.
    """

    class Role(models.TextChoices):
        CLIENT = "client", _("Client")
        COACH = "coach", _("Coach")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts",
        help_text=_("The person identity that owns this account"),
    )
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "Login email for this account. Unique across accounts; NULL for legacy "
            "secondary accounts that have not added an email yet."
        ),
    )
    is_email_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether this account's email proved ownership"),
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this account's email was verified"),
    )
    role = models.CharField(max_length=10, choices=Role.choices, db_index=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Account-level lifecycle state"),
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        help_text=_("Profile image for this account"),
    )

    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["user", "role"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.email or self.user_id} - {self.role}"

    @property
    def display_email(self) -> str:
        """Login email shown by the API, falling back to the person identity."""
        return self.email or self.user.email

    @property
    def profile(self):
        """No role-specific profile in this base."""
        return None

    @property
    def has_profile(self) -> bool:
        """Onboarding gate is permissive by default in this base."""
        return True

    @property
    def full_name(self) -> str:
        """Name shown in the account switcher; falls back to the person identity."""
        profile = self.profile
        if profile is not None and profile.full_name:
            return profile.full_name
        return self.user.get_full_name() or self.user.email.split("@")[0]


class EmailOTP(TimestampedModel, UUIDModel):
    """Single-use 6-digit code for email verification, reset, add-account, or email change.

    Only the HMAC-SHA256 hash of the code is stored. The newest unconsumed row
    for ``(user, email, purpose)`` is the only valid code, because issuing a new
    code stamps ``consumed_at`` on every earlier unconsumed row of the same scope.
    """

    class Purpose(models.TextChoices):
        VERIFY_EMAIL = "verify_email", _("Verify Email")
        RESET_PASSWORD = "reset_password", _("Reset Password")
        CHANGE_EMAIL = "change_email", _("Change Email")
        ADD_ACCOUNT = "add_account", _("Add Account")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otps",
    )
    email = models.EmailField(
        blank=True,
        default="",
        db_index=True,
        help_text=_("Target mailbox for this code (an Account email or a new email)"),
    )
    purpose = models.CharField(max_length=20, choices=Purpose.choices, db_index=True)
    code_hash = models.CharField(max_length=64, help_text=_("HMAC-SHA256 of the code"))
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Flow-specific payload, e.g. the requested role or pending email"),
    )

    class Meta:
        verbose_name = _("Email OTP")
        verbose_name_plural = _("Email OTPs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "email", "purpose", "-created_at"]),
        ]

    def __str__(self) -> str:
        target = self.email or self.user_id
        return f"{target} - {self.purpose} ({self.created_at:%Y-%m-%d %H:%M})"

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    @property
    def is_locked(self) -> bool:
        return self.attempts >= settings.OTP_MAX_ATTEMPTS


class SocialAccountLink(TimestampedModel, UUIDModel):
    """Remember which Account a provider identity signs in to.

    allauth's ``SocialAccount`` is person-wide (``User``); Qoot authenticates a
    specific Account, and Apple only returns the email on the first consent.
    This binding gives every later provider login a stable Account.
    """

    social_account = models.OneToOneField(
        "socialaccount.SocialAccount",
        on_delete=models.CASCADE,
        related_name="qoot_link",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="social_links",
    )

    class Meta:
        verbose_name = _("Social Account Link")
        verbose_name_plural = _("Social Account Links")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account"]),
        ]

    def __str__(self) -> str:
        return f"{self.social_account.provider} -> {self.account_id}"
