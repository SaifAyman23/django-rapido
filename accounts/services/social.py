"""Google, Apple, and Facebook sign-in (QOOT-001 §2.4).

Verification is provider-native: Google ID tokens are checked against every
configured ``GOOGLE_OAUTH_CLIENT_IDS`` audience, Apple identity tokens against
``APPLE_BUNDLE_ID`` and Apple's JWKS, and Facebook access tokens against the
Graph API ``debug_token`` endpoint plus ``/me``. allauth keeps the provider
identity (``SocialAccount``); ``SocialAccountLink`` remembers the Qoot Account
that identity signs in to, which is required because Apple only returns the email
on the first consent.

Resolution rules:
- Existing provider identity wins, even if a new email would map elsewhere.
- Otherwise a provider-verified email resolves ``Account.email`` exactly.
- No match requires ``role`` and creates User + Account.
- A provider identity never merges two different Users.
"""

import base64
import json
import logging
import secrets
from functools import lru_cache
from hashlib import sha256

import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import SocialAccountLink
from accounts.services.accounts import (
    create_account_for_user,
    find_account_by_email,
    primary_account,
    unique_username,
)
from accounts.services.guards import (
    ensure_account_belongs_to,
    ensure_account_enabled,
    ensure_provider_identity_owner,
    ensure_provider_identity_slot,
    ensure_user_enabled,
    normalize_email,
    normalize_role,
    resolve_email_owner,
)
from accounts.services.tokens import build_token_pair
from common.exceptions import InvalidSocialTokenError, RoleRequiredError

logger = logging.getLogger(__name__)
User = get_user_model()

GOOGLE_PROVIDER = "google"
APPLE_PROVIDER = "apple"
FACEBOOK_PROVIDER = "facebook"

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = ["https://accounts.google.com", "accounts.google.com"]
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
FACEBOOK_GRAPH_URL = "https://graph.facebook.com"


def _provider_timeout() -> int:
    """HTTP timeout for provider calls, configurable per environment."""
    return int(getattr(settings, "SOCIAL_HTTP_TIMEOUT_SECONDS", 10))


@lru_cache(maxsize=2)
def _jwks_client(url: str) -> jwt.PyJWKClient:
    """One cached JWKS client per provider (keys are cached inside PyJWT)."""
    return jwt.PyJWKClient(url, timeout=_provider_timeout())


