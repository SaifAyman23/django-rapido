"""Multi-account service — create, resolve, list, and add a person's Accounts.

One Django User owns many Account rows, including several with the same role.
Each Account has its own login email. The account limit comes from
``settings.MAX_LINKED_ACCOUNTS`` and is enforced under a row lock on the
User so two parallel adds cannot exceed it (QOOT-001 §2.3).

Pre-flight checks (email ownership, account limit, role) live in
``accounts.services.guards`` so register, add-account, social, and email-change
share one implementation.
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import Account, EmailOTP
from accounts.services.guards import (
    ensure_account_slot_available,
    ensure_email_available_for_new_account,
    normalize_email,
    normalize_role,
    resolve_email_owner,
)
from accounts.services.otp import issue_otp, verify_otp
from common.exceptions import AccountNotFoundError, EmailAlreadyRegisteredError, RoleRequiredError

User = get_user_model()


def unique_username(email: str) -> str:
    """Derive a unique username from the email local part (shared by sign-up paths)."""
    base = (email.split("@")[0] or "user")[:140]
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1
    return username


def active_accounts(user):
    """Accounts the person may act as, oldest first."""
    return Account.objects.filter(user=user, is_active=True).order_by("created_at")


def primary_account(user):
    """Return the oldest account, which owns ``User.email`` and allauth identity."""
    oldest = active_accounts(user).first()
    if oldest is not None:
        return oldest
    return Account.objects.filter(user=user).order_by("created_at").first()


def get_account_for_user(user, account_id=None, *, required: bool = False):
    """Return ``account_id`` if it belongs to ``user``, else the default account."""
    accounts = active_accounts(user)
    if account_id:
        account = accounts.filter(pk=account_id).first()
        if account is None:
            if required:
                raise AccountNotFoundError()
            return None
        return account
    account = accounts.first()
    if account is None and required:
        raise RoleRequiredError()
    return account


def find_account_by_email(email, *, active_only: bool = True):
    """Resolve an Account from its login email (case-insensitive)."""
    return resolve_email_owner(email, active_only=active_only).account


def resolve_login_identity(email):
    """Return ``(user, account)`` for a login email, or ``(None, None)``.

    ``Account.email`` wins because it is the app-facing identifier. Legacy
    rows without an account email fall back to ``User.email`` plus the primary
    Account. Disabled accounts are still resolved so login can return
    ``ACCOUNT_DISABLED`` instead of a misleading credentials error.
    """
    owner = resolve_email_owner(email, active_only=False)
    if not owner.exists:
        return None, None
    if owner.account is not None:
        return owner.user, owner.account
    return owner.user, primary_account(owner.user)


def create_account_for_user(
    user,
    role,
    *,
    email=None,
    is_email_verified: bool = False,
    verified_at=None,
) -> Account:
    """Create one role Account for ``user`` inside the caller's atomic block.

    The User row is locked so parallel adds cannot exceed the linked-account
    limit. The same role may be created more than once.
    """
    role = normalize_role(role)
    target = normalize_email(email) or None

    locked_user = type(user).objects.select_for_update().get(pk=user.pk)
    ensure_account_slot_available(locked_user)

    account = Account.objects.create(
        user=locked_user,
        role=role,
        email=target,
        is_email_verified=bool(is_email_verified),
        verified_at=verified_at if is_email_verified else None,
    )

    from accounts.services.subscriptions_hook import on_account_created

    on_account_created(account)
    return account


def request_add_account(user, *, email: str, role: str) -> EmailOTP:
    """Issue an ``ADD_ACCOUNT`` code for a new email the person wants to add."""
    target = normalize_email(email)
    role = normalize_role(role)

    # Cheapest checks first: ownership of the email, then the linked limit.
    ensure_email_available_for_new_account(user, target)

    return issue_otp(
        user,
        EmailOTP.Purpose.ADD_ACCOUNT,
        email=target,
        metadata={"role": role, "email": target},
    )


def verify_add_account(user, *, email: str, code: str) -> Account:
    """Consume the add-account code and create the verified Account.

    The code is consumed before the account is created. ``verify_otp`` must
    keep its short transaction boundary so failed attempts persist.
    """
    target = normalize_email(email)
    otp = verify_otp(user, EmailOTP.Purpose.ADD_ACCOUNT, code, email=target)
    role = normalize_role((otp.metadata or {}).get("role"))

    # Re-check under the write transaction: another request may have claimed
    # the email between the code request and this verification.
    ensure_email_available_for_new_account(user, target)
    try:
        with transaction.atomic():
            return create_account_for_user(
                user,
                role,
                email=target,
                is_email_verified=True,
                verified_at=timezone.now(),
            )
    except IntegrityError as exc:
        # Two people can verify the same free email at almost the same moment.
        # The unique constraint wins the race; translate it into the same typed
        # error the pre-flight check raises instead of a generic 409.
        raise EmailAlreadyRegisteredError() from exc


def resend_add_account(user, *, email: str):
    """Re-issue the pending add-account code for ``email`` (role preserved).

    Returns ``None`` when no add-account request exists for that email, so the
    caller can keep the response neutral instead of revealing pending state.
    """
    target = normalize_email(email)

    latest = (
        EmailOTP.objects.filter(
            user=user,
            email__iexact=target,
            purpose=EmailOTP.Purpose.ADD_ACCOUNT,
        )
        .order_by("-created_at")
        .first()
    )
    if latest is None:
        return None

    # The email may have been claimed since the request. Keep the response
    # neutral (no code, no ownership leak) instead of raising here.
    if resolve_email_owner(target, active_only=False).user is not None:
        return None
    ensure_account_slot_available(user)

    role = normalize_role((latest.metadata or {}).get("role"))
    return issue_otp(
        user,
        EmailOTP.Purpose.ADD_ACCOUNT,
        email=target,
        enforce_cooldown=False,
        metadata={"role": role, "email": target},
    )


def list_for_user(user):
    """Return the caller's own Account rows (QOOT-001 §1.5 Account visibility)."""
    return (
        Account.objects.filter(user=user)
        .select_related("user", "client_profile", "coach_profile")
        .order_by("created_at")
    )


