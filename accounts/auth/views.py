"""
REUSE: Generic social login — Google/Facebook OAuth with JWT.

- Supports PKCE code flow + SDK id_token/access_token fallback
- Handles multiple Google clients (web/Android/iOS) via aud matching
- Generic role handling: reads user.role, no hardcoded customer/ops
- From ras-elbar-go/backend/accounts/auth/views.py — project-agnostic.
"""

import base64
import json
import logging
from datetime import timedelta

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialApp, SocialToken
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter

# api/auth/views.py
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client, OAuth2Error
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.models import Device

from .serializers import (
    SocialLoginErrorSerializer,
    SocialLoginRequestSerializer,
    SocialLoginResponseSerializer,
)

logger = logging.getLogger(__name__)

PROVIDER_ADAPTERS = {
    "google": GoogleOAuth2Adapter,
    "facebook": FacebookOAuth2Adapter,
}


def _decode_id_token_aud(id_token):
    """Return the `aud` (audience) claim from a Google ID token without verifying it.

    Signature verification happens later in GoogleOAuth2Adapter.complete_login
    against the selected app's client_id. Here we only read the claim so the
    correct OAuth client can be selected when multiple clients are configured.
    """
    try:
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
        return data.get("aud")
    except Exception:
        return None


SOCIAL_LOGIN_DESCRIPTION = """
Exchanges an OAuth authorization code or provider token for JWT access/refresh tokens.

## What to Send

**Authorization code flow:** POST `{ "code": "...", "redirect_uri": "..."
[, "code_verifier": "..." ] }`

- `code` — the authorization code from the provider's callback redirect.
- `redirect_uri` — the exact callback URL registered in the provider console.
  Must match what was used in the initial authorization redirect.
- `code_verifier` — required for Google (PKCE), optional/omit for Facebook
  (Facebook does not support PKCE).

**SDK / access token flow:** POST `{ "id_token": "..." }` (Google)
or `{ "access_token": "..." }` (Facebook). Omit `code`, `code_verifier`,
and `redirect_uri`.

For **Flutter**, the SDK/access-token flow is recommended over PKCE.
Provider SDKs (`google_sign_in`, `flutter_facebook_auth`) handle token
acquisition natively, are simpler to integrate, and avoid the complexity
of managing a system-browser redirect round-trip with custom URL schemes.

## Mobile (Flutter) — Quickstart

Use the SDK flow with `google_sign_in`. After the user signs in, send the
Google **ID token** (not the access token):

    { "id_token": "<id token>", "device_uuid": "<device id>" }

Requirements for Google:

- Send the `id_token`. The backend only accepts an ID token for Google,
  never an access token.
- The token's `aud` (audience) claim must equal one of the three registered
  Google clients (Android / iOS / web) — the matching app is selected and
  verified automatically. Build the app with the matching
  `google-services.json` (Android) or `GoogleService-Info.plist` (iOS).
  If you pass a `webClientId` to `google_sign_in`, use the registered web
  client ID.
- Request the `email` scope so the account is linked or created correctly
  and the JWT carries the user's email.
- ID tokens expire after about one hour — fetch a fresh one per login.
- `device_uuid` is optional and activates the push device for this user.
  The login succeeds without it.

## Provider Behaviour

- **Google**: Requires PKCE (`code_challenge_method=S256`). The backend expects
  the raw `code_verifier` to verify the authorization code.
- **Facebook**: Does not support PKCE. Send `code` + `redirect_uri` only.
  `code_verifier` is ignored if provided.

## Multiple Google Clients

Google issues a separate OAuth client per platform (web, Android, iOS), each
with its own client ID. The backend holds one `SocialApp` per client (seeded in
the database) and picks the right one automatically:

- **SDK / ID-token flow**: the token's `aud` (audience) claim must equal one of
  the registered client IDs — the matching app is selected and verified.
- **Authorization-code flow**: the code exchange is attempted against each
  configured client; only the client that issued the code (matching
  `redirect_uri` + PKCE verifier) succeeds.
- Android/iOS OAuth clients have **no client secret** (`secret=""`).

## What You Get Back

On success (HTTP 200): `{ "access": "<JWT>", "refresh": "<JWT>", "user": {...} }`
- `access` — short-lived JWT (15 min). Send as `Authorization: Bearer <token>`.
- `refresh` — long-lived JWT (30 days). Use with the token refresh endpoint.
- `user` — serialized user object.

On error: HTTP 400 (bad request), 401 (invalid/fraudulent code), or 500 (server error).

## Notes

- Authorization codes are one-time use. A "redirect_uri mismatch" error from
  the provider usually means the code was already consumed.
- `redirect_uri` must match the provider console registration exactly
  (trailing slash, scheme, and domain all matter).
- PKCE `code_verifier` is generated and stored entirely client-side. The
  provider never sees it — only the `code_challenge`.
- The same `redirect_uri` value is used for both providers (each validates
  against its own console registration).
"""


