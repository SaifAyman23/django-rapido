# Authentication Guide — OTP + JWT + Social (REUSE)

## Overview

Generic auth engine from ras-elbar-go — project-agnostic, no deliveryman logic.

```
Register (email+password) → OTP email (6 digits, 10m, 5 attempts) → Verify → JWT (refresh HttpOnly cookie + access body)
                                                            ↘ Password reset (OTP → token 15m → reset)
Social login (Google/Facebook) → auto-link by email → JWT
```

## Models (accounts/models.py)

```python
class OTPRecord(TimestampedModel, UUIDModel):
    class OTPType(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email Verification"
        PASSWORD_RESET = "password_reset", "Password Reset"
    user = FK(User)
    otp = CharField(6)
    expires_at = DateTimeField
    type = CharField(choices=OTPType)
    attempts = IntegerField(default=0)  # F() guard
    is_used = BooleanField(default=False)

class PasswordResetToken(TimestampedModel, UUIDModel):
    user = FK(User)
    token = CharField(256, unique=True)  # secrets.token_urlsafe(32) → 43 chars
    expires_at = DateTimeField
    is_used = BooleanField(default=False)
    attempts = IntegerField(default=0)
```

Indexes: `Index(otp, type, expires_at)` + `Index(user, type)`.

## Helpers (accounts/helpers.py)

```python
generate_otp() -> str  # random 100000-999999
generate_password_reset_token() -> str  # token_urlsafe(32)
create_and_send_otp(user, otp_type="email_verification", expiry_minutes=10) -> OTPRecord
    # REUSE: swap send_verification_email() → .delay() for Celery
validate_otp(code, purpose="email_verification", max_attempts=5) -> OTPRecord
    # Filters is_used=False, expires_at__gte=now(), increments attempts via F()
validate_credentials(email, password) -> User
    # Checks empty, check_password, SUSPENDED, is_banned, optional UNVERIFIED gate
    # REUSE: wrap with role check if needed: if user.role != "admin": raise ...
```

## Serializers

- `CustomTokenObtainPairSerializer` — `username_field` lax CharField, calls `validate_credentials`, adds `token["email"]` claim (add `role` if needed)
- `UserRegistrationSerializer` — handles social-only reuse (`has_usable_password()`), username collision loop
- `UserVerifyAccountSerializer` — `code` 6 chars → `validate_otp` → `otp_record`
- `UserResetPasswordSerializer` — `token` + `password` matching
- `UserEmailSerializer` — `email` + `type` (validates OTPType.values)

## Views (accounts/views.py)

- `CustomTokenObtainPairView` — sets `refresh_token` HttpOnly `Lax` via `set_refresh_token_cookie(response, token)`
- `CookieTokenRefreshView` — `refresh = data["refresh"] or COOKIE["refresh_token"]` (body wins), rotates cookie
- `UserViewSet`:
  - `register POST AllowAny + AuthRateThrottle @transaction.atomic` → `transaction.on_commit(lambda: create_and_send_otp(user))`
  - `verify_account POST verify?` — `EMAIL_VERIFICATION`: sets `is_verified/active/verified_at`, returns `refresh+access`; `PASSWORD_RESET`: returns `PasswordResetToken`
  - `send_verification_code POST AllowAny` — anti-enumeration (always 200 even if email not found), creates 10m OTP, `on_commit delay`
  - `reset_password POST AllowAny` — `select_for_update` token, checks `attempts<5`, `set_password`, marks `is_used`
  - `me GET/PATCH`, `logout POST` (blacklist + clear cookies)

## Social Login (accounts/auth/adapters.py) — REUSE

```python
# settings/base.py
SOCIALACCOUNT_ADAPTER = "accounts.auth.adapters.SocialAccountAdapter"
SOCIALACCOUNT_PROVIDERS = {
    "google": {"SCOPE": ["openid","profile","email"], "APP": {"client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID")}},
    "facebook": {"SCOPE": ["email","public_profile"], "VERSION": "v21.0", ...}
}
```

`SocialAccountAdapter`:
- `list_apps()` dedupes DB + settings `APP` blocks → prevents `MultipleObjectsReturned` (DB wins)
- `pre_social_login()` auto-links by email via `EmailAddress` or `CustomUser.email` → prevents UNIQUE violation

Enable providers by uncommenting in `base.py` + `INSTALLED_APPS` (`allauth.socialaccount.providers.google`).

## Throttling & Security

- `AuthRateThrottle` (`scope=auth`) on register/verify/send/reset — `anon 30/m` IP-based
- `BaseViewSetMixin._scrub_request_data` masks `password/code/otp/secret/token` before `LOG_REQUESTS` debug
- `transaction.atomic + select_for_update` on OTP/token mutation
- Anti-enumeration on `send_verification_code` always `200`

## Environment

```bash
# .env.example
# GOOGLE_OAUTH_CLIENT_ID=
# GOOGLE_OAUTH_CLIENT_SECRET=
# FACEBOOK_OAUTH_CLIENT_ID=
# FACEBOOK_OAUTH_CLIENT_SECRET=
```

## Wiring

```python
# accounts/urls.py
router.register(r"users", UserViewSet)
path("login/", CustomTokenObtainPairView.as_view())
path("token/refresh/", CookieTokenRefreshView.as_view())
# REUSE: verify/ is action on viewset: POST /api/v1/users/users/verify/
```

See `docs/examples/state_machine.md` for transactional pattern reuse.

---

## Removal — How to Remove This Feature

