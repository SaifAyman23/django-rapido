"""Password reset (QOOT-002) — OTP request + confirm, no tokens involved."""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.models import EmailOTP
from accounts.services.accounts import resolve_login_identity
from accounts.services.otp import issue_otp, queue_otp_email, seconds_until_resend, verify_otp
from accounts.services.tokens import blacklist_all_refresh_tokens
from common.exceptions import InvalidCodeError

logger = logging.getLogger(__name__)
User = get_user_model()


def request_password_reset(email: str) -> None:
    """Send a RESET_PASSWORD code when an Account or User email exists.

    Anti-enumeration: the caller always returns the same neutral message.
    Within the 60-second cooldown nothing is sent (still neutral); beyond the
    hourly cap ``ThrottledError`` propagates so the client sees ``429``.
    """
    email = (email or "").strip().lower()
    user, _account = resolve_login_identity(email)
    if user is None or not user.is_active or user.status == User.Status.SUSPENDED:
        return

    purpose = EmailOTP.Purpose.RESET_PASSWORD
    if seconds_until_resend(user, purpose, email=email) > 0:
        return

    otp = issue_otp(user, purpose, email=email, enforce_cooldown=False)
    queue_otp_email(otp)


def confirm_password_reset(*, email: str, code: str, new_password: str) -> None:
    """Validate the code, set the shared User password, end every session.

    ``verify_otp`` runs outside the transaction so a wrong code still persists
    its attempt counter. The password belongs to the User, so resetting from
    any verified account email resets the one shared password.
    """
    email = (email or "").strip().lower()
    user, account = resolve_login_identity(email)
    if user is None:
        raise InvalidCodeError()

    verify_otp(user, EmailOTP.Purpose.RESET_PASSWORD, code, email=email)

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        user.set_password(new_password)
        # Proving mailbox control also verifies the email (QOOT-002 §2.6).
        if not user.is_verified:
            user.is_verified = True
            user.verified_at = timezone.now()
        if user.status == User.Status.UNVERIFIED:
            user.status = User.Status.ACTIVE
        user.save(update_fields=["password", "is_verified", "verified_at", "status", "updated_at"])

        if account is not None:
            account = type(account).objects.select_for_update().get(pk=account.pk)
            if not account.is_email_verified or not account.email:
                account.email = account.email or email
                account.is_email_verified = True
                account.verified_at = account.verified_at or timezone.now()
                account.save(
                    update_fields=[
                        "email",
                        "is_email_verified",
                        "verified_at",
                        "updated_at",
                    ]
                )

        blacklist_all_refresh_tokens(user)

    logger.info("Password reset completed user=%s", user.pk)
