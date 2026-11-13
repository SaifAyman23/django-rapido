"""JWT helpers - every token pair is bound to exactly one active Account.

The access/refresh tokens carry an ``account_id`` claim. ``AccountJWTAuthentication``
turns that claim back into ``request.active_account``, so views never guess the
role from the User.
"""

from django.utils import timezone
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken
from rest_framework_simplejwt.utils import datetime_from_epoch


def build_token_pair(user, account) -> dict:
    """Return ``{"access": ..., "refresh": ...}`` for ``user`` acting as ``account``."""
    refresh = RefreshToken.for_user(user)

    claims = {
        "account_id": str(account.pk),
        "role": account.role,
        "email": account.display_email,
    }

    for key, value in claims.items():
        refresh[key] = value

    access = refresh.access_token

    for key, value in claims.items():
        access[key] = value

    # ``for_user`` records the outstanding token before the account claims are
    # added. Persist the final token text so per-account revocation can match the
    # ``account_id`` claim later (deleting one Account must not revoke others).
    OutstandingToken.objects.filter(jti=refresh["jti"]).update(token=str(refresh))

    return {"access": str(access), "refresh": str(refresh)}


def register_outstanding_refresh_token(raw_token: str) -> None:
    """Record a rotated refresh token so it can be revoked later.

    ``TokenRefreshView`` rotates without adding the new token to
    ``OutstandingToken``. Without this, deleting one Account could not revoke the
    session that was refreshed last.
    """
    payload = UntypedToken(raw_token, verify=False).payload
    jti = payload.get(api_settings.JTI_CLAIM)
    expires_at = payload.get("exp")

    if not jti or not expires_at:
        return

    issued_at = payload.get("iat")

    OutstandingToken.objects.update_or_create(
        jti=jti,
        defaults={
            "user_id": payload.get(api_settings.USER_ID_CLAIM),
            "created_at": (
                datetime_from_epoch(issued_at) if issued_at is not None else timezone.now()
            ),
            "token": raw_token,
            "expires_at": datetime_from_epoch(expires_at),
        },
    )


def blacklist_all_refresh_tokens(user) -> int:
    """Blacklist every outstanding refresh token of ``user`` (password reset, delete)."""
    return blacklist_other_refresh_tokens(user)


def blacklist_account_refresh_tokens(user, account) -> int:
    """Blacklist only the refresh tokens bound to ``account``.

    Outstanding tokens store the raw JWT, so the ``account_id`` claim identifies
    the session to revoke. Decoding is unverified on purpose: an expired token is
    still safe to blacklist and must not break account deletion.
    """
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

    account_id = str(account.pk)
    count = 0

    for outstanding in OutstandingToken.objects.filter(user=user):
        try:
            payload = UntypedToken(outstanding.token, verify=False).payload
        except Exception:  # malformed / legacy row - nothing to match
            continue

        if str(payload.get("account_id", "")) != account_id:
            continue

        _, created = BlacklistedToken.objects.get_or_create(token=outstanding)
        if created:
            count += 1

    return count


def blacklist_other_refresh_tokens(user, *, keep_raw_token: str = "") -> int:
    """Blacklist every refresh token of ``user`` except ``keep_raw_token``.

    Used by in-app password/email change so the current session survives while
    the rest are revoked.
    """
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    count = 0

    for outstanding in OutstandingToken.objects.filter(user=user):
        if keep_raw_token and outstanding.token == keep_raw_token:
            continue

        _, created = BlacklistedToken.objects.get_or_create(token=outstanding)
        if created:
            count += 1

    return count