def _decode_unverified_audience(token: str):
    """Read ``aud`` without verification (used only for provider diagnostics)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8"))).get("aud")
    except Exception:
        logger.debug("Failed to decode token aud claim", exc_info=True)
        return None


def _google_audiences():
    ids = [client_id.strip() for client_id in settings.GOOGLE_OAUTH_CLIENT_IDS if client_id.strip()]
    # allauth SocialApp rows are an optional second source (admin-seeded apps).
    try:
        from allauth.socialaccount.models import SocialApp

        ids.extend(
            SocialApp.objects.filter(provider=GOOGLE_PROVIDER)
            .exclude(client_id="")
            .values_list("client_id", flat=True)
        )
    except Exception:  # allauth not migrated yet / table unavailable
        logger.debug("allauth SocialApp lookup unavailable", exc_info=True)
    ids = list(dict.fromkeys(ids))
    if not ids:
        logger.warning("Google sign-in attempted without a configured client id")
        raise InvalidSocialTokenError()
    return ids


def _google_client_secret(client_id: str) -> str:
    try:
        from allauth.socialaccount.models import SocialApp

        app = SocialApp.objects.filter(provider=GOOGLE_PROVIDER, client_id=client_id).first()
        if app and app.secret:
            return app.secret
    except Exception:
        logger.debug("allauth SocialApp secret lookup unavailable", exc_info=True)
    return getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")


def verify_google_id_token(id_token: str) -> dict:
    """Verify a Google ID token and return its claims.

    The audience list is the single source of truth for Android, iOS, and web
    clients, so any registered client can sign in.
    """
    try:
        signing_key = _jwks_client(GOOGLE_JWKS_URL).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=_google_audiences(),
            issuer=GOOGLE_ISSUERS,
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
        )
    except InvalidSocialTokenError:
        raise
    except Exception as exc:
        logger.warning(
            "Google ID token rejected aud=%s: %s",
            _decode_unverified_audience(id_token),
            exc,
        )
        raise InvalidSocialTokenError() from exc

    email = normalize_email(claims.get("email"))
    if not email or str(claims.get("email_verified", "")).lower() not in {"true", "1"}:
        raise InvalidSocialTokenError()
    claims["email"] = email
    return claims


def exchange_google_code(*, code: str, redirect_uri: str, code_verifier: str | None = None) -> dict:
    """Exchange a Google authorization code and verify the returned ID token.

    Each configured client is tried because Android/iOS/web hold different
    client IDs; only the client that issued the code succeeds. Mobile clients
    use PKCE and have no secret.
    """
    audiences = _google_audiences()
    last_error = None

    for client_id in audiences:
        secret = _google_client_secret(client_id)
        data = {
            "code": code,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if secret:
            data["client_secret"] = secret
        if code_verifier:
            data["code_verifier"] = code_verifier
        try:
            response = requests.post(
                GOOGLE_TOKEN_URL,
                data=data,
                timeout=_provider_timeout(),
            )
            if not response.ok:
                last_error = response.text[:200]
                continue
            payload = response.json()
            id_token = payload.get("id_token")
            if id_token:
                return verify_google_id_token(id_token)
            last_error = "token response has no id_token"
        except Exception as exc:  # network / malformed response
            last_error = str(exc)

    logger.warning("Google code exchange failed: %s", last_error)
    raise InvalidSocialTokenError()


def _apple_nonce_matches(claim_nonce, provided_nonce) -> bool:
    """Accept both the raw nonce and ``SHA-256(nonce)`` (Expo/client variants)."""
    claim = str(claim_nonce or "")
    provided = str(provided_nonce or "")
    if not claim or not provided:
        return False
    if secrets.compare_digest(claim, provided):
        return True
    hashed = sha256(provided.encode("utf-8")).hexdigest()
    return secrets.compare_digest(claim, hashed)


def verify_apple_identity_token(identity_token: str, *, nonce: str | None = None) -> dict:
    """Verify an Apple identity token against Apple's JWKS and the bundle ID."""
    bundle_id = (getattr(settings, "APPLE_BUNDLE_ID", "") or "").strip()
    if not bundle_id:
        logger.warning("Apple sign-in attempted without APPLE_BUNDLE_ID")
        raise InvalidSocialTokenError()

    try:
        signing_key = _jwks_client(APPLE_JWKS_URL).get_signing_key_from_jwt(identity_token)
        claims = jwt.decode(
            identity_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=bundle_id,
            issuer=APPLE_ISSUER,
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
        )
    except Exception as exc:
        logger.warning("Apple identity token rejected: %s", exc)
        raise InvalidSocialTokenError() from exc

    if nonce:
        if not _apple_nonce_matches(claims.get("nonce"), nonce):
            raise InvalidSocialTokenError()
    elif claims.get("nonce"):
        # The client sent a nonce to Apple but did not echo it to us.
        raise InvalidSocialTokenError()

    claims["email"] = normalize_email(claims.get("email"))
    claims["email_verified"] = str(claims.get("email_verified", "")).lower() in {
        "true",
        "1",
    }
    return claims


def _facebook_app_credentials() -> tuple[str, str]:
    """Return ``(app_id, app_secret)`` or fail closed when Facebook is unconfigured."""
    app_id = (getattr(settings, "FACEBOOK_APP_ID", "") or "").strip()
    app_secret = (getattr(settings, "FACEBOOK_APP_SECRET", "") or "").strip()
    if not app_id or not app_secret:
        logger.warning("Facebook sign-in attempted without FACEBOOK_APP_ID/SECRET")
        raise InvalidSocialTokenError()
    return app_id, app_secret


def _facebook_graph_url(path: str) -> str:
    version = (getattr(settings, "FACEBOOK_GRAPH_API_VERSION", "") or "v21.0").strip("/")
    return f"{FACEBOOK_GRAPH_URL}/{version}/{path.lstrip('/')}"


