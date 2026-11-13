"""Login and email-verification services (QOOT-001).

- Login resolves ``Account.email`` first, then falls back to ``User.email`` plus
  the primary Account, and issues tokens for exactly one Account.
- ``verify_email`` proves mailbox control for that Account, flips it to
  verified, and only then issues the first token pair.
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.models import EmailOTP
from accounts.services.accounts import get_account_for_user, resolve_login_identity
from accounts.services.guards import ensure_account_enabled, ensure_user_enabled
from accounts.services.otp import verify_otp
from accounts.services.tokens import build_token_pair
from common.exceptions import AccountNotFoundError, EmailNotVerifiedError, InvalidCredentialsError

logger = logging.getLogger(__name__)
User = get_user_model()


def check_credentials(*, email: str, password: str):
    """Validate email/password and return ``(user, resolved_account)``.

    The email is an Account login identifier first, so a secondary account can
    sign in with its own email and the person's one shared password. One generic
    ``INVALID_CREDENTIALS`` message covers unknown email, wrong password, and
    social-only accounts (no usable password).
    """
    user, account = resolve_login_identity(email)

    if user is None or not user.has_usable_password() or not user.check_password(password):
        raise InvalidCredentialsError()

    # Shared guards keep disabled-person/disabled-account handling identical to
    # social login and email change.
    ensure_user_enabled(user)
    ensure_account_enabled(account)

    return user, account


def authenticate_user(*, email: str, password: str, account_id=None):
    """Validate credentials and return ``(user, account)`` for a verified Account."""
    user, resolved = check_credentials(email=email, password=password)

    if not user.is_verified:
        raise EmailNotVerifiedError()

    selected_id = account_id or (resolved.pk if resolved is not None else None)
    account = get_account_for_user(user, selected_id, required=True)
    if not account.is_email_verified:
        raise EmailNotVerifiedError()

    return user, account


def login_user(*, email: str, password: str, account_id=None) -> dict:
    """Authenticate and return ``{user, account, access, refresh}``."""
    user, account = authenticate_user(email=email, password=password, account_id=account_id)
    tokens = build_token_pair(user, account)
    return {"user": user, "account": account, **tokens}


def verify_email(user, code: str, account_id=None, email=None) -> dict:
    """Consume the verification code, mark the Account/User verified, issue tokens.

    Not decorated with ``@transaction.atomic``: ``verify_otp`` must be able to
    persist a failed-attempt counter before the 422 is raised.
    """
    target = (email or "").strip().lower() or user.email
    verify_otp(user, EmailOTP.Purpose.VERIFY_EMAIL, code, email=target)

    with transaction.atomic():
        accounts = user.accounts.filter(is_active=True).order_by("created_at")

        account = None
        if account_id:
            account = accounts.filter(pk=account_id).first()
        elif target:
            account = accounts.filter(email__iexact=target).first()
        if account is None:
            account = accounts.order_by("-created_at").first()
        if account is None:
            raise AccountNotFoundError()

        now = timezone.now()
        if not account.is_email_verified:
            account.email = account.email or target
            account.is_email_verified = True
            account.verified_at = now
            account.save(update_fields=["email", "is_email_verified", "verified_at", "updated_at"])

        if not user.is_verified:
            user.is_verified = True
            user.verified_at = now
            user.status = User.Status.ACTIVE
            user.is_active = True
            user.save(update_fields=["is_verified", "verified_at", "status", "is_active"])

        if account.role == "client":
            from subscriptions.services import assign_trial

            assign_trial(account, user)

        tokens = build_token_pair(user, account)

    logger.info("Email verified user=%s account=%s", user.pk, account.pk)
    return {"user": user, "account": account, **tokens}
