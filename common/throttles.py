"""Rate-limit classes shared across apps.

REUSE: AuthRateThrottle is used on public auth endpoints (register, OTP,
password-reset) to prevent brute-force/email-spam. It is keyed by IP
because the caller is unauthenticated. Wire via:

    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth"] = "30/minute"
    view.throttle_classes = [AuthRateThrottle]

From ras-elbar-go/backend/common/throttles.py
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