def verify_facebook_access_token(access_token: str) -> dict:
    """Verify a Facebook user access token and return identity claims.

    ``debug_token`` proves the token is valid and was issued to our app; ``/me``
    then returns the stable Facebook user id and, when the user granted the
    ``email`` permission, the email. Facebook may omit the email, so a first-time
    identity without one cannot create an Account, while a known identity can
    still sign in through ``SocialAccountLink``.
    """
    token = str(access_token or "").strip()
    if not token:
        raise InvalidSocialTokenError()

    app_id, app_secret = _facebook_app_credentials()
    app_token = f"{app_id}|{app_secret}"

    try:
        debug_response = requests.get(
            _facebook_graph_url("debug_token"),
            params={"input_token": token, "access_token": app_token},
            timeout=_provider_timeout(),
        )
        debug_payload = debug_response.json() if debug_response.content else {}
        debug = debug_payload.get("data") or {}
        if (
            not debug_response.ok
            or not debug.get("is_valid")
            or str(debug.get("app_id", "")) != app_id
        ):
            logger.warning("Facebook access token rejected: %s", debug_payload)
            raise InvalidSocialTokenError()

        profile_response = requests.get(
            _facebook_graph_url("me"),
            params={"fields": "id,email,name", "access_token": token},
            timeout=_provider_timeout(),
        )
        profile = profile_response.json() if profile_response.content else {}
        if not profile_response.ok:
            logger.warning("Facebook profile lookup failed: %s", profile)
            raise InvalidSocialTokenError()
    except InvalidSocialTokenError:
        raise
    except Exception as exc:  # network / malformed response
        logger.warning("Facebook token verification failed: %s", exc)
        raise InvalidSocialTokenError() from exc

    uid = str(profile.get("id") or "").strip()
    if not uid or str(debug.get("user_id") or uid) != uid:
        raise InvalidSocialTokenError()

    email = normalize_email(profile.get("email"))
    return {
        "sub": uid,
        "email": email,
        "email_verified": bool(email),
        "name": profile.get("name", ""),
    }


def _provider_claims_for_google(
    *, id_token: str | None, code: str | None, redirect_uri: str | None, code_verifier: str | None
) -> dict:
    if id_token:
        return verify_google_id_token(id_token)
    if code and redirect_uri:
        return exchange_google_code(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )
    raise InvalidSocialTokenError()


def _mark_identity_verified(user, account) -> None:
    """Provider proof verifies both the person identity and the Account email."""
    now = timezone.now()

    user_fields = []
    if not user.is_verified:
        user.is_verified = True
        user.verified_at = user.verified_at or now
        user_fields += ["is_verified", "verified_at"]
    if user.status == User.Status.UNVERIFIED:
        user.status = User.Status.ACTIVE
        user_fields.append("status")
    if not user.is_active:
        user.is_active = True
        user_fields.append("is_active")
    if user_fields:
        user.save(update_fields=sorted(set(user_fields)))

    if not account.is_email_verified:
        account.is_email_verified = True
        account.verified_at = account.verified_at or now
        account.save(update_fields=["is_email_verified", "verified_at", "updated_at"])


def _link_provider(user, account, *, provider: str, uid: str, claims: dict):
    """Create/refresh allauth's SocialAccount and bind it to ``account``."""
    from allauth.socialaccount.models import SocialAccount

    social_account = SocialAccount.objects.filter(provider=provider, uid=uid).first()
    ensure_provider_identity_owner(social_account, user)

    if social_account is None:
        try:
            with transaction.atomic():
                social_account = SocialAccount.objects.create(
                    user=user,
                    provider=provider,
                    uid=uid,
                    extra_data=claims,
                )
        except IntegrityError:
            # A parallel request created the same identity first: reuse it.
            social_account = SocialAccount.objects.filter(provider=provider, uid=uid).first()
            if social_account is None:
                raise
            ensure_provider_identity_owner(social_account, user)
    else:
        social_account.extra_data = claims
        social_account.save(update_fields=["extra_data"])

    SocialAccountLink.objects.update_or_create(
        social_account=social_account,
        defaults={"account": account},
    )
    return social_account


def _existing_identity(provider: str, uid: str):
    from allauth.socialaccount.models import SocialAccount

    return SocialAccount.objects.select_related("user").filter(provider=provider, uid=uid).first()


def _resolve_existing_identity(social_account, *, provider: str, email: str, role):
    """Resolve the Account bound to an existing provider identity."""
    user = social_account.user
    ensure_user_enabled(user)

    link = (
        SocialAccountLink.objects.select_related("account")
        .filter(social_account=social_account)
        .first()
    )
    if link is not None:
        account = link.account
        ensure_account_belongs_to(account, user)
    else:
        account = None
        if email:
            candidate = find_account_by_email(email)
            if candidate is not None and candidate.user_id == user.pk:
                account = candidate
        if account is None:
            account = primary_account(user)
        if account is None:
            if not role:
                raise RoleRequiredError()
            account = create_account_for_user(
                user,
                normalize_role(role),
                email=email or None,
                is_email_verified=bool(email),
                verified_at=timezone.now() if email else None,
            )
        SocialAccountLink.objects.update_or_create(
            social_account=social_account,
            defaults={"account": account},
        )

    ensure_account_enabled(account)

    if email and account.email is None:
        account.email = email
        account.save(update_fields=["email", "updated_at"])

    _mark_identity_verified(user, account)
    return user, account, False


