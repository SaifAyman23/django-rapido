"""
REUSE: Common middleware — all 13 classes are project-agnostic.

Enable selectively in settings/base.py MIDDLEWARE.
Active by default: RequestLogging + PerformanceMonitoring + SecurityHeaders + RequestEnhancement.
Opt-in: RateLimit, AuditLogging, ErrorHandling, APIVersion, Timezone, CORSMiddleware, CacheControl.
See guides/common/Middleware guide.md + docs/examples/state_machine.md.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, Optional

import pytz
from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from common.models import AuditLog

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all HTTP requests and responses with unique request ID and timing"""

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> None:
        """Generate request ID, record start time, log incoming request"""
        request.request_id = str(uuid.uuid4())
        request.request_start_time = time.time()

        logger.info(
            f"{request.method} {request.path}",
            extra={
                "request_id": request.request_id,
                "method": request.method,
                "path": request.path,
                "user_id": request.user.id if request.user.is_authenticated else None,
                "ip_address": self.get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:100],
            },
        )

        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Calculate duration, log response, add X-Request-ID header"""
        duration = (time.time() - getattr(request, "request_start_time", time.time())) * 1000

        log_level = logging.INFO
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING

        logger.log(
            log_level,
            f"{request.method} {request.path} {response.status_code}",
            extra={
                "request_id": getattr(request, "request_id", ""),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
                "user_id": request.user.id if request.user.is_authenticated else None,
            },
        )

        response["X-Request-ID"] = getattr(request, "request_id", "")

        return response

    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Extract client IP from X-Forwarded-For or REMOTE_ADDR"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Monitor request/response performance with DB query counting and slow-request warnings"""

    SLOW_REQUEST_THRESHOLD = 1000

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> None:
        """Start performance timer and record initial DB query count"""
        request.start_time = time.time()
        request.db_queries_start = len(connection.queries)
        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Calculate duration, count DB queries, log slow requests, add headers"""
        duration = (time.time() - getattr(request, "start_time", time.time())) * 1000
        db_queries = len(connection.queries) - getattr(request, "db_queries_start", 0)

        if duration > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"Slow request: {request.method} {request.path}",
                extra={
                    "duration_ms": round(duration, 2),
                    "db_queries": db_queries,
                    "path": request.path,
                    "method": request.method,
                    "user_id": request.user.id if request.user.is_authenticated else None,
                },
            )

        response["X-Response-Time"] = f"{duration:.2f}ms"
        response["X-DB-Queries"] = str(db_queries)

        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses"""

    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    def __init__(self, get_response):
        super().__init__(get_response)
        self.headers = dict(self.SECURITY_HEADERS)

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add security headers that are not already present"""
        for header, value in self.headers.items():
            if header not in response:
                response[header] = value
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Tiered rate limiting by IP or user using Redis cache"""

    RATE_LIMITS = {
        "anonymous": (100, 3600),
        "authenticated": (1000, 3600),
        "staff": (10000, 3600),
        "premium": (5000, 3600),
    }

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_view(
        self, request: HttpRequest, view_func: Any, view_args: Any, view_kwargs: Any
    ) -> Optional[HttpResponse]:
        """Check rate limit after authentication is available"""
        tier = self.get_user_tier(request.user)
        limit, window = self.RATE_LIMITS[tier]

        identifier = self.get_identifier(request)
        from django.core.cache import cache

        current_requests = cache.get(identifier, 0)

        if current_requests >= limit:
            logger.warning(
                f"Rate limit exceeded: {identifier}",
                extra={"identifier": identifier, "tier": tier, "limit": limit},
            )
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "window": window,
                    "tier": tier,
                    "retry_after": window,
                },
                status=429,
            )

        cache.set(identifier, current_requests + 1, window)
        return None

    def get_user_tier(self, user: Any) -> str:
        """Determine user tier for rate limiting"""
        if not user.is_authenticated:
            return "anonymous"
        if user.is_staff:
            return "staff"
        if hasattr(user, "subscription") and getattr(user.subscription, "is_premium", False):
            return "premium"
        return "authenticated"

    def get_identifier(self, request: HttpRequest) -> str:
        """Get rate limit cache key based on user ID or IP"""
        if request.user.is_authenticated:
            return f"rate_limit:user:{request.user.id}"
        return f"rate_limit:ip:{self.get_client_ip(request)}"

    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Extract client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class AuditLoggingMiddleware(MiddlewareMixin):
    """Log POST/PUT/PATCH/DELETE actions to database for audit trail"""

    AUDIT_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    SKIP_PATHS = ["/health/", "/metrics/", "/api/docs/"]

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> None:
        """Create audit log entry for state-changing requests"""
        if request.method not in self.AUDIT_METHODS:
            return None

        if any(request.path.startswith(path) for path in self.SKIP_PATHS):
            return None

        AuditLog.objects.create(
            action=request.method.lower(),
            object_repr=request.path,
            user=request.user if request.user.is_authenticated else None,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            timestamp=timezone.now(),
        )

        return None

    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Extract client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Catch unhandled exceptions and return JSON error responses"""

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> Optional[JsonResponse]:
        """Handle and log exceptions, return structured JSON error"""
        from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError

        if isinstance(exception, ValidationError):
            status = 400
            error_type = "validation_error"
        elif isinstance(exception, PermissionDenied):
            status = 403
            error_type = "permission_denied"
        elif isinstance(exception, ObjectDoesNotExist):
            status = 404
            error_type = "not_found"
        else:
            status = 500
            error_type = "internal_error"

        log_level = logging.ERROR if status >= 500 else logging.WARNING
        logger.log(
            log_level,
            f"{error_type}: {exception}",
            exc_info=status >= 500,
            extra={
                "error_type": error_type,
                "status_code": status,
                "path": request.path,
                "method": request.method,
                "request_id": getattr(request, "request_id", ""),
            },
        )

        return JsonResponse(
            {
                "error": {
                    "type": error_type,
                    "message": str(exception) if settings.DEBUG else "An error occurred",
                    "status": status,
                },
                "request_id": getattr(request, "request_id", ""),
            },
            status=status,
        )


class APIVersionHeaderMiddleware(MiddlewareMixin):
    """Add API version header to all responses"""

    API_VERSION = "1.0.0"

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add X-API-Version header"""
        response["X-API-Version"] = self.API_VERSION
        return response