> All steps are safe — no other app depends on accounts OTP (except optional `notifications` tasks). Deleting OTP still keeps basic JWT login.

### OTP + Password Reset (keep JWT, drop verification)

1. **Delete models** `accounts/models.py` → remove `OTPRecord` + `PasswordResetToken` (entire file → leave `from django.db import models`). Then `python manage.py makemigrations accounts --name remove_otp` + `migrate`.
2. **Delete helpers** `accounts/helpers.py` → remove `generate_otp`, `generate_password_reset_token`, `create_and_send_otp`, `validate_otp` (keep `validate_credentials` if you keep login).
3. **Delete serializers** `accounts/serializers.py` → remove `UserVerifyAccountSerializer`, `UserResetPasswordSerializer`, `UserEmailSerializer`.
4. **Delete views** `accounts/views.py` → remove `verify_account`, `send_verification_code`, `reset_password` actions (keep `register` but change it to not call `create_and_send_otp` — return `201` directly).
5. **Delete admin** `accounts/admin.py` → remove `OTPRecordAdmin` + `PasswordResetTokenAdmin` registrations.
6. **Delete tasks** `accounts/tasks.py` → remove `send_verification_email` (or keep if you reuse email elsewhere) + `accounts/notifications.py` `should_notify` import if it was only for OTP welcome.
7. **Settings** OTP uses `EMAIL_*` only: if you fully remove email, delete `EMAIL_*` block `base.py:277-284` (`EMAIL_HOST/PORT/USER/PASSWORD/USE_TLS/DEFAULT_FROM_EMAIL`). OTP itself adds no new settings, but `base.py:390 JWT_SECRET_KEY`/`392 JWT_ALGORITHM` (`JWT_*`) and `REST_FRAMEWORK throttles auth 30/m` (`base.py:369`) + `common/throttles.py AuthRateThrottle` / `common/mixins.py:444 SENSITIVE_LOG_KEYS` scrubbing `otp/token` remain for JWT.
8. **Env** If you drop email, delete `.env.example:53-54 JWT_SECRET_KEY/JWT_ALGORITHM` keep if JWT stays, and delete `EMAIL_*` 7 lines `57-63` (`EMAIL_BACKEND/HOST/PORT/USER/PASSWORD/USE_TLS/DEFAULT_FROM_EMAIL`). OTP enforces `common/helpers.py:301 set_refresh_token_cookie` still needed for JWT.
9. **Common** Keep `common/throttles.py:16 AuthRateThrottle` if you keep JWT login (it throttles `register/verify/reset`); delete only if you drop all auth throttling. `common/mixins.py:444` still scrubs `otp/token` — keep if any auth remains.
10. **URLs** nothing to remove — `verify/` etc are viewset actions, they vanish when views are deleted.

### Social OAuth (drop Google/Facebook)

1. **Settings `project/settings/base.py`** → delete/comment:
   - `INSTALLED_APPS` `allauth`, `allauth.account`, `allauth.socialaccount*` (6 lines `base.py:88-92`)
   - `AUTHENTICATION_BACKENDS` `allauth...` (if uncommented)
   - `SOCIALACCOUNT_*` block `base.py:250-266`
   - `MIDDLEWARE` `allauth.account.middleware.AccountMiddleware` `base.py:113`
2. **Delete adapter** `accounts/auth/adapters.py` + `accounts/auth/__init__.py` + `accounts/auth/` folder.
3. **URLs** `project/urls.py` → remove `socialaccount_signup` 404 stub `path('accounts/social/signup/', ...)`.
4. **Admin** `project/settings/unfold_config.py` → remove `Social Apps/Accounts/Tokens` items under `Users & Accounts` (3 items).
5. **Requirements** `requirements.txt:23` → delete `django-allauth==65.18.0`.
6. **Env** `.env.example:72-79` → delete `GOOGLE_OAUTH_*` / `FACEBOOK_*` commented lines.

### JWT Keep / Drop

- **To drop JWT entirely** (use session auth): `project/settings/base.py` → delete `rest_framework_simplejwt` from `INSTALLED_APPS` (`base.py:80` + `token_blacklist`), `SIMPLE_JWT` dict `base.py:382-403` (`ACCESS 30m/REFRESH 30d`), `REST_FRAMEWORK DEFAULT_AUTHENTICATION_CLASSES JWTAuthentication` (`base.py:349`), `REST_FRAMEWORK throttles auth 30/m` (`base.py:369`) + `common/throttles.py` if no auth throttling needed, `accounts/serializers.py CustomTokenObtainPairSerializer` + `accounts/views.py CustomTokenObtainPairView / CookieTokenRefreshView`, `project/urls.py token/refresh/verify/blacklist`, `common/helpers.py:301 set_refresh_token_cookie / 332 set_token_cookies / 356 clear_token_cookies / 371 get_refresh_token_from_cookie` (4 helpers), `common/mixins.py:444` still useful for password scrubbing but not JWT. Install `django.contrib.auth` session fallback. Env—delete `.env.example:53-54 JWT_SECRET_KEY/JWT_ALGORITHM` + keep `SECRET_KEY` base.
- **To keep JWT but drop cookie** (header only): keep serializers/views but remove `set_refresh_token_cookie` calls in `accounts/views.py` and `common/helpers.py` `set_refresh_token_cookie` (keep `clear_token_cookies` for logout). Env keep `JWT_*`.

After removal, run `make check-format && make test && docker compose config > /dev/null` to verify no import errors.