def _resolve_new_identity(*, provider: str, uid: str, email: str, role, claims: dict):
    """Resolve or create the User/Account for a provider identity seen first time."""
    if not email:
        # No verified email and no existing binding: there is nothing to anchor.
        raise InvalidSocialTokenError()

    # One lookup answers "is this email already tied to a person or account?".
    owner = resolve_email_owner(email, active_only=False)
    user, account = owner.user, owner.account
    created = False

    if user is not None:
        ensure_user_enabled(user)
        # One provider identity per person/provider: never merge two Users.
        ensure_provider_identity_slot(user, provider, uid)

    if user is None:
        if not role:
            raise RoleRequiredError()
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=None,
                    username=unique_username(email),
                )
                user.is_verified = True
                user.verified_at = timezone.now()
                user.status = User.Status.ACTIVE
                user.save(update_fields=["is_verified", "verified_at", "status"])
        except IntegrityError:
            # A parallel request created this person first: continue with it.
            owner = resolve_email_owner(email, active_only=False)
            user, account = owner.user, owner.account
            ensure_user_enabled(user)
        else:
            created = True

    if account is None and user is not None:
        account = primary_account(user)

    if account is None:
        if not role:
            raise RoleRequiredError()
        account = create_account_for_user(
            user,
            normalize_role(role),
            email=email,
            is_email_verified=True,
            verified_at=timezone.now(),
        )
    elif account.email is None:
        account.email = email
        account.save(update_fields=["email", "updated_at"])

    ensure_account_enabled(account)
    _mark_identity_verified(user, account)
    _link_provider(user, account, provider=provider, uid=uid, claims=claims)
    return user, account, created


def _social_login(*, provider: str, uid: str, email: str, role, claims: dict) -> dict:
    email = normalize_email(email)
    uid = str(uid or "").strip()
    if not uid:
        raise InvalidSocialTokenError()

    # Pre-flight read: a known provider identity resolves before any write, so
    # a repeat sign-in never touches the Account or the verified flags.
    social_account = _existing_identity(provider, uid)

    # One transaction keeps the provider identity, its Account binding, and the
    # verified flags consistent. ``create_account_for_user`` also needs an
    # atomic block for its row lock.
    with transaction.atomic():
        if social_account is not None:
            user, account, created = _resolve_existing_identity(
                social_account,
                provider=provider,
                email=email,
                role=role,
            )
        else:
            user, account, created = _resolve_new_identity(
                provider=provider,
                uid=uid,
                email=email,
                role=role,
                claims=claims,
            )

        tokens = build_token_pair(user, account)

    logger.info(
        "Social login provider=%s user=%s account=%s created=%s",
        provider,
        user.pk,
        account.pk,
        created,
    )
    return {"user": user, "account": account, "created": created, **tokens}


def login_with_google(
    *,
    id_token: str | None = None,
    code: str | None = None,
    redirect_uri: str | None = None,
    code_verifier: str | None = None,
    role=None,
) -> dict:
    """Verify Google credentials and return the bound Account + tokens."""
    claims = _provider_claims_for_google(
        id_token=id_token,
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
    )
    return _social_login(
        provider=GOOGLE_PROVIDER,
        uid=str(claims.get("sub", "")),
        email=claims.get("email", ""),
        role=role,
        claims=claims,
    )


def login_with_apple(*, identity_token: str, nonce=None, role=None) -> dict:
    """Verify an Apple identity token and return the bound Account + tokens."""
    claims = verify_apple_identity_token(identity_token, nonce=nonce)
    email = claims.get("email", "")
    if email and not claims.get("email_verified"):
        # An unverified relay address must never claim an existing Account.
        raise InvalidSocialTokenError()

    return _social_login(
        provider=APPLE_PROVIDER,
        uid=str(claims.get("sub", "")),
        email=email,
        role=role,
        claims=claims,
    )


def login_with_facebook(*, access_token: str, role=None) -> dict:
    """Verify a Facebook access token and return the bound Account + tokens."""
    claims = verify_facebook_access_token(access_token)
    return _social_login(
        provider=FACEBOOK_PROVIDER,
        uid=str(claims.get("sub", "")),
        email=claims.get("email", ""),
        role=role,
        claims=claims,
    )


def social_link_for(account):
    """Return the provider links bound to ``account`` (admin/debug helper)."""
    return SocialAccountLink.objects.filter(account=account).select_related("social_account")


__all__ = [
    "exchange_google_code",
    "login_with_apple",
    "login_with_facebook",
    "login_with_google",
    "social_link_for",
    "verify_apple_identity_token",
    "verify_facebook_access_token",
    "verify_google_id_token",
]
