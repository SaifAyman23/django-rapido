"""Pre-flight guards shared by the auth and social flows (QOOT-001 / QOOT-002).

Each guard answers one question *before* a flow spends real effort — creates a
User or Account, issues an OTP and sends an email, or burns a provider token
exchange — and raises the same typed error the flow would have raised later.
Views and services call these instead of re-querying ``User``/``Account`` for
the same facts (AGENTS §3.2 / §3.5: one source of truth, no duplication).

The guards are pure: they take model instances or primitives, never requests,
and never return HTTP responses.
"""

from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.models import Account
from common.exceptions import (
    AccountAlreadyAddedError,
    AccountDisabledError,
    AccountLimitReachedError,
    AccountOwnershipConflictError,
    EmailAlreadyRegisteredError,
    RoleRequiredError,
)

User = get_user_model()


def normalize_email(email) -> str:
    """Trim and lowercase a login email."""
    return (email or "").strip().lower()


def normalize_role(role) -> str:
    """Return a valid ``Account.Role`` value or raise ``ROLE_REQUIRED``."""
    value = str(role or "").strip().lower()
    if value not in Account.Role.values:
        raise RoleRequiredError()
    return value


@dataclass(frozen=True)
class EmailOwner:
    """Who already owns an email: an Account, a legacy User, or nobody."""

    user: object | None
    account: Account | None

    @property
    def exists(self) -> bool:
        return self.user is not None

    @property
    def verified(self) -> bool:
        """True when using this email would collide with a verified identity."""
        if self.account is not None and self.account.is_email_verified:
            return True
        return bool(self.user is not None and self.user.is_verified)


def resolve_email_owner(email, *, active_only: bool = True) -> EmailOwner:
    """Resolve an email to its Account or legacy User in one lookup.

    ``Account.email`` wins because it is the app-facing login identifier.
    ``User.email`` is only a fallback for accounts that have not been given an
    email yet. Inactive accounts are skipped unless ``active_only`` is false.
    """
    target = normalize_email(email)
    if not target:
        return EmailOwner(user=None, account=None)

    account = Account.objects.select_related("user").filter(email__iexact=target).first()
    if account is not None:
        if account.is_active or not active_only:
            return EmailOwner(user=account.user, account=account)
        # Never resume a legacy ``User.email`` when an Account already owns the
        # address but is disabled for this lookup: falling through would
        # resurrect a disabled login (or let a stale owner block a new one).
        return EmailOwner(user=None, account=None)

    return EmailOwner(user=User.objects.filter(email__iexact=target).first(), account=None)


def ensure_email_available_for_registration(email) -> EmailOwner:
    """Return the resume candidate, or raise ``EMAIL_ALREADY_REGISTERED``.

    Runs before a User, Account, or OTP is created. Unverified owners are
    returned so the caller can resume their sign-up instead of duplicating it.
    """
    owner = resolve_email_owner(email, active_only=False)
    if owner.verified:
        raise EmailAlreadyRegisteredError()
    return owner


def ensure_account_slot_available(user) -> None:
    """Raise ``ACCOUNT_LIMIT_REACHED`` when the person owns too many accounts."""
    if Account.objects.filter(user=user).count() >= settings.MAX_LINKED_ACCOUNTS:
        raise AccountLimitReachedError()


def ensure_email_available_for_new_account(user, email) -> None:
    """Raise when ``email`` cannot become another login email for ``user``."""
    owner = resolve_email_owner(email, active_only=False)
    if owner.user is not None:
        if owner.user.pk == user.pk:
            raise AccountAlreadyAddedError()
        raise EmailAlreadyRegisteredError()
    ensure_account_slot_available(user)


def ensure_email_available_for_change(user, email, *, account) -> None:
    """Raise when ``email`` cannot replace ``account``'s login email (QOOT-012)."""
    owner = resolve_email_owner(email, active_only=False)
    if owner.user is None:
        return
    if owner.user.pk != user.pk:
        raise EmailAlreadyRegisteredError()
    if owner.account is not None and owner.account.pk != account.pk:
        # Another Account of the same person already uses this email.
        raise EmailAlreadyRegisteredError()


def ensure_user_enabled(user) -> None:
    """Raise ``ACCOUNT_DISABLED`` for a missing, inactive, or suspended person."""
    if user is None or not user.is_active or user.status == User.Status.SUSPENDED:
        raise AccountDisabledError()


def ensure_account_enabled(account) -> None:
    """Raise ``ACCOUNT_DISABLED`` when the selected Account is not active."""
    if account is not None and not account.is_active:
        raise AccountDisabledError()


def ensure_account_belongs_to(account, user) -> None:
    """Raise ``ACCOUNT_OWNERSHIP_CONFLICT`` when an Account has another owner."""
    if account is not None and account.user_id != user.pk:
        raise AccountOwnershipConflictError()


def ensure_provider_identity_owner(social_account, user) -> None:
    """Raise ``ACCOUNT_OWNERSHIP_CONFLICT`` for a provider identity of another User."""
    if social_account is not None and social_account.user_id != user.pk:
        raise AccountOwnershipConflictError()


def ensure_provider_identity_slot(user, provider: str, uid: str) -> None:
    """One provider identity per person and provider; a second one is a conflict."""
    from allauth.socialaccount.models import SocialAccount

    if SocialAccount.objects.filter(user=user, provider=provider).exclude(uid=uid).exists():
        raise AccountOwnershipConflictError()


__all__ = [
    "EmailOwner",
    "ensure_account_belongs_to",
    "ensure_account_enabled",
    "ensure_account_slot_available",
    "ensure_email_available_for_change",
    "ensure_email_available_for_new_account",
    "ensure_email_available_for_registration",
    "ensure_provider_identity_owner",
    "ensure_provider_identity_slot",
    "ensure_user_enabled",
    "normalize_email",
    "normalize_role",
    "resolve_email_owner",
]
