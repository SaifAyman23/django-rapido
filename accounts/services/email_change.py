"""Email change with OTP proof of control (QOOT-012, service only for now)."""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.models import EmailOTP
from accounts.services.accounts import primary_account
from accounts.services.guards import ensure_email_available_for_change
from accounts.services.otp import issue_otp, queue_otp_email, verify_otp
from common.exceptions import AccountNotFoundError, InvalidCodeError

logger = logging.getLogger(__name__)
User = get_user_model()


def _resolve_account(user, account=None):
    """Return the account whose login email changes (defaults to the primary)."""
    target = account or primary_account(user)
    if target is None:
        # Nothing to change; stop before issuing a code or sending mail.
        raise AccountNotFoundError()
    return target


def request_email_change(user, new_email: str, *, account=None):
    """Issue a CHANGE_EMAIL code for ``new_email`` (stored in OTP metadata)."""
    new_email = (new_email or "").strip().lower()
    target_account = _resolve_account(user, account)
    ensure_email_available_for_change(user, new_email, account=target_account)

    with transaction.atomic():
        otp = issue_otp(
            user,
            EmailOTP.Purpose.CHANGE_EMAIL,
            email=new_email,
            enforce_cooldown=False,
            metadata={"new_email": new_email},
        )
        transaction.on_commit(lambda: queue_otp_email(otp))
    return otp


def confirm_email_change(user, code: str, *, account=None, new_email=None, keep_refresh="") -> str:
    """Consume the code and move the target Account (and User) to the new email."""
    requested = (new_email or "").strip().lower()
    otp = verify_otp(user, EmailOTP.Purpose.CHANGE_EMAIL, code)
    new_email_from_metadata = (otp.metadata or {}).get("new_email", "").strip().lower()
    if not new_email_from_metadata:
        raise InvalidCodeError()
    if requested and requested != new_email_from_metadata:
        raise InvalidCodeError()

    new_email = new_email_from_metadata
    target_account = _resolve_account(user, account)
    ensure_email_available_for_change(user, new_email, account=target_account)

    now = timezone.now()
    with transaction.atomic():
        target_account.email = new_email
        target_account.is_email_verified = True
        target_account.verified_at = now
        target_account.save(
            update_fields=["email", "is_email_verified", "verified_at", "updated_at"]
        )

        # The oldest account owns ``User.email`` (admin / allauth identity).
        primary = primary_account(user)
        if primary is not None and primary.pk == target_account.pk:
            user.email = new_email
            user.is_verified = True
            user.verified_at = now
            user.save(update_fields=["email", "is_verified", "verified_at", "updated_at"])

    from accounts.services.tokens import blacklist_other_refresh_tokens

    blacklist_other_refresh_tokens(user, keep_raw_token=keep_refresh)
    logger.info("Email changed user=%s account=%s", user.pk, target_account.pk)
    return new_email