@extend_schema(
    tags=["Authentication"],
    summary=_("Social login (Google / Facebook)"),
    description=SOCIAL_LOGIN_DESCRIPTION,
    parameters=[
        OpenApiParameter(
            name="provider",
            type=str,
            location=OpenApiParameter.PATH,
            description=_('OAuth provider identifier. Currently supports "google" and "facebook".'),
            enum=["google", "facebook"],
        ),
    ],
    request=SocialLoginRequestSerializer,
    responses={
        200: OpenApiResponse(
            response=SocialLoginResponseSerializer,
            description=_(
                "JWT access and refresh tokens. Use the access token as Bearer in subsequent requests."
            ),
            examples=[
                OpenApiExample(
                    name="Login success",
                    value={
                        "access": "eyJhbGciOiJIUzI1NiIs...",
                        "refresh": "eyJhbGciOiJIUzI1NiIs...",
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            response=SocialLoginErrorSerializer,
            description=_(
                "Missing or invalid parameters (e.g. missing redirect_uri, unknown provider)."
            ),
            examples=[
                OpenApiExample(
                    name="Missing redirect_uri",
                    value={"detail": "redirect_uri required"},
                    response_only=True,
                ),
                OpenApiExample(
                    name="Missing code or token",
                    value={
                        "detail": "Either `code` + `code_verifier` or `access_token` / `id_token` is required."
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    name="Unknown provider",
                    value={"detail": "Unknown provider."},
                    response_only=True,
                ),
            ],
        ),
        401: OpenApiResponse(
            response=SocialLoginErrorSerializer,
            description=_("Invalid or expired authorization code / provider token."),
            examples=[
                OpenApiExample(
                    name="Invalid code",
                    value={"detail": "Invalid authorization code: [error details]"},
                    response_only=True,
                ),
                OpenApiExample(
                    name="Expired provider token",
                    value={"detail": "Invalid or expired provider token."},
                    response_only=True,
                ),
            ],
        ),
        403: OpenApiResponse(
            response=SocialLoginErrorSerializer,
            description=_("Login not permitted (e.g. account disabled, blocked by adapter)."),
            examples=[
                OpenApiExample(
                    name="Login not permitted",
                    value={"detail": "Login not permitted."},
                    response_only=True,
                ),
            ],
        ),
        500: OpenApiResponse(
            response=SocialLoginErrorSerializer,
            description=_("Server error (provider not configured, account creation failed)."),
            examples=[
                OpenApiExample(
                    name="Provider not configured",
                    value={"detail": "Provider not configured"},
                    response_only=True,
                ),
                OpenApiExample(
                    name="Social login failed",
                    value={"detail": "Social login failed: [error details]"},
                    response_only=True,
                ),
            ],
        ),
    },
    examples=[
        OpenApiExample(
            name="Google login (PKCE code flow)",
            summary="POST to /api/v1/users/api/auth/social/google/ with authorization code + PKCE verifier",
            value={
                "code": "4/0AeaYSHB...",
                "code_verifier": "aB3dEfGhIjKlMnOpQrStUvWxYz1234567890ABCDEF",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Facebook login (code flow, no PKCE)",
            summary="POST to /api/v1/users/api/auth/social/facebook/ with authorization code only",
            value={
                "code": "AQB...abc123",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Google login (SDK fallback)",
            summary="POST to /api/v1/users/api/auth/social/google/ with Google ID token",
            value={
                "id_token": "eyJhbGciOiJSUzI1NiIs...",
                "device_uuid": "a3f1c2d4-0000-4000-8000-000000000000",
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Facebook login (SDK fallback)",
            summary="POST to /api/v1/users/api/auth/social/facebook/ with Facebook access token",
            value={
                "access_token": "EAA...ZCw",
            },
            request_only=True,
        ),
    ],
)
class SocialLoginJWTView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def _get_provider_apps(self, provider):
        """Return the SocialApp candidates for a provider (DB first, settings fallback)."""
        apps = list(SocialApp.objects.filter(provider=provider))
        if apps:
            return apps
        provider_config = settings.SOCIALACCOUNT_PROVIDERS.get(provider)
        if provider_config is None:
            return []
        return [
            SocialApp(
                provider=provider,
                name=provider.title(),
                client_id=provider_config["APP"]["client_id"],
                secret=provider_config["APP"]["secret"],
            )
        ]

    def _find_app_by_id_token_aud(self, apps, id_token):
        """Select the Google app whose client_id matches the ID token's `aud` claim."""
        aud = _decode_id_token_aud(id_token)
        if not aud:
            return None
        for app in apps:
            if app.client_id and app.client_id == aud:
                return app
        return None

    def _exchange_code(self, request, adapter, apps, code, code_verifier, redirect_uri):
        """Exchange an authorization code, trying each configured OAuth client.

        Google may have multiple OAuth clients (web/Android/iOS). Only the client
        that issued the code (matching redirect_uri + PKCE verifier) succeeds, so
        we try each until one returns a token. OAuth2Client strips empty secrets,
        so mobile clients with no secret work for PKCE exchanges.
        """
        last_error = None
        for app in apps:
            client = OAuth2Client(
                request,
                app.client_id,
                app.secret,
                adapter.access_token_method,
                adapter.access_token_url,
                redirect_uri,
            )
            try:
                kwargs = {"code": code}
                if code_verifier:
                    kwargs["pkce_code_verifier"] = code_verifier
                token_data = client.get_access_token(**kwargs)
                return token_data, app
            except Exception as e:
                last_error = e
                logger.warning("Code exchange failed for client %s", app.client_id)
        if last_error is None:
            raise OAuth2Error("No provider client configured.")
        raise last_error

    def post(self, request, provider):
        adapter_cls = PROVIDER_ADAPTERS.get(provider)
        if adapter_cls is None:
            return Response({"detail": _("Unknown provider.")}, status=status.HTTP_400_BAD_REQUEST)

        apps = self._get_provider_apps(provider)
        if not apps:
            return Response(
                {"detail": _("Provider not configured")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        adapter = adapter_cls(request)
        device_uuid = request.data.get("device_uuid")
        code = request.data.get("code")
        raw_token = request.data.get("id_token" if provider == "google" else "access_token")

        token = None
        token_data = None

        if code:
            redirect_uri = request.data.get("redirect_uri")
            code_verifier = request.data.get("code_verifier")

            if not redirect_uri:
                return Response(
                    {"detail": _("redirect_uri required")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.debug("Exchanging code for token with provider %s", provider)

            try:
                token_data, app = self._exchange_code(
                    request, adapter, apps, code, code_verifier, redirect_uri
                )
            except Exception as e:
                return Response(
                    {"detail": _("Invalid authorization code: %(error)s") % {"error": str(e)}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            token = SocialToken(
                app=app,
                token=token_data.get("access_token", ""),
                token_secret=token_data.get("refresh_token", ""),
                expires_at=timezone.now() + timedelta(seconds=token_data.get("expires_in")),
            )
        elif raw_token:
            if provider == "google":
                aud = _decode_id_token_aud(raw_token)
                selected = self._find_app_by_id_token_aud(apps, raw_token)
                if selected:
                    app = selected
                    logger.info(
                        "Google ID token aud=%s matched SocialApp client_id=%s",
                        aud,
                        app.client_id[:12] + "..." if app.client_id else "none",
                    )
                else:
                    # No matching client — log safely and fail instead of silently using apps[0]
                    # REUSE: This is generic — replace aud check with your own client IDs if needed
                    available = [a.client_id[:12] + "..." for a in apps if a.client_id]
                    logger.warning(
                        "Google ID token aud=%s did not match any SocialApp client_id. Available: %s",
                        aud,
                        available,
                    )
                    # Example: if you have a known web client ID, log specific error:
                    # if aud == "YOUR_WEB_CLIENT_ID.apps.googleusercontent.com":
                    #     logger.error("Web client ID not found in SocialApp DB — check seeding")
                    return Response(
                        {"detail": _("No matching Google OAuth client for this ID token.")},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                token_data = {"id_token": raw_token}
            else:
                app = apps[0]
            token = SocialToken(app=app, token=raw_token)
        else:
            return Response(
                {
                    "detail": _(
                        "Either `code` + `code_verifier` or `access_token` / `id_token` is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            logger.debug("Completing social login for provider %s", provider)
            login = adapter.complete_login(request, app, token, response=token_data)
        except Exception as e:
            logger.error(f"complete_login failed: {e}", exc_info=True)
            return Response(
                {"detail": _("Invalid or expired provider token.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login.token = token
        login.state = {}

        try:
            # Returns an HttpResponseRedirect on BOTH the success path
            # (perform_login redirects to socialaccount_login_done) and the
            # pending-signup path (auto_signup blocked, e.g. no email from
            # Facebook). Do NOT treat every response as refusal; decide by
            # whether a persisted user exists below.
            complete_social_login(request, login)
        except ImmediateHttpResponse:
            return Response(
                {"detail": _("Login not permitted.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            return Response(
                {"detail": _("Social login failed: %(error)s") % {"error": str(e)}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # SocialLogin holds the user on .user; .account.user may not exist if signup was
        # not completed (e.g. pending signup redirect). Use .user safely to avoid
        # RelatedObjectDoesNotExist: SocialAccount has no user.
        try:
            user = login.user
        except Exception:
            user = None
        if user is None or not user.pk:
            try:
                user = login.account.user
            except Exception:
                user = None
        if user is None or not user.pk:
            # Signup never completed (provider returned no verified email, e.g.
            # Facebook without the email permission). Surface as 403 instead of
            # falling through with an unsaved user.
            return Response(
                {"detail": _("Login not permitted.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user.is_active:
            user.is_active = True
            user.save()

        primary_email = user.emailaddress_set.filter(primary=True).first()
        if primary_email and not primary_email.verified:
            primary_email.verified = True
            primary_email.save()

        extra_data = login.account.extra_data or {}
        picture_url = extra_data.get("picture")
        if picture_url and not user.picture:
            user.picture = picture_url

        refresh = RefreshToken.for_user(user)
        refresh["email"] = user.email
        refresh["role"] = user.role
        # ── Diagnostic: immediate validation on same process (safe metadata only) ──
        try:
            import hashlib

            from rest_framework_simplejwt.settings import api_settings
            from rest_framework_simplejwt.tokens import AccessToken

            access_str = str(refresh.access_token)
            # Validate immediately using same config
            validated = AccessToken(access_str)
            # Safe metadata (no token)
            alg = api_settings.ALGORITHM
            signing_key_hash = hashlib.sha256(str(api_settings.SIGNING_KEY).encode()).hexdigest()[
                :8
            ]
            logger.info(
                "JWT generated and immediately validated OK provider=%s user_id=%s token_type=%s alg=%s iss=%s aud=%s jti=%s signing_key_hash=%s pid=%s",
                provider,
                str(validated.get(api_settings.USER_ID_CLAIM)),
                validated.get(api_settings.TOKEN_TYPE_CLAIM),
                alg,
                validated.get("iss", ""),
                validated.get("aud", ""),
                str(validated.get("jti", ""))[:8],
                signing_key_hash,
                str(timezone.now().timestamp()),
            )
        except Exception as e:
            import hashlib

            from rest_framework_simplejwt.settings import api_settings

            try:
                signing_key_hash = hashlib.sha256(
                    str(api_settings.SIGNING_KEY).encode()
                ).hexdigest()[:8]
            except Exception:
                signing_key_hash = "unknown"
            logger.error(
                "JWT immediate validation FAILED provider=%s user_id=%s alg=%s signing_key_hash=%s error=%s",
                provider,
                str(getattr(user, "id", "")),
                api_settings.ALGORITHM,
                signing_key_hash,
                str(e),
                exc_info=True,
            )

        response_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "onboarding_required": user.role == "customer" and not user.onboarding_completed,
        }

        user.status = "active"
        user.is_verified = True
        user.oauth_provider = app.provider
        user.save(update_fields=["picture", "status", "is_verified", "oauth_provider", "oauth_id"])

        try:
            Device.objects.filter(device_uuid=device_uuid).update(
                is_active=True, user=user, last_seen_at=timezone.now()
            )
        except Exception as e:
            raise ValidationError({"detail": _("Failed to update device status: ") + str(e)})

        return Response(response_data)