class APIVersionMiddleware(MiddlewareMixin):
    """Handle API versioning with deprecation warnings"""

    CURRENT_VERSION = "2.0.0"
    SUPPORTED_VERSIONS = ["1.0.0", "1.5.0", "2.0.0"]
    DEPRECATED_VERSIONS = ["1.0.0"]
    SUNSET_DATE = "2026-12-31"

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Extract and validate requested API version"""
        version = (
            request.META.get("HTTP_X_API_VERSION")
            or self.extract_version_from_url(request.path)
            or self.CURRENT_VERSION
        )

        if version not in self.SUPPORTED_VERSIONS:
            return JsonResponse(
                {
                    "error": "Unsupported API version",
                    "requested": version,
                    "supported": self.SUPPORTED_VERSIONS,
                },
                status=400,
            )

        request.api_version = version

        if version in self.DEPRECATED_VERSIONS:
            logger.warning(
                f"Deprecated API version used: {version}",
                extra={
                    "version": version,
                    "path": request.path,
                    "user_id": request.user.id if request.user.is_authenticated else None,
                },
            )

        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add version header and deprecation warnings"""
        version = getattr(request, "api_version", self.CURRENT_VERSION)
        response["X-API-Version"] = version

        if version in self.DEPRECATED_VERSIONS:
            response["X-API-Deprecated"] = "true"
            response["X-API-Sunset-Date"] = self.SUNSET_DATE

        return response

    @staticmethod
    def extract_version_from_url(path: str) -> Optional[str]:
        """Extract API version from URL path like /api/v1.0.0/..."""
        match = re.match(r"/api/v(\d+\.\d+\.\d+)/", path)
        return match.group(1) if match else None


class TimezoneMiddleware(MiddlewareMixin):
    """Set timezone based on request header or user preference"""

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> None:
        """Activate timezone for the current request"""
        tz_header = request.META.get("HTTP_X_TIMEZONE")

        if not tz_header and request.user.is_authenticated:
            tz_header = getattr(request.user, "timezone", None)

        if tz_header:
            try:
                timezone.activate(pytz.timezone(tz_header))
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Invalid timezone: {tz_header}")
                timezone.deactivate()
        else:
            timezone.deactivate()

        return None