def delete_account(user, account_id) -> dict:
    """Hard-delete one Account and everything that cascades from it.

    Removing the **last** Account deletes the person identity (``User``) too,
    because an Account is the only meaningful payload a User has. Removing one of
    several Accounts deletes only that Account; when it was the primary Account,
    ``User.email`` mirrors the oldest remaining Account that still has an email.
    If no remaining Account has one, the legacy ``User.email`` fallback is kept.

    Only the deleted Account's refresh tokens are blacklisted, except when the
    whole User is deleted. Returns ``{"user_deleted": bool, "account": Account}``.
    """
    from accounts.services.subscriptions_hook import on_account_deleted
    from accounts.services.tokens import (
        blacklist_account_refresh_tokens,
        blacklist_all_refresh_tokens,
    )

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        account = (
            Account.objects.select_for_update().filter(user=locked_user, pk=account_id).first()
        )
        if account is None:
            raise AccountNotFoundError()

        account_email = normalize_email(account.email)
        oldest = Account.objects.filter(user=locked_user).order_by("created_at").first()
        is_primary = bool(account_email) and account_email == normalize_email(locked_user.email)
        if not is_primary and oldest is not None:
            is_primary = oldest.pk == account.pk

        remaining = Account.objects.filter(user=locked_user).exclude(pk=account.pk)
        if not remaining.exists():
            blacklist_all_refresh_tokens(locked_user)
            on_account_deleted(account)
            locked_user.delete()
            return {"user_deleted": True, "account": account}

        blacklist_account_refresh_tokens(locked_user, account)
        on_account_deleted(account)
        account.delete()

        if is_primary:
            successor = (
                remaining.filter(email__isnull=False)
                .exclude(email="")
                .order_by("created_at")
                .first()
            )
            successor_email = normalize_email(successor.email) if successor is not None else ""
            if successor_email and successor_email != normalize_email(locked_user.email):
                locked_user.email = successor_email
                locked_user.save(update_fields=["email"])

        return {"user_deleted": False, "account": account}


def delete_user_identity(user) -> None:
    """Hard-delete the person identity, every Account, and all cascaded data."""
    from accounts.services.subscriptions_hook import on_account_deleted
    from accounts.services.tokens import blacklist_all_refresh_tokens

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        blacklist_all_refresh_tokens(locked_user)
        for account in Account.objects.filter(user=locked_user):
            on_account_deleted(account)
        locked_user.delete()
