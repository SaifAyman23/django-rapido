"""Rate-limit classes shared across apps.

REUSE: AuthRateThrottle is used on public auth endpoints (register, OTP,
password-reset) to prevent brute-force/email-spam. It is keyed by IP
because the caller is unauthenticated. Wire via:

    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth"] = "30/minute"
    view.throttle_classes = [AuthRateThrottle]

Django Rapido — reusable throttles.
"""

from rest_framework.throttling import SimpleRateThrottle


class AuthRateThrottle(SimpleRateThrottle):
    """
    IP-based rate limit for public authentication endpoints.

    Uses the "auth" scope from DEFAULT_THROTTLE_RATES.
    """

    scope = "auth"

    def get_cache_key(self, request, view):
        """Key throttling by client IP (no authentication required)."""
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class OTPThrottle(SimpleRateThrottle):
    """Per-identity limit for OTP issue/resend (email, falling back to IP)."""

    scope = "otp"

    def get_cache_key(self, request, view):
        ident = ""
        data = getattr(request, "data", None)
        if isinstance(data, dict):
            ident = (data.get("email") or "").strip().lower()
        if not ident:
            user = getattr(request, "user", None)
            ident = getattr(user, "email", "") if user and getattr(user, "is_authenticated", False) else ""
        if not ident:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AccountLinkThrottle(SimpleRateThrottle):
    """Per-user limit for add-account attempts."""

    scope = "account_link"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(user.pk)}