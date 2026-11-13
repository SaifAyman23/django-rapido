"""Registration service — QOOT-001 email sign up.

Register never issues a JWT. It creates (or reuses an unverified) User +
Account, issues a verification code for that email, and returns a pending state
so the app routes to Verify Email. Tokens are issued only after ``verify_email``.

``Account.email`` is the login identifier and is unique across accounts. A
verified email always means "use Log in and add this account", never a second
User or a second Account. The verified/unverified decision is a shared
pre-flight guard (``accounts.services.guards``) so no User or OTP is created for
an email that can never be registered.
"""

import logging

from django.contrib.auth import get_user_model

from accounts.models import EmailOTP
from accounts.services.accounts import create_account_for_user, unique_username
from accounts.services.guards import (
    ensure_email_available_for_registration,
    normalize_email,
    normalize_role,
    resolve_email_owner,
)
from accounts.services.otp import issue_otp, queue_otp_email, seconds_until_resend
from common.exceptions import EmailAlreadyRegisteredError, ThrottledError

logger = logging.getLogger(__name__)
User = get_user_model()


def _locked_user(user):
    """Re-read the owner under a row lock inside the register transaction."""
    return User.objects.select_for_update().get(pk=user.pk)


def register_user(*, email: str, password: str, role: str):
    """Create (or resume) an unverified User with a role Account.

    Returns ``(user, account, otp, created)`` where ``created`` is False when an
    existing unverified email was re-registered. A verified email raises
    ``EMAIL_ALREADY_REGISTERED`` — that person must log in and add an account.
    """
    email = normalize_email(email)
    role = normalize_role(role)

    # One lookup decides new vs resume and raises before any write.
    owner = ensure_email_available_for_registration(email)

    account = owner.account
    if account is not None:
        user = owner.user
        created = False
    else:
        user = _locked_user(owner.user) if owner.user is not None else None
        created = user is None

        if created:
            user = User.objects.create_user(
                email=email,
                password=password,
                username=unique_username(email),
            )
            user.is_verified = False
            user.status = User.Status.UNVERIFIED
            user.save(update_fields=["is_verified", "status"])

        account = user.accounts.order_by("created_at").first()
        if account is None:
            account = create_account_for_user(
                user,
                role,
                email=email,
                is_email_verified=False,
            )
        elif account.email is None:
            # Legacy secondary/primary row without a login email: adopt it.
            account.email = email
            account.save(update_fields=["email", "updated_at"])
        elif account.email.lower() != email:
            raise EmailAlreadyRegisteredError()

    if not account.is_active:
        account.is_active = True
        account.save(update_fields=["is_active", "updated_at"])

    otp = issue_otp(
        user,
        EmailOTP.Purpose.VERIFY_EMAIL,
        email=email,
        enforce_cooldown=False,
    )

    logger.info(
        "Register pending verification user=%s account=%s role=%s created=%s",
        user.pk,
        account.pk,
        account.role,
        created,
    )
    return user, account, otp, created


def send_verification_code(otp) -> None:
    """Queue the verification email (transaction.on_commit boundary in the view)."""
    queue_otp_email(otp)


def resend_verification_email(email: str):
    """Issue a new verification code for an unverified email, if any.

    Returns the OTP row (queued by the caller after commit) or ``None`` when
    the email is unknown or already verified. Anti-enumeration is handled by
    the view: both cases return the same neutral ``204``.
    """
    target = normalize_email(email)
    # Resend is anti-enumeration: never raise for unknown/verified emails.
    owner = resolve_email_owner(target, active_only=False)
    if not owner.exists or owner.verified:
        return None

    user = owner.user
    account = owner.account
    if account is None:
        account = user.accounts.order_by("created_at").first()
        if account is not None and account.email is None:
            account.email = target
            account.save(update_fields=["email", "updated_at"])

    remaining = seconds_until_resend(user, EmailOTP.Purpose.VERIFY_EMAIL, email=target)
    if remaining:
        raise ThrottledError(context={"retry_after": remaining})

    return issue_otp(
        user,
        EmailOTP.Purpose.VERIFY_EMAIL,
        email=target,
        enforce_cooldown=False,
    )


__all__ = [
    "register_user",
    "resend_verification_email",
    "send_verification_code",
]
