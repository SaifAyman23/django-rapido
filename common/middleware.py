"""
Ultimate custom middleware for Django
Provides production-grade middleware with:
- Request/response logging
- Performance monitoring
- Security headers
- Error tracking
- CORS handling
"""

from typing import Callable, Optional, Dict, Any
from time import time
import logging
import json
import uuid

from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# ===========================
# Logging Middleware
# ===========================

class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all HTTP requests and responses"""

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Log incoming request"""
        # Generate request ID
        request.request_id = str(uuid.uuid4())
        request.request_start_time = time()

        # Log request
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
        """Log outgoing response"""
        duration = (time() - getattr(request, "request_start_time", time())) * 1000  # ms

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
                "duration_ms": duration,
                "user_id": request.user.id if request.user.is_authenticated else None,
            },
        )

        # Add request ID to response headers
        response["X-Request-ID"] = getattr(request, "request_id", "")

        return response

    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "")

        return ip


# ===========================
# Performance Middleware
# ===========================

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Monitor request/response performance"""

    SLOW_REQUEST_THRESHOLD = 1000  # 1 second in milliseconds

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Start performance timer"""
        request.start_time = time()
        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Monitor response time"""
        duration = (time() - getattr(request, "start_time", time())) * 1000  # ms

        # Log slow requests
        if duration > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"Slow request: {request.method} {request.path}",
                extra={
                    "duration_ms": duration,
                    "path": request.path,
                    "method": request.method,
                },
            )

        # Add performance headers
        response["X-Response-Time"] = f"{duration:.2f}ms"

        return response


# ===========================
# Security Middleware
# ===========================

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to responses"""

    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add security headers"""
        for header, value in self.SECURITY_HEADERS.items():
            if header not in response:
                response[header] = value

        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limit requests by IP or user"""

    RATE_LIMIT_WINDOW = 3600  # 1 hour
    RATE_LIMIT_REQUESTS = 1000

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Check rate limit"""
        # Get identifier
        if request.user.is_authenticated:
            identifier = f"rate_limit:{request.user.id}"
        else:
            ip = RequestLoggingMiddleware.get_client_ip(request)
            identifier = f"rate_limit:{ip}"

        # Get current count
        current_requests = cache.get(identifier, 0)

        if current_requests >= self.RATE_LIMIT_REQUESTS:
            logger.warning(
                f"Rate limit exceeded: {identifier}",
                extra={"identifier": identifier},
            )

            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "retry_after": self.RATE_LIMIT_WINDOW,
                },
                status=429,
            )

        # Increment counter
        cache.set(identifier, current_requests + 1, self.RATE_LIMIT_WINDOW)

        return None


# ===========================
# Audit Middleware
# ===========================

class AuditLoggingMiddleware(MiddlewareMixin):
    """Log user actions for audit trail"""

    AUDIT_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    SKIP_PATHS = ["/health/", "/metrics/", "/api/docs/"]

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Log state-changing requests"""
        if request.method not in self.AUDIT_METHODS:
            return None

        if any(request.path.startswith(path) for path in self.SKIP_PATHS):
            return None

        # Log audit event
        logger.info(
            f"Audit: {request.method} {request.path}",
            extra={
                "method": request.method,
                "path": request.path,
                "user_id": request.user.id if request.user.is_authenticated else None,
                "ip_address": RequestLoggingMiddleware.get_client_ip(request),
                "timestamp": timezone.now().isoformat(),
            },
        )

        return None


# ===========================
# Error Handling Middleware
# ===========================

class ErrorHandlingMiddleware(MiddlewareMixin):
    """Handle and log exceptions"""

    def process_exception(self, request: HttpRequest, exception: Exception) -> Optional[HttpResponse]:
        """Handle exceptions"""
        logger.error(
            f"Unhandled exception: {str(exception)}",
            exc_info=True,
            extra={
                "path": request.path,
                "method": request.method,
                "user_id": request.user.id if request.user.is_authenticated else None,
                "request_id": getattr(request, "request_id", ""),
            },
        )

        # Return error response
        return JsonResponse(
            {
                "error": "Internal server error",
                "request_id": getattr(request, "request_id", ""),
            },
            status=500,
        )


# ===========================
# API Version Middleware
# ===========================

class APIVersionHeaderMiddleware(MiddlewareMixin):
    """Add API version header to responses"""

    API_VERSION = "1.0.0"

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add API version header"""
        response["X-API-Version"] = self.API_VERSION
        return response


# ===========================
# Timezone Middleware
# ===========================

class TimezoneMiddleware(MiddlewareMixin):
    """Set timezone based on user preference"""

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Set timezone from header or user preference"""
        timezone_header = request.META.get("HTTP_X_TIMEZONE")

        if timezone_header:
            try:
                from django.utils.timezone import activate
                activate(timezone_header)
            except Exception:
                logger.warning(f"Invalid timezone: {timezone_header}")

        return None


# ===========================
# CORS Middleware
# ===========================

class CORSMiddleware(MiddlewareMixin):
    """Custom CORS handling"""

    ALLOWED_ORIGINS = getattr(settings, "CORS_ALLOWED_ORIGINS", [])

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add CORS headers"""
        origin = request.META.get("HTTP_ORIGIN")

        if origin in self.ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Max-Age"] = "3600"

        return response


# ===========================
# Request Enhancement Middleware
# ===========================

class RequestEnhancementMiddleware(MiddlewareMixin):
    """Enhance request with additional metadata"""

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Add custom attributes to request"""
        # Add IP address
        request.client_ip = RequestLoggingMiddleware.get_client_ip(request)

        # Add user agent
        request.user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Add timestamp
        request.received_at = timezone.now()

        # Add request body (for logging)
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                request.body_data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            request.body_data = {}

        return None


# ===========================
# Cache Control Middleware
# ===========================

class CacheControlMiddleware(MiddlewareMixin):
    """Add cache control headers"""

    CACHE_CONTROL_DEFAULT = "max-age=0, no-cache, no-store, must-revalidate"
    CACHE_TIMEOUT_API = 300  # 5 minutes

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add cache control headers"""
        if request.path.startswith("/api/"):
            # API responses
            if request.method == "GET":
                response["Cache-Control"] = f"max-age={self.CACHE_TIMEOUT_API}"
            else:
                response["Cache-Control"] = self.CACHE_CONTROL_DEFAULT
        else:
            # Default cache control
            response["Cache-Control"] = self.CACHE_CONTROL_DEFAULT

        return response