class UserTimezoneMiddleware(MiddlewareMixin):
    """Set timezone from authenticated user profile"""

    DEFAULT_TIMEZONE = "UTC"

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> None:
        """Activate user's preferred timezone"""
        if request.user.is_authenticated:
            user_tz = getattr(request.user, "timezone", self.DEFAULT_TIMEZONE)
            try:
                timezone.activate(pytz.timezone(user_tz))
            except Exception:
                timezone.activate(pytz.timezone(self.DEFAULT_TIMEZONE))
        else:
            timezone.activate(pytz.timezone(self.DEFAULT_TIMEZONE))

        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Deactivate custom timezone after request completes"""
        timezone.deactivate()
        return response


class CORSMiddleware(MiddlewareMixin):
    """Custom CORS handling with origin allowlist"""

    ALLOWED_ORIGINS = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
    ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    ALLOWED_HEADERS = "Content-Type, Authorization, X-Requested-With"
    MAX_AGE = 3600

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Handle preflight OPTIONS requests"""
        if request.method == "OPTIONS":
            response = HttpResponse()
            origin = request.META.get("HTTP_ORIGIN")

            if origin in self.ALLOWED_ORIGINS or "*" in self.ALLOWED_ORIGINS:
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Methods"] = self.ALLOWED_METHODS
                response["Access-Control-Allow-Headers"] = self.ALLOWED_HEADERS
                response["Access-Control-Max-Age"] = str(self.MAX_AGE)

            return response

        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add CORS headers to all responses"""
        origin = request.META.get("HTTP_ORIGIN")

        if origin in self.ALLOWED_ORIGINS or "*" in self.ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = self.ALLOWED_METHODS
            response["Access-Control-Allow-Headers"] = self.ALLOWED_HEADERS
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Max-Age"] = str(self.MAX_AGE)

        return response


class DynamicCORSMiddleware(MiddlewareMixin):
    """CORS with pattern matching support for wildcard subdomains"""

    def __init__(self, get_response):
        super().__init__(get_response)

    @staticmethod
    def is_origin_allowed(origin: str) -> bool:
        """Check if origin matches allowed origins with wildcard support"""
        allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])

        if origin in allowed_origins:
            return True

        for pattern in allowed_origins:
            if pattern.startswith("*."):
                domain = pattern[2:]
                if origin.endswith(domain):
                    return True

        return False

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add CORS headers with dynamic origin validation"""
        origin = request.META.get("HTTP_ORIGIN")

        if origin and self.is_origin_allowed(origin):
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"

        return response


class RequestEnhancementMiddleware(MiddlewareMixin):
    """Add custom attributes to request object for downstream use"""

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> None:
        """Enhance request with client IP, user agent, timestamp, device info, and body data"""
        request.client_ip = self.get_client_ip(request)
        request.user_agent = request.META.get("HTTP_USER_AGENT", "")
        request.received_at = timezone.now()
        request.is_mobile = self.is_mobile_device(request)
        request.is_tablet = self.is_tablet_device(request)

        if request.method in ("POST", "PUT", "PATCH"):
            try:
                request.body_data = json.loads(request.body) if request.body else {}
            except (json.JSONDecodeError, ValueError):
                request.body_data = {}

        return None

    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Extract client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @staticmethod
    def is_mobile_device(request: HttpRequest) -> bool:
        """Detect mobile device from user agent"""
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        mobile_keywords = ["mobile", "android", "iphone", "ipod"]
        return any(keyword in user_agent for keyword in mobile_keywords)

    @staticmethod
    def is_tablet_device(request: HttpRequest) -> bool:
        """Detect tablet device from user agent"""
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        tablet_keywords = ["tablet", "ipad"]
        return any(keyword in user_agent for keyword in tablet_keywords)


class CacheControlMiddleware(MiddlewareMixin):
    """Add cache control headers based on URL path prefix"""

    CACHE_CONTROL_DEFAULT = "max-age=0, no-cache, no-store, must-revalidate"
    CACHE_TIMEOUT_API = 300

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Set Cache-Control header based on request path"""
        if request.path.startswith("/api/"):
            if request.method == "GET":
                response["Cache-Control"] = f"max-age={self.CACHE_TIMEOUT_API}"
            else:
                response["Cache-Control"] = self.CACHE_CONTROL_DEFAULT
        elif request.path.startswith("/static/"):
            response["Cache-Control"] = "max-age=31536000, immutable"
        else:
            response["Cache-Control"] = self.CACHE_CONTROL_DEFAULT

        return response


class SmartCacheMiddleware(MiddlewareMixin):
    """Intelligent cache control based on regex path patterns"""

    CACHE_RULES = {
        r"^/api/public/": ("max-age=3600", True),
        r"^/api/user/": ("max-age=300", True),
        r"^/api/private/": ("no-cache", False),
        r"^/static/": ("max-age=31536000", True),
    }

    def __init__(self, get_response):
        super().__init__(get_response)

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Apply cache control header matching the first applicable rule"""
        for pattern, (cache_control, cacheable) in self.CACHE_RULES.items():
            if re.match(pattern, request.path):
                if cacheable and request.method == "GET":
                    response["Cache-Control"] = cache_control
                else:
                    response["Cache-Control"] = "no-cache, no-store"
                break
        else:
            response["Cache-Control"] = "no-cache, no-store"

        return response
