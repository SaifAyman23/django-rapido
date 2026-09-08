# Authentication Guide — OTP + JWT + OAuth (Google/Facebook via allauth) — Django Rapido V2.0

> **Brand:** Django Rapido V2.0 — Project-agnostic, reusable auth engine.
> **Stack:** Django 5.2 + DRF 3.16 + `django-allauth==65.18.0` + `djangorestframework_simplejwt==5.4.0` + PostgreSQL 17.
> **Covers:** Email+password → OTP verification (6 digits, 10m, 5 attempts) → JWT (refresh HttpOnly `Lax` + access body) + Password-reset (OTP → 15m `PasswordResetToken` → reset) + Social OAuth (Google/Facebook → auto-link → JWT). One file-map, zero hardcoding, copy-paste setup from scratch.

## Table of Contents

1. [Overview & Flow](#1-overview--flow)
2. [When You Need OAuth vs When You Don't](#2-when-you-need-oauth-vs-when-you-dont)
3. [What OAuth Infra Offers](#3-what-oauth-infra-offers)
4. [Architecture & Exact File Map (file:line)](#4-architecture--exact-file-map-fileline)
5. [How OAuth Actually Works — Step-by-Step](#5-how-oauth-actually-works--step-by-step)
6. [Setup From Zero to Current State (Copy-Paste)](#6-setup-from-zero-to-current-state-copy-paste)
7. [Frontend Integration — Web + Flutter (Token Exchange)](#7-frontend-integration--web--flutter-token-exchange)
8. [OTP+JWT Context — Kept Standalone](#8-otpjwt-context--kept-standalone)
9. [Throttling & Security](#9-throttling--security)
10. [Environment](#10-environment)
11. [Wiring (URLs, Admin, Settings)](#11-wiring-urls-admin-settings)
12. [How to Adjust / Enhance](#12-how-to-adjust--enhance)
13. [Testing & Debugging](#13-testing--debugging)
14. [Removal — How to Remove This Feature](#14-removal--how-to-remove-this-feature)

---

## 1. Overview & Flow

```
Register (email+password) ─┬─→ OTP email (6 digits, 10m, 5 attempts) ─→ Verify ─→ JWT (refresh HttpOnly + access body)
                           │                                          ↘ Password reset (OTP → token 15m → reset)
                           └─→ Social login (Google id_token / Facebook access_token  OR  PKCE code+verifier)
                                   → allauth adapter dedupe + auto-link by email → JWT (refresh+access + role/email claims)
                                                            ↘ optional device_uuid → Device activation (FCM)
```

**Generic & reusable:** No hardcoded `client_id`, no hardcoded role string (`"customer"`), no hardcoded URL. Everything dynamic via `SocialApp` (DB) / `settings.SOCIALACCOUNT_PROVIDERS` / `os.getenv` / `request`. See `§3.5 No Hardcoded Nonsense` in `AGENTS.md`.

| Concern | Source of truth | Never |
|---|---|---|
| `client_id` / `aud` | `SocialApp.objects.filter(provider=...)` + `settings.SOCIALACCOUNT_PROVIDERS[provider].APP` | `if aud == "822776...apps.googleusercontent.com"` |
| Roles | `getattr(user,"role")` + `create_role_permission("seller")` | `if user.role == "customer"` literal in auth |
| Secrets / URLs | `os.getenv` / `.env.example` | string literal in `views.py` / `adapters.py` |
| Business TZ | `os.getenv("BUSINESS_TIME_ZONE")` `project/settings/base.py:225` | `"Africa/Cairo"` literal in logic |

---

## 2. When You Need OAuth vs When You Don't

### Use OAuth (Google/Facebook via allauth) when:

- You have **native mobile** (Flutter/React Native) or **SPA** that already uses Google/Apple/Facebook SDK — SDK gives you `id_token`/`access_token` for free, you just exchange it for your own JWT and avoid password UX.
- You want **no-password onboarding** — one tap, account created, `is_verified=True`, no OTP email round-trip.
- You need **verified email for free** — provider has already verified the email; you can trust it and skip OTP.
- You need **multiple Google clients** (web + Android + iOS with different `client_id`) — infra handles `aud` fan-out (see `§5.4`).
- You want **FCM device linking** on first login — send `device_uuid` with social login, it activates the `Device`.

### You DON'T need OAuth when:

- **Internal / B2B / admin-only** app — email+password + OTP is simpler, fewer dependencies, no provider console setup.
- You must **enforce custom password policy** at registration — OTP+JWT `UserRegistrationSerializer` `accounts/serializers.py:48` is fully under your control; social users have no password.
- You need **offline / air-gapped** deploys — allauth needs outbound HTTPS to `googleapis.com` / `graph.facebook.com` to verify tokens (network dependency).
- You only have **web + no SDK** and don't want Google Cloud / Meta Developer project overhead — just keep OTP+JWT.
- You need **strict provider-agnostic audits** — JWT claims are yours either way; OAuth adds `oauth_provider`/`oauth_id` fields you may not need.

**Cost of enabling:** `+1` dependency (`django-allauth==65.18.0` `requirements.txt:24`), `+3` DB tables (`socialaccount_socialapp`, `socialaccount_socialaccount`, `socialaccount_socialtoken`), `+1` adapter file, `+1` view file, `+6` lines in `INSTALLED_APPS`/`MIDDLEWARE`/`AUTHENTICATION_BACKENDS`. No new Redis/Celery infra.

---

## 3. What OAuth Infra Offers

- **Providers:** `google` + `facebook` via `allauth.socialaccount.providers.google` / `facebook`. Extensible to `apple`, `github`, `twitter`, etc. by adding one `INSTALLED_APPS` line + one adapter entry + one `SocialApp` row.
- **Two login modes per provider** (both return your own JWT, not provider tokens):
  - **PKCE Code Flow** (web): frontend redirects to provider → provider redirects back with `code` → backend exchanges `code+code_verifier+redirect_uri` via `OAuth2Client` for `token_data`, then `adapter.complete_login`.
  - **SDK / Token Flow** (mobile preferred): frontend SDK (`google_sign_in`, `flutter_facebook_auth`) obtains `id_token` (Google) or `access_token` (Facebook) → backend verifies it with `adapter.complete_login` → issues JWT. No `redirect_uri` needed.
- **Multi-client Google:** Three OAuth clients (web/Android/iOS) each own `SocialApp` row; Google `id_token.aud == client_id` picks the right one — no hardcoding, no `apps[0]` for Google (see `§5.4`).
- **Auto-link by email:** `SocialAccountAdapter.pre_social_login()` `accounts/auth/adapters.py:40` links social login to existing local `CustomUser` by `EmailAddress` or `CustomUser.email` → prevents `UNIQUE` violation, verifies `EmailAddress.verified`.
- **Dedupe bug fix:** `SocialAccountAdapter.list_apps()` `accounts/auth/adapters.py:21` dedupes DB + `settings.SOCIALACCOUNT_PROVIDERS.APP` → prevents `MultipleObjectsReturned` on `get_app()` when the same `client_id` exists in both places; DB wins.
- **JWT on success:** `RefreshToken.for_user(user)` with `token["email"]` + `token["role"]` (extendable) — same JWT infra as email+password. `common/helpers.py:301` `set_refresh_token_cookie` still sets HttpOnly cookie if you want it; social view returns body `access`/`refresh` (`accounts/auth/views.py:556`).
- **Immediate validation diagnostic:** after issuing JWT, same-process `AccessToken(access_str)` validation logs `alg`, `signing_key_hash[:8]`, `jti[:8]` `accounts/auth/views.py:508-554` — catches `JWT_SECRET_KEY` drift before the client does.
- **Device activation:** optional `device_uuid` in request → `Device.objects.filter(device_uuid=...).update(is_active=True, user=user)` `accounts/auth/views.py:567-570`.
- **Unfold admin:** `Social Apps / Social Accounts / Social Tokens` under *Users & Accounts* `project/settings/unfold_config.py:299-314`.
- **Security posture:** `AllowAny` on `SocialLoginJWTView` (public), but tokens verified by provider; `500 → redirect → ImmediateHttpResponse → 403` is NOT treated as failure (see `§5.6`).

---

## 4. Architecture & Exact File Map (file:line)

```
accounts/
  auth/
    __init__.py:1                package marker
    adapters.py:20               class SocialAccountAdapter(DefaultSocialAccountAdapter)
    adapters.py:21               def list_apps(self, request, provider, client_id)  # dedupe DB+settings
    adapters.py:40               def pre_social_login(self, request, sociallogin)    # auto-link by email
    adapters.py:66               def _link(self, request, sociallogin, user, email_address)
    views.py:44                  PROVIDER_ADAPTERS = {"google": GoogleOAuth2Adapter, "facebook": FacebookOAuth2Adapter}
    views.py:50                  def _decode_id_token_aud(id_token) -> str|None  # base64 aud without verifying
    views.py:66                  SOCIAL_LOGIN_DESCRIPTION (OpenAPI long description, PKCE + Flutter guide)
    views.py:154                 @extend_schema(...) class SocialLoginJWTView(APIView)
    views.py:293                 class SocialLoginJWTView              # permission_classes=[AllowAny], authentication_classes=[]
    views.py:297                 def _get_provider_apps(self, provider) → list[SocialApp]  # DB first, settings fallback
    views.py:314                 def _find_app_by_id_token_aud(self, apps, id_token)      # Google aud==client_id match
    views.py:324                 def _exchange_code(self, request, adapter, apps, code, verifier, redirect_uri) # fan-out
    views.py:355                 def post(self, request, provider)      # entry point POST /api/v1/users/api/auth/social/<provider>/
    views.py:396-425             Google id_token aud matching + 401 No matching client
    views.py:442                 adapter.complete_login(request, app, token, response=token_data)
    views.py:459                 complete_social_login(request, login)  # may raise ImmediateHttpResponse
    views.py:474-490             login.user / login.account.user resolution + 403 if pk is None (no verified email)
    views.py:505-566             RefreshToken.for_user(user) + refresh["email"]/["role"] + immediate AccessToken check
    views.py:567                 Device activation + user status/is_verified/oauth_provider save

  models.py:24                   class OTPRecord(TimestampedModel, UUIDModel) + OTPType(TextChoices)
  models.py:55                   class PasswordResetToken(TimestampedModel, UUIDModel)
  helpers.py:20                  def validate_credentials(email, password) -> User
  helpers.py:76                  def generate_otp() -> str
  helpers.py:81                  def generate_password_reset_token() -> str
  helpers.py:86                  def create_and_send_otp(user, otp_type, expiry_minutes) -> OTPRecord
  helpers.py:116                 def validate_otp(code, purpose, max_attempts) -> OTPRecord  # F() guard
  serializers.py:15              class CustomTokenObtainPairSerializer(TokenObtainPairSerializer)  # username_field lax + validate_credentials + token["email"]
  serializers.py:48              class UserRegistrationSerializer  # social-only reuse via has_usable_password()
  serializers.py:106             class UserVerifyAccountSerializer  # code 6 + purpose → validate_otp
  serializers.py:122             class UserResetPasswordSerializer # token + password matching + expiry
  serializers.py:141             class UserEmailSerializer         # email + type(OTPType.values)
  serializers.py:157             class UserDetailSerializer
  views.py:37                    class CustomTokenObtainPairView(TokenObtainPairView)  # set_refresh_token_cookie
  views.py:53                    class CookieTokenRefreshView(TokenObtainPairView)     # body or COOKIE refresh_token
  views.py:74                    class UserViewSet(BaseViewSet) + actions register/verify_account/send_verification_code/reset_password/me/logout
  views.py:108                   def register  @transaction.atomic AllowAny + AuthRateThrottle
  views.py:150                   def verify_account  EMAIL_VERIFICATION → JWT / PASSWORD_RESET → PasswordResetToken
  views.py:205                   def send_verification_code  anti-enumeration always 200
  views.py:252                   def reset_password  select_for_update token attempts<5
  urls.py:14                     router.register(r"users", UserViewSet)
  urls.py:18                     path("login/", CustomTokenObtainPairView)
  urls.py:20                     path("token/refresh/", CookieTokenRefreshView)
  urls.py:21-22                  path("token/verify|blacklist/")
  admin.py:10                    @admin.register(OTPRecord) OTPRecordAdmin(BaseAdmin)
  admin.py:20                    @admin.register(PasswordResetToken)
  tasks.py:16                    @shared_task send_verification_email(user_id, email, otp) max_retries=3
  tasks.py:58                    @shared_task notify_welcome_email
  tasks.py:89                    @shared_task cleanup_expired_sessions

project/settings/base.py:60      INSTALLED_APPS core
project/settings/base.py:88      # "allauth.socialaccount.providers.google"  (uncomment to enable)
project/settings/base.py:98      # "allauth.socialaccount.providers.facebook" (uncomment to enable)
project/settings/base.py:92      "allauth", "allauth.account", "allauth.socialaccount"  # enabled even when providers commented
project/settings/base.py:101     SITE_ID = 1  # required by allauth
project/settings/base.py:103     AUTHENTICATION_BACKENDS = [ModelBackend]  # + "allauth.account.auth_backends.AuthenticationBackend" when social enabled
project/settings/base.py:108     MIDDLEWARE  # :119 allauth.account.middleware.AccountMiddleware (always active)
project/settings/base.py:254     # ── allauth provider verification only ──
project/settings/base.py:258     SOCIALACCOUNT_AUTO_SIGNUP = True
project/settings/base.py:259     SOCIALACCOUNT_EMAIL_VERIFICATION = "none"  # provider already verified → trust
project/settings/base.py:260     SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
project/settings/base.py:261     SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
project/settings/base.py:262     SOCIALACCOUNT_STORE_TOKENS = True
project/settings/base.py:263     # SOCIALACCOUNT_ADAPTER = "accounts.auth.adapters.SocialAccountAdapter"
project/settings/base.py:264     # SOCIALACCOUNT_PROVIDERS = {"google": {"SCOPE":..., "APP": {"client_id": os.getenv(...)}}}
project/settings/base.py:268-274 # facebook VERSION v21.0
project/settings/base.py:356     REST_FRAMEWORK DEFAULT_AUTHENTICATION_CLASSES JWTAuthentication
project/settings/base.py:369-378 DEFAULT_THROTTLE_RATES anon 100/h, user 1000/h, auth 30/m
project/settings/base.py:390     SIMPLE_JWT ACCESS 30m / REFRESH 30d / BLACKLIST_AFTER_ROTATION True / ALGORITHM HS256
project/settings/base.py:398     SIGNING_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY
project/urls.py:40               path("api/v1/users/", include("accounts.urls"))
project/urls.py:75               path("accounts/social/signup/", lambda ... 404) # HTML stub, prevents 500 when auto_signup blocked
project/urls.py:40-72            i18n_patterns admin/live-logs + admin/ + schema/swagger
project/settings/unfold_config.py:277 navigation Users & Accounts → Social Apps/Accounts/Tokens (3 items)
common/throttles.py:16           class AuthRateThrottle(SimpleRateThrottle) scope=auth get_cache_key IP
common/helpers.py:301            def set_refresh_token_cookie(response, token, lifetime=30d) HttpOnly Lax
common/helpers.py:332            def set_token_cookies (legacy wrapper)
common/helpers.py:356            def clear_token_cookies
common/helpers.py:371            def get_refresh_token_from_cookie
common/mixins.py:88              class BaseViewSetMixin  handle_exception envelope {"error":{"code":...}} + SENSITIVE_LOG_KEYS:444
common/models.py:378             class CustomUser(AbstractUser, UUIDModel) email USERNAME_FIELD, Status UNVERIFIED/ACTIVE/SUSPENDED, is_verified, verified_at
requirements.txt:24              django-allauth==65.18.0
.env.example:71-79               # GOOGLE_OAUTH_CLIENT_ID/SECRET + FACEBOOK_OAUTH_CLIENT_ID/SECRET (commented, REUSE)
```

**DB tables added by allauth** (after `migrate`): `socialaccount_socialapp`, `socialaccount_socialaccount`, `socialaccount_socialtoken` + `account_emailaddress`. No OTP tables needed for social flow.

---

## 5. How OAuth Actually Works — Step-by-Step

### 5.1 Two entry paths, one exit (your JWT)

```
Web (PKCE)                               Mobile SDK (id_token/access_token)
─────────                                ─────────────────────────────────
FE → GET provider authorize?             FE → google_sign_in / flutter_facebook_auth
       code_challenge=S256                 → id_token (Google) / access_token (Facebook)
FE ←  provider?code=...                  FE → POST /api/v1/users/api/auth/social/<provider>/
FE → POST /api/v1/.../social/<p>/        {id_token: "eyJ..."} (+ device_uuid)
       {code, redirect_uri,               │
        code_verifier}                    │
                │                         │
                └────→ SocialLoginJWTView.post() accounts/auth/views.py:355 ─┐
                        ├─ _get_provider_apps() :297  DB rows, else settings fallback
                        ├─ if code: _exchange_code() :324  fan-out over each SocialApp
                        │            OAuth2Client(...).get_access_token(code, pkce_code_verifier)
                        │            only the issuing client succeeds (redirect_uri+verifier must match)
                        ├─ elif id_token: _find_app_by_id_token_aud() :314 decode aud → client_id == aud ?
                        │            Google: must match, else 401 No matching client :422
                        │            Facebook: apps[0] (no aud check) :428
                        ├─ SocialToken(app, token) + adapter.complete_login() :442  ← signature verified here
                        ├─ complete_social_login(request, login) :459
                        │     → SocialAccountAdapter.list_apps() :21 dedupes
                        │     → SocialAccountAdapter.pre_social_login() :40 auto-links by email
                        │     → creates/updates SocialAccount + EmailAddress + CustomUser
                        │     raises ImmediateHttpResponse on redirect → caught → 403 Login not permitted
                        ├─ resolve user: login.user or login.account.user :474  (401→403 if no pk = no verified email)
                        ├─ activate user, verify primary EmailAddress, copy picture :492-503
                        ├─ RefreshToken.for_user(user) + token["email"], token["role"] + immediate AccessToken check :505-554
                        ├─ user.status=active, is_verified=True, oauth_provider/id :562-565
                        └─ Device activation if device_uuid :567
                        → 200 {access, refresh, onboarding_required}  (refresh long-lived, access short)
```

### 5.2 Adapter — `accounts/auth/adapters.py:20`

**`list_apps(request, provider, client_id):21`** — dedupes `super().list_apps()` which merges DB `SocialApp` + `settings.SOCIALACCOUNT_PROVIDERS[provider].APP`. Without it, same `client_id` in both places → `MultipleObjectsReturned` in `get_app()`. Fix: DB-backed `app.pk is not None` wins; settings fallback kept only if key not seen.

```python
# accounts/auth/adapters.py:21
class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def list_apps(self, request, provider=None, client_id=None):
        apps = super().list_apps(request, provider=provider, client_id=client_id)
        seen_client_ids = set()
        deduped = []
        for app in apps:
            is_db_backed = app.pk is not None
            key = (app.provider, app.client_id)
            if is_db_backed:
                if key in seen_client_ids: continue
                seen_client_ids.add(key); deduped.append(app)
            else:
                if key not in seen_client_ids:
                    seen_client_ids.add(key); deduped.append(app)
        return deduped
```

**`pre_social_login(request, sociallogin):40`** — auto-link. `sociallogin.is_existing` → return. `SocialAccount.objects.filter(provider, uid).first()` → exists → return (already linked). Extract `email = (extra_data.get("email") or "").lower()` → `EmailAddress.objects.filter(email__iexact=email).first()` → `_link(..., email_address.user)` or `CustomUser.objects.filter(email__iexact=email, is_active=True).first()` → `_link(..., user)`. Prevents `UNIQUE email` crash when a user registered via password then logs in via Google with same email. `_link:66` does `sociallogin.connect(request, user)` + `email_address.verified=True` if needed + `user.is_active=True`.

### 5.3 Google `aud` check — `accounts/auth/views.py:50-63, 314-425`

Google issues **one OAuth client per platform** (web/Android/iOS), each with distinct `client_id`. The `id_token` payload's `aud` claim equals the `client_id` that minted it. Backend must pick the matching `SocialApp`.

```python
# accounts/auth/views.py:50
def _decode_id_token_aud(id_token):
    try:
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
        return data.get("aud")  # no signature verify — verification happens in complete_login
    except Exception:
        return None
```

Flow: `_find_app_by_id_token_aud:314` loops `apps` for `app.client_id == aud`. Matched → `logger.info aud=... matched ...` `accounts/auth/views.py:409`; not matched → `logger.warning ... Available: [a.client_id[:12]...]` + `401 No matching Google OAuth client for this ID token.` No hardcoding, no `apps[0]` for Google. **Facebook:** no `aud`, uses `apps[0]` directly `accounts/auth/views.py:428` — simple as-is.

> Never `if aud == "822776...apps.googleusercontent.com"` — always `SocialApp.objects.filter(provider="google")` seeded via admin (debug log `available = [a.client_id[:12]...]`).

### 5.4 PKCE Code exchange — `accounts/auth/views.py:324-353`

```
FE: code_challenge = S256(code_verifier) on authorize
     ─→ provider stores challenge
BE: client.get_access_token(code, pkce_code_verifier=verifier) — provider verifies challenge==S256(verifier)
```

Facebook has **no PKCE** — `code_verifier` is ignored (pass nothing). Google **requires** it. Backend tries each `SocialApp` until one succeeds (mobile clients have empty `secret`, `OAuth2Client` strips empty secrets, so PKCE still works).

```python
# accounts/auth/views.py:324
def _exchange_code(self, request, adapter, apps, code, code_verifier, redirect_uri):
    last_error = None
    for app in apps:
        client = OAuth2Client(request, app.client_id, app.secret,
                              adapter.access_token_method, adapter.access_token_url, redirect_uri)
        try:
            kwargs = {"code": code}
            if code_verifier: kwargs["pkce_code_verifier"] = code_verifier
            token_data = client.get_access_token(**kwargs)
            return token_data, app
        except Exception as e:
            last_error = e; logger.warning("Code exchange failed for client %s", app.client_id)
    raise last_error or OAuth2Error("No provider client configured.")
```

**Gotchas:** codes single-use → `redirect_uri mismatch` often means code already consumed. `redirect_uri` must match provider console **exactly** (scheme/host/trailing slash).

### 5.5 allauth settings — `project/settings/base.py:258-274`

```python
# project/settings/base.py:258
SOCIALACCOUNT_AUTO_SIGNUP = True              # create CustomUser if no auto-link match
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"      # trust provider-verified email (skip OTP)
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True  # allow email auto-link
SOCIALACCOUNT_STORE_TOKENS = True             # persist SocialToken
# SOCIALACCOUNT_ADAPTER = "accounts.auth.adapters.SocialAccountAdapter"  # uncomment to enable
# SOCIALACCOUNT_PROVIDERS = {
#     "google": {"SCOPE": ["openid","profile","email"], "APP": {"client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID"), "secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")}},
#     "facebook": {"SCOPE": ["email","public_profile"], "VERSION": "v21.0", "APP": {"client_id": os.getenv("FACEBOOK_OAUTH_CLIENT_ID"), "secret": os.getenv("FACEBOOK_OAUTH_CLIENT_SECRET")}},
# }
```

`SCOPE` must include `email` (and `openid` for Google) so `extra_data["email"]` is populated for auto-link + JWT `email` claim. `VERSION v21.0` pins Graph API.

### 5.6 `complete_social_login` & `ImmediateHttpResponse`

`complete_social_login(request, login)` `accounts/auth/views.py:459` returns `HttpResponseRedirect` on **both** success (`perform_login → socialaccount_login_done`) and pending-signup (`auto_signup` blocked e.g. Facebook without `email` permission). The view catches `ImmediateHttpResponse:460 → 403 Login not permitted` (adapter blocked login) and generic `Exception:465 → 500 Social login failed`. Then it resolves `user = login.user` (fallback `login.account.user`) `accounts/auth/views.py:474`; if `user is None or not user.pk` → `403 Login not permitted` — surfaces missing verified email instead of returning unsaved user.

### 5.7 JWT issuance — `accounts/auth/views.py:505-566`

```python
# accounts/auth/views.py:505
refresh = RefreshToken.for_user(user)
refresh["email"] = user.email          # cf. CustomTokenObtainPairSerializer.get_token:42 adds email
refresh["role"] = user.role            # REUSE: generic — reads attr, no hardcoded "customer"
response_data = {"access": str(refresh.access_token), "refresh": str(refresh),
                 "onboarding_required": user.role == "customer" and not user.onboarding_completed}
user.status = "active"; user.is_verified = True
user.oauth_provider = app.provider; user.save(update_fields=["picture","status","is_verified","oauth_provider","oauth_id"])
```

Immediately validates with `AccessToken(access_str)` `accounts/auth/views.py:515` and logs `signing_key_hash[:8]` / `alg` / `jti[:8]` — safe metadata, no token leakage — useful in Live Logs `dashboard/live_logs.py:38`.

---

## 6. Setup From Zero to Current State (Copy-Paste)

Assume no OAuth exists. Follow in order — each step leaves the app runnable.

### Step 0 — Install

```bash
pip install django-allauth==65.18.0
# or: pip install -r requirements.txt  # already contains it requirements.txt:24
```

### Step 1 — Settings `project/settings/base.py`

**1a. `INSTALLED_APPS:60`** — keep `allauth` triple enabled (already in base), uncomment providers you need:

```python
# project/settings/base.py:88
INSTALLED_APPS = [
    # ...
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",    # ← uncomment
    "allauth.socialaccount.providers.facebook",  # ← uncomment
]
```

**1b. `SITE_ID:101`** — already set:

```python
SITE_ID = 1
```

**1c. `AUTHENTICATION_BACKENDS:103`** — uncomment allauth backend:

```python
# project/settings/base.py:103
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",  # ← uncomment
]
```

**1d. `MIDDLEWARE:108`** — `AccountMiddleware` already active at `base.py:119`:

```python
MIDDLEWARE = [
    # ...
    "allauth.account.middleware.AccountMiddleware",  # must be after AuthenticationMiddleware
]
```

**1e. allauth block `base.py:258-274`** — uncomment adapter + providers:

```python
# project/settings/base.py:258
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_ADAPTER = "accounts.auth.adapters.SocialAccountAdapter"
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["openid", "profile", "email"],
        "APP": {"client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID"), "secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")},
    },
    "facebook": {
        "SCOPE": ["email", "public_profile"],
        "VERSION": "v21.0",
        "APP": {"client_id": os.getenv("FACEBOOK_OAUTH_CLIENT_ID"), "secret": os.getenv("FACEBOOK_OAUTH_CLIENT_SECRET")},
    },
}
```

**1f. Env ` .env.example:71-79` + `.env`** — add (never commit `.env`):

```bash
# .env
GOOGLE_OAUTH_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxxxx
FACEBOOK_OAUTH_CLIENT_ID=1234567890
FACEBOOK_OAUTH_CLIENT_SECRET=abcdef...
# For 3 Google clients (web/Android/iOS) put ONE client here; others go in SocialApp DB rows.
```

> `GOOGLE_OAUTH_CLIENT_ID` here is settings fallback; DB `SocialApp` rows win when present (`_get_provider_apps:297`). For single-client projects, settings alone suffices.

### Step 2 — Adapter `accounts/auth/adapters.py`

Create the folder + file verbatim:

```bash
mkdir -p accounts/auth
```

```python
# accounts/auth/adapters.py:20
"""
REUSE: Generic SocialAccountAdapter — fixes two production bugs:
1. Duplicate SocialApp (DB + settings.APP) → MultipleObjectsReturned → list_apps() dedupes
2. Existing local account + social same email → UNIQUE → pre_social_login() auto-links
Wire via: SOCIALACCOUNT_ADAPTER = "accounts.auth.adapters.SocialAccountAdapter"
"""
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def list_apps(self, request, provider=None, client_id=None):  # :21
        apps = super().list_apps(request, provider=provider, client_id=client_id)
        seen_client_ids, deduped = set(), []
        for app in apps:
            is_db_backed = app.pk is not None
            key = (app.provider, app.client_id)
            if is_db_backed:
                if key in seen_client_ids: continue
                seen_client_ids.add(key); deduped.append(app)
            else:
                if key not in seen_client_ids:
                    seen_client_ids.add(key); deduped.append(app)
        return deduped

    def pre_social_login(self, request, sociallogin):  # :40
        if sociallogin.is_existing: return
        existing_account = SocialAccount.objects.filter(provider=sociallogin.account.provider, uid=sociallogin.account.uid).first()
        if existing_account: return
        email = (sociallogin.account.extra_data or {}).get("email") or ""
        email = email.lower()
        if not email: return
        email_address = EmailAddress.objects.filter(email__iexact=email).first()
        if email_address and email_address.user_id:
            self._link(request, sociallogin, email_address.user, email_address); return
        user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
        if user: self._link(request, sociallogin, user)

    def _link(self, request, sociallogin, user, email_address=None):  # :66
        sociallogin.connect(request, user)
        if email_address and not email_address.verified:
            email_address.verified = True; email_address.save()
        if not user.is_active:
            user.is_active = True; user.save()
```

```python
# accounts/auth/__init__.py:1
"""Accounts auth helpers — social account adapter package."""
```

### Step 3 — OAuth View `accounts/auth/views.py`

Create `accounts/auth/views.py:293` exactly as in repo (574 lines). Key imports: `GoogleOAuth2Adapter`, `FacebookOAuth2Adapter`, `OAuth2Client`, `OAuth2Error`, `SocialApp`, `SocialToken`, `complete_social_login`, `RefreshToken`. Copy `PROVIDER_ADAPTERS:44`, `_decode_id_token_aud:50`, `SOCIAL_LOGIN_DESCRIPTION:66`, `SocialLoginJWTView:293` with `_get_provider_apps:297`, `_find_app_by_id_token_aud:314`, `_exchange_code:324`, `post:355`.

Add serializers if not present:

```python
# accounts/auth/serializers.py (create)
from rest_framework import serializers

class SocialLoginRequestSerializer(serializers.Serializer):
    code = serializers.CharField(required=False, allow_blank=True)
    redirect_uri = serializers.CharField(required=False, allow_blank=True)
    code_verifier = serializers.CharField(required=False, allow_blank=True)
    id_token = serializers.CharField(required=False, allow_blank=True)
    access_token = serializers.CharField(required=False, allow_blank=True)
    device_uuid = serializers.UUIDField(required=False)

class SocialLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    onboarding_required = serializers.BooleanField(required=False)

class SocialLoginErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
```

### Step 4 — URLs

**`accounts/urls.py:1`** — ensure router exists, add social route (currently commented `accounts/urls.py:28`). Wire to `accounts.auth.views.SocialLoginJWTView`:

```python
# accounts/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from accounts.views import CookieTokenRefreshView, CustomTokenObtainPairView, UserViewSet
from accounts.auth.views import SocialLoginJWTView

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/social/<str:provider>/", SocialLoginJWTView.as_view(), name="social_login"),
]
```

**`project/urls.py:29`** — include:

```python
# project/urls.py:29
api_prefix = "api/v1"
urlpatterns = [
    path(f"{api_prefix}/users/", include("accounts.urls")),
    # ...
] + i18n_patterns(...)

# HTML stub — prevents 500 when auto_signup blocked (already in project/urls.py:75)
urlpatterns += [path("accounts/social/signup/",
    lambda r: HttpResponse("Social signup via HTML not supported. Use POST /api/v1/users/api/auth/social/<provider>/", status=404),
    name="socialaccount_signup")]
```

### Step 5 — Admin seeding (SocialApp)

Do **not** hardcode `client_id` in code — seed via admin or fixture:

**Via admin UI** (`/admin/socialaccount/socialapp/add/`):
- Provider: `google`, Name: `Google Web`, Client id: `xxxxx.apps.googleusercontent.com`, Secret: `GOCSPX-xxxx`, Sites: select `example.com` (SITE_ID=1). Repeat for `Google Android` (secret blank), `Google iOS`.
- Provider: `facebook`, Client id, Secret, `Sites`.

**Via shell / fixture:**

```python
# seed_social_apps.py
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

site = Site.objects.get(id=1)
for provider, client_id, secret, name in [
    ("google", "WEB_ID.apps.googleusercontent.com", "WEB_SECRET", "Google Web"),
    ("google", "ANDROID_ID.apps.googleusercontent.com", "", "Google Android"),
    ("google", "IOS_ID.apps.googleusercontent.com", "", "Google iOS"),
    ("facebook", "FB_ID", "FB_SECRET", "Facebook"),
]:
    app, _ = SocialApp.objects.get_or_create(provider=provider, client_id=client_id,
                                             defaults={"name": name, "secret": secret})
    app.sites.add(site)
```

Mobile clients have **no secret** — `OAuth2Client` strips empty secrets, PKCE still works.

**Provider console setup:**
- Google Cloud → Credentials → Create OAuth client (Web, Android, iOS) → Authorized redirect URIs must include your `redirect_uri` exactly (e.g. `http://localhost:5173/auth/callback`, `com.example.app:/oauth2redirect`).
- Facebook → Developers → App → Facebook Login → Valid OAuth Redirect URIs = same `redirect_uri`.

### Step 6 — Migrate & Verify

```bash
python manage.py migrate  # creates socialaccount_* tables
python manage.py check
python manage.py shell -c "from allauth.socialaccount.models import SocialApp; print(list(SocialApp.objects.values('provider','client_id')))"
# Should list seeded apps
make check-format && make test
```

### Step 7 — Test (copy-paste curl)

```bash
# SDK flow — Google id_token (mobile)
curl -X POST http://localhost:8000/api/v1/users/api/auth/social/google/ \
  -H "Content-Type: application/json" \
  -d '{"id_token":"eyJhbGciOiJSUzI1NiIs...","device_uuid":"a3f1c2d4-0000-4000-8000-000000000000"}'
# → 200 {"access":"eyJ...","refresh":"eyJ...","onboarding_required": false}

# SDK flow — Facebook access_token
curl -X POST http://localhost:8000/api/v1/users/api/auth/social/facebook/ \
  -H "Content-Type: application/json" \
  -d '{"access_token":"EAA...ZCw"}'
# → 200

# PKCE Code flow — Google (web)
curl -X POST http://localhost:8000/api/v1/users/api/auth/social/google/ \
  -H "Content-Type: application/json" \
  -d '{"code":"4/0Aea...","code_verifier":"dBjft...","redirect_uri":"http://localhost:5173/auth/callback"}'
# → 200

# Wrong audience → 401
curl -X POST http://localhost:8000/api/v1/users/api/auth/social/google/ \
  -d '{"id_token":"<token with aud not in SocialApp>"}'
# → 401 {"detail":"No matching Google OAuth client for this ID token."}

# Use JWT
curl http://localhost:8000/api/v1/users/users/me/ -H "Authorization: Bearer <access>"
```

---

## 7. Frontend Integration — Web + Flutter (Token Exchange)

### Web (PKCE) — recommended for SPA

```ts
// 1. Generate PKCE pair (client-side)
const verifier = randomString(64); // base64url 43-128 chars
const challenge = await pkceChallenge(verifier); // S256
sessionStorage.setItem("pkce_verifier", verifier);

// 2. Redirect to provider authorize
const params = new URLSearchParams({
  client_id: GOOGLE_CLIENT_ID,
  redirect_uri: "http://localhost:5173/auth/callback",
  response_type: "code",
  scope: "openid profile email",
  code_challenge: challenge,
  code_challenge_method: "S256",
});
location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params}`;

// 3. Callback handler /auth/callback?code=...
const code = new URLSearchParams(location.search).get("code");
const verifier2 = sessionStorage.getItem("pkce_verifier");
const { data } = await axios.post("/api/v1/users/api/auth/social/google/", {
  code, code_verifier: verifier2, redirect_uri: "http://localhost:5173/auth/callback",
});
localStorage.setItem("access", data.access);
localStorage.setItem("refresh", data.refresh);
axios.defaults.headers.common.Authorization = `Bearer ${data.access}`;
```

For Facebook, same but **omit `code_verifier`** — send `{code, redirect_uri}` only `accounts/auth/views.py:76`.

### Flutter — SDK flow (recommended)

Use SDK, not PKCE — simpler, no browser redirect, no custom scheme.

```dart
// pubspec: google_sign_in, flutter_facebook_auth
import 'package:google_sign_in/google_sign_in.dart';

final google = GoogleSignIn(
  scopes: ['email', 'profile'],
  // For Android/iOS, build with google-services.json / GoogleService-Info.plist.
  // If using webClientId, set serverClientId to the WEB client_id.
  serverClientId: 'WEB_CLIENT_ID.apps.googleusercontent.com',
);
final account = await google.signIn();
final auth = await account!.authentication;
final idToken = auth.idToken; // ← send this, NOT accessToken

final res = await dio.post('/api/v1/users/api/auth/social/google/', data: {
  'id_token': idToken,
  'device_uuid': deviceUuid, // optional, from notifications Device
});
final access = res.data['access'];
// Store refresh securely (flutter_secure_storage), set Authorization header
```

**Google requirements:** `id_token` only (backend rejects `access_token` for Google `accounts/auth/views.py:370`), `aud` must equal one of the three seeded `SocialApp.client_id` (build app with matching `google-services.json`), request `email` scope, fetch fresh `id_token` per login (1h expiry). `device_uuid` optional `accounts/auth/views.py:368`.

Facebook Flutter: `flutter_facebook_auth` → `accessToken.token` → `POST {access_token}`.

### Token refresh (both)

```bash
curl -X POST http://localhost:8000/api/v1/users/token/refresh/ \
  -H "Content-Type: application/json" -d '{"refresh":"<refresh>"}'
# or via cookie: --cookie "refresh_token=..."
```

---

## 8. OTP+JWT Context — Kept Standalone

OAuth section is deep and standalone; this keeps OTP+JWT as the password-based companion. Both issue the same JWT.

### Models `accounts/models.py:24,55`

```python
# accounts/models.py:24
class OTPRecord(TimestampedModel, UUIDModel):
    class OTPType(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", _("Email Verification")
        PASSWORD_RESET = "password_reset", _("Password Reset")
    user = FK(User, on_delete=CASCADE, related_name="otp_records")
    otp = CharField(6)
    expires_at = DateTimeField
    type = CharField(choices=OTPType)
    attempts = IntegerField(default=0)
    is_used = BooleanField(default=False)
    # Meta indexes: (otp, type, expires_at) + (user, type)  accounts/models.py:46

# accounts/models.py:55
class PasswordResetToken(TimestampedModel, UUIDModel):
    user = FK(User, related_name="password_reset_tokens")
    token = CharField(256, unique=True)  # secrets.token_urlsafe(32) → 43 chars accounts/helpers.py:81
    expires_at = DateTimeField; is_used = BooleanField(default=False)
    attempts = IntegerField(default=0)
```

### Helpers `accounts/helpers.py`

| Helper | Location | Notes |
|---|---|---|
| `validate_credentials(email,password)->User` | `helpers.py:20` | empty+check_password+SUSPENDED+is_banned+optional UNVERIFIED/role gate; wrap with role check if needed |
| `generate_otp()->str` | `helpers.py:76` | `random 100000-999999` |
| `generate_password_reset_token()->str` | `helpers.py:81` | `secrets.token_urlsafe(32)` |
| `create_and_send_otp(user, otp_type="email_verification", expiry_minutes=10) -> OTPRecord` | `helpers.py:86` | sync `send_verification_email(user.id,email,otp)`; REUSE: swap to `.delay()` for Celery |
| `validate_otp(code, purpose, max_attempts=5)->OTPRecord` | `helpers.py:116` | filters `is_used=False, expires_at__gte=now()`, `F("attempts")+1` race-safe |

### Serializers `accounts/serializers.py`

- `CustomTokenObtainPairSerializer:15` — `username_field` lax CharField, calls `validate_credentials:25`, `get_token:41` adds `token["email"]` (add `role` if needed).
- `UserRegistrationSerializer:48` — social-only reuse (`has_usable_password()` check `:62`), username collision loop `:84`.
- `UserVerifyAccountSerializer:106` — `code` 6 chars → `validate_otp` → `otp_record`.
- `UserResetPasswordSerializer:122` — `token` + `password` matching, expiry check.
- `UserEmailSerializer:141` — `email` + `type` (validates `OTPType.values`).
- `UserDetailSerializer:157` — read-only `id/created_at/updated_at`.

### Views `accounts/views.py:37,53,74`

- `CustomTokenObtainPairView:37` — `serializer.validated_data["refresh"]` → `set_refresh_token_cookie(response, token)` `common/helpers.py:301` (HttpOnly `Lax`).
- `CookieTokenRefreshView:53` — `refresh = data["refresh"] or COOKIE["refresh_token"]` body wins, rotates cookie.
- `UserViewSet:74` — `register:108` `AllowAny+AuthRateThrottle @transaction.atomic` → `on_commit(lambda: create_and_send_otp(user))`
- `verify_account:150` — `EMAIL_VERIFICATION:157` sets `is_verified/active/verified_at` → returns `refresh+access`; `PASSWORD_RESET:180` creates `PasswordResetToken` 15m.
- `send_verification_code:205` — anti-enumeration always `200` even if email not found `:214`; creates 10m OTP `on_commit delay` `:235`.
- `reset_password:252` — `select_for_update:258` token, `attempts<5`, `set_password`, `is_used`.
- `me:88` GET, `logout:293` blacklist + `clear_token_cookies`.

### JWT Settings `project/settings/base.py:390-411`

`ACCESS 30m`, `REFRESH 30d`, `BLACKLIST_AFTER_ROTATION True`, `ALGORITHM HS256`, `SIGNING_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY`, `AUTH_HEADER_TYPES=("Bearer",)`. `REST_FRAMEWORK:356` `JWTAuthentication`, `AllowAny` read / `IsAuthenticated` write, pagination `StandardPagination`.

### Curl — Register → Verify → Login

```bash
curl -X POST http://localhost:8000/api/v1/users/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Pass123!","password_confirm":"Pass123!"}'
# → 201 {detail: "OTP sent to email"}

curl -X POST http://localhost:8000/api/v1/users/users/verify/ \
  -H "Content-Type: application/json" \
  -d '{"code":"123456","purpose":"email_verification"}'
# → 200 {refresh, access}

curl -X POST http://localhost:8000/api/v1/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"Pass123!"}'
# → 200 {refresh, access} + Set-Cookie: refresh_token=...

curl -X POST http://localhost:8000/api/v1/users/token/refresh/ \
  -H "Content-Type: application/json" -d '{"refresh":"<refresh>"}'

# Password reset
curl -X POST http://localhost:8000/api/v1/users/users/send-verification-code/ \
  -d '{"email":"user@example.com","type":"password_reset"}' # → 200 always
curl -X POST http://localhost:8000/api/v1/users/users/verify/ \
  -d '{"code":"123456","purpose":"password_reset"}' # → 200 {token:"abc..."}
curl -X POST http://localhost:8000/api/v1/users/users/reset-password/ \
  -d '{"token":"abc...","password":"NewPass123!","password_confirm":"NewPass123!"}'
```

---

## 9. Throttling & Security

- `AuthRateThrottle` `common/throttles.py:16` `scope=auth` IP-based, not user — `anon 30/m` `project/settings/base.py:377`. Wire on `register/verify/send/reset` `accounts/views.py:105,146,203,249`. OAuth `SocialLoginJWTView` is `AllowAny` but provider-verified; add `throttle_classes=[AuthRateThrottle]` there if you want same `30/m` on social.
- `BaseViewSetMixin._scrub_request_data` `common/mixins.py:450` masks `password/code/otp/secret/token/refresh` before `LOG_REQUESTS` debug.
- `transaction.atomic + select_for_update` on OTP `accounts/helpers.py:136` `F()` + `accounts/views.py:258` token mutation — prevents race on concurrent verify/reset.
- Anti-enumeration on `send_verification_code:205` — always `200` even if email not found `accounts/views.py:214`.
- No secrets in code — `os.getenv("GOOGLE_OAUTH_CLIENT_ID")` `base.py:267` / `FACEBOOK_*` `:272` — never commit `.env`.

---

## 10. Environment

```bash
# .env.example:71-79
# GOOGLE_OAUTH_CLIENT_ID=
# GOOGLE_OAUTH_CLIENT_SECRET=
# FACEBOOK_OAUTH_CLIENT_ID=
# FACEBOOK_OAUTH_CLIENT_SECRET=

# JWT — dedicated key falls back to SECRET_KEY
# .env.example:52
# JWT_SECRET_KEY=        # base.py:398 SIGNING_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY
# JWT_ALGORITHM=HS256    # base.py:396

# Email (OTP)
# .env.example:58-69
# EMAIL_HOST=smtp.gmail.com  EMAIL_PORT=587  EMAIL_HOST_USER/EMAIL_HOST_PASSWORD  DEFAULT_FROM_EMAIL
```

---

## 11. Wiring (URLs, Admin, Settings)

```python
# accounts/urls.py:14 — UserViewSet + JWT
router.register(r"users", UserViewSet)
path("login/", CustomTokenObtainPairView.as_view())
path("token/refresh/", CookieTokenRefreshView.as_view())
path("api/auth/social/<str:provider>/", SocialLoginJWTView.as_view())  # wire as in §6 Step 4

# project/urls.py:40 — root
path("api/v1/users/", include("accounts.urls"))
path("accounts/social/signup/", lambda r: HttpResponse(..., status=404))  # :75 HTML stub

# project/settings/base.py:60 — apps
INSTALLED_APPS:  allauth, allauth.account, allauth.socialaccount (+ providers.google/facebook)
AUTHENTICATION_BACKENDS: ModelBackend + allauth.account.auth_backends.AuthenticationBackend
MIDDLEWARE: allauth.account.middleware.AccountMiddleware
SOCIALACCOUNT_* :258-274

# project/settings/unfold_config.py:277 — sidebar Users & Accounts → Social Apps/Accounts/Tokens
```

---

## 12. How to Adjust / Enhance

### Add a new provider (Apple / GitHub example)

```bash
pip install django-allauth==65.18.0  # already installed
```

```python
# project/settings/base.py:88 — add provider app
INSTALLED_APPS += ["allauth.socialaccount.providers.apple"]  # or providers.github

# project/settings/base.py:264 — add provider config (env, no hardcoding)
SOCIALACCOUNT_PROVIDERS["apple"] = {
    "APP": {"client_id": os.getenv("APPLE_CLIENT_ID"), "secret": os.getenv("APPLE_CLIENT_SECRET")},
    "SCOPE": ["email", "name"],
}
# GitHub
SOCIALACCOUNT_PROVIDERS["github"] = {
    "APP": {"client_id": os.getenv("GITHUB_CLIENT_ID"), "secret": os.getenv("GITHUB_CLIENT_SECRET")},
    "SCOPE": ["user:email"],
}
```

```python
# accounts/auth/views.py:44 — register adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
PROVIDER_ADAPTERS["apple"] = AppleOAuth2Adapter
# GitHub: from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
```

Seed `SocialApp` for `apple`/`github` via admin `/admin/socialaccount/socialapp/add/` with `Sites=1`, then test `POST /api/v1/users/api/auth/social/apple/` same contract. Apple id_token uses same `aud==client_id` logic as Google — extend `_find_app_by_id_token_aud:314` to `if provider in ("google","apple"):` or add separate branch.

### Add custom JWT claims

```python
# accounts/serializers.py:41 — also patched in social view accounts/auth/views.py:505
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = getattr(user, "role", "")
        token["onboarding_completed"] = getattr(user, "onboarding_completed", False)
        return token

# + social view already does:
refresh["email"] = user.email; refresh["role"] = user.role  # accounts/auth/views.py:505
refresh["org_id"] = str(getattr(user, "org_id", ""))  # add here
```

Also extend immediate `AccessToken` diagnostic log `accounts/auth/views.py:508` if you validate `iss`/`aud` claims.

### PKCE — already implemented

Google requires `S256` (`code_challenge_method=S256` on authorize, `pkce_code_verifier` on exchange `accounts/auth/views.py:344`). Facebook ignores it. No extra code — frontend must generate `code_verifier` (43-128 chars) and send it with `code`. Backend's `_exchange_code:324` tries each `SocialApp` so multi-client PKCE works. To enforce PKCE, reject missing `code_verifier` for `provider=="google"` in `post:355`.

### Restrict by email domain

```python
# accounts/auth/adapters.py:40 — extend pre_social_login or add is_open_for_signup
ALLOWED_DOMAINS = set(os.getenv("OAUTH_ALLOWED_DOMAINS","").split(","))  # e.g. "example.com,acme.io"

def pre_social_login(self, request, sociallogin):
    # ... existing auto-link logic ...
    email = (sociallogin.account.extra_data or {}).get("email") or ""
    domain = email.split("@")[-1].lower()
    if ALLOWED_DOMAINS and domain not in ALLOWED_DOMAINS:
        from allauth.core.exceptions import ImmediateHttpResponse
        from django.http import HttpResponse
        raise ImmediateHttpResponse(HttpResponse("Domain not allowed", status=403))
```

Alternative: override `is_open_for_signup(self, request, sociallogin)` to `return False` for disallowed domains → forces `403 Login not permitted` path `accounts/auth/views.py:460`.

### Role mapping on social login

Never `if email == "admin@example.com": user.role="admin"` literal. Use DB/setting:

```python
# accounts/auth/views.py:491 — after user resolved
# Option A: DB-driven — check EmailAddress domain or an allow-list model
from django.conf import settings
admin_emails = set(os.getenv("OAUTH_ADMIN_EMAILS","").split(","))
if user.email.lower() in admin_emails and getattr(user,"role",None) != "admin":
    user.role = "admin"; user.save(update_fields=["role"])

# Option B: first-social-login default role from settings
if not getattr(user, "role", None):
    user.role = os.getenv("OAUTH_DEFAULT_ROLE", "customer"); user.save(update_fields=["role"])
```

Keep `create_role_permission("seller")` factory `common/permissions.py` — no `if user.role == "customer"` hard-wired.

### Add avatar / name sync

Already copies `picture` `accounts/auth/views.py:501-503`:

```python
extra_data = login.account.extra_data or {}
picture_url = extra_data.get("picture")
if picture_url and not getattr(user, "picture", None):
    user.picture = picture_url
```

Extend for `first_name`/`last_name`:

```python
if extra_data.get("given_name") and not user.first_name:
    user.first_name = extra_data["given_name"][:30]
if extra_data.get("family_name") and not user.last_name:
    user.last_name = extra_data["family_name"][:30]
```

### Rate-limit social login

```python
# accounts/auth/views.py:293
from common.throttles import AuthRateThrottle
class SocialLoginJWTView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthRateThrottle]  # → anon 30/m base.py:377
```

### Verify `aud` strictly + log

Already strict `accounts/auth/views.py:414-425` — logs `aud` vs `available` and returns `401`. To add `iss` check:

```python
# _decode_id_token_aud → also decode iss, assert iss in ("https://accounts.google.com","accounts.google.com")
```

---

## 13. Testing & Debugging

```python
# tests/test_social_auth.py — unit for adapter dedupe
def test_list_apps_dedupe(db, rf):
    from allauth.socialaccount.models import SocialApp
    from accounts.auth.adapters import SocialAccountAdapter
    from django.contrib.sites.models import Site
    site = Site.objects.get(id=1)
    app_db = SocialApp.objects.create(provider="google", name="G", client_id="CID", secret="S")
    app_db.sites.add(site)
    adapter = SocialAccountAdapter()
    request = rf.get("/")
    # settings SOCIALACCOUNT_PROVIDERS google APP client_id=CID also exists → dedupe returns 1
    apps = adapter.list_apps(request, provider="google")
    assert len([a for a in apps if a.client_id=="CID"]) == 1

# tests/test_social_auth.py — auto-link
def test_pre_social_login_links_by_email(db, rf, user_factory):
    user = user_factory(email="foo@example.com")
    # build SocialLogin with extra_data email=foo@example.com → pre_social_login should call _link
    # assert SocialAccount.objects.filter(user=user).exists()

# Integration — mock provider
def test_social_login_google_id_token(client, mocker):
    mocker.patch("accounts.auth.views.GoogleOAuth2Adapter.complete_login", return_value=MockLogin(user=user))
    mocker.patch("accounts.auth.views.complete_social_login", return_value=None)
    resp = client.post("/api/v1/users/api/auth/social/google/", {"id_token": fake_jwt_with_aud(CID)}, format="json")
    assert resp.status_code == 200 and "access" in resp.json()
```

**Logs to watch** `dashboard/live_logs.py:38` + `accounts/auth/views.py:409,417,509,541`:
- `Google ID token aud=... matched ...` — correct fan-out.
- `did not match any SocialApp ... Available: [...]` — provider console `client_id` vs DB mismatch → reseed.
- `JWT generated and immediately validated OK ... jti=...` / `JWT immediate validation FAILED ...` — `JWT_SECRET_KEY` drift / `ALGORITHM` mismatch.
- Live Logs terminal shows `401 amber No matching Google OAuth client` with `cause`.

**Common errors:**

| Symptom | Cause | Fix |
|---|---|---|
| `401 No matching Google OAuth client` | `id_token aud` not in `SocialApp` | Seed `SocialApp` with correct `client_id` per platform; build app with matching `google-services.json` |
| `401 Invalid or expired provider token` | `complete_login` failed (signature/expired token) | Fetch fresh `id_token` (1h expiry), check `allauth` provider `VERSION` |
| `403 Login not permitted` | `ImmediateHttpResponse` or `user.pk is None` (no verified email) | Request `email` scope; Facebook needs `email` permission; check `extra_data.email` |
| `redirect_uri mismatch` | code already consumed or URI not in provider console | Use `code` once, register exact `redirect_uri` (scheme+host+slash) in Google/Facebook console |
| `MultipleObjectsReturned on get_app` | same `client_id` in DB + settings | Keep `SocialAccountAdapter.list_apps` dedupe `:21` |

---

## 14. Removal — How to Remove This Feature

### OTP + Password Reset (keep JWT, drop verification)

1. **Models** `accounts/models.py:24` → delete `OTPRecord:24` + `PasswordResetToken:55` (leave `from django.db import models`). `makemigrations accounts --name remove_otp` + `migrate`.
2. **Helpers** `accounts/helpers.py:76` → remove `generate_otp:76`, `generate_password_reset_token:81`, `create_and_send_otp:86`, `validate_otp:116` (keep `validate_credentials:20` if you keep login).
3. **Serializers** `accounts/serializers.py:106` → remove `UserVerifyAccountSerializer:106`, `UserResetPasswordSerializer:122`, `UserEmailSerializer:141`.
4. **Views** `accounts/views.py:150` → remove `verify_account:150`, `send_verification_code:205`, `reset_password:252` (keep `register:108` but drop `create_and_send_otp` call).
5. **Admin** `accounts/admin.py:10` → remove `OTPRecordAdmin:10` + `PasswordResetTokenAdmin:20`.
6. **Tasks** `accounts/tasks.py:16` → remove `send_verification_email:16` (keep if reused elsewhere).
7. **Settings** no OTP-specific settings; `EMAIL_*` `base.py:286-292` only if you drop email entirely.
8. **URLs** `verify/` etc are viewset actions — vanish when views deleted.

### Social OAuth (drop Google/Facebook)

1. **Settings** `project/settings/base.py` → delete/comment: `INSTALLED_APPS` `allauth*` 6 lines `:88-92` (keep core `allauth` if you still use email verification — else remove all 3), `AUTHENTICATION_BACKENDS` allauth line `:105`, `SOCIALACCOUNT_*` block `:254-274`, keep `MIDDLEWARE` `AccountMiddleware :119` only if any `allauth` remains.
2. **Delete adapter** `accounts/auth/adapters.py:20` + `accounts/auth/__init__.py:1` + `accounts/auth/views.py:293` (+ `accounts/auth/serializers.py`).
3. **URLs** `project/urls.py:75` → remove `socialaccount_signup` 404 stub if fully removing allauth; `accounts/urls.py` social route.
4. **Admin** `project/settings/unfold_config.py:299` → remove `Social Apps/Accounts/Tokens` 3 items under *Users & Accounts*.
5. **Requirements** `requirements.txt:24` → delete `django-allauth==65.18.0` if no allauth at all.
6. **Env** `.env.example:71-79` → delete `GOOGLE_OAUTH_*` / `FACEBOOK_*`.
7. **DB** `python manage.py migrate` — leaves `socialaccount_*` tables; to drop: `python manage.py migrate socialaccount zero` then `migrate` or manually `DROP TABLE`.

### JWT Keep / Drop

- **Drop JWT entirely** (session auth): `project/settings/base.py` → delete `rest_framework_simplejwt` from `INSTALLED_APPS` `:85` + `token_blacklist`, `SIMPLE_JWT` dict `:390-411`, `REST_FRAMEWORK DEFAULT_AUTHENTICATION_CLASSES JWTAuthentication` `:357`, `accounts/serializers.py:15` + `accounts/views.py:37,53`, `project/urls.py` `token/verify/blacklist`, `common/helpers.py` `set_refresh_token_cookie:301 / clear_token_cookies:356 / get_refresh_token_from_cookie:371`.
- **Keep JWT but drop cookie** (header only): keep serializers/views but remove `set_refresh_token_cookie` calls in `accounts/views.py:48,69`.

After removal: `make check-format && make test && docker compose config > /dev/null`.

---

> **REUSE checklist:** before writing anything, check `common/` — `BaseViewSet` `common/views.py:40`, `BaseAdmin` `common/unfold_admin_bases.py`, `AuthRateThrottle` `common/throttles.py:16`, `AuditLog` `common/models.py:490`, `set_refresh_token_cookie` `common/helpers.py:301`. If missing, add there first.