# Django Custom Middleware Guide

**A comprehensive guide to implementing production-grade custom middleware**

---

## Table of Contents

1. [Overview](#overview)
2. [Middleware Basics](#middleware-basics)
3. [Request Logging Middleware](#request-logging-middleware)
4. [Performance Monitoring](#performance-monitoring)
5. [Security Middleware](#security-middleware)
6. [Rate Limiting](#rate-limiting)
7. [Audit Logging](#audit-logging)
8. [Error Handling](#error-handling)
9. [API Versioning](#api-versioning)
10. [Timezone Handling](#timezone-handling)
11. [CORS Middleware](#cors-middleware)
12. [Request Enhancement](#request-enhancement)
13. [Cache Control](#cache-control)
14. [Best Practices](#best-practices)
15. [Testing Middleware](#testing-middleware)

---

## Overview

Middleware is a framework of hooks into Django's request/response processing. It's a light, low-level plugin system for globally altering Django's input or output.

### What is Middleware?

Middleware sits between the web server and your Django views:

```
Request → Middleware → View → Middleware → Response
```

### When to Use Middleware

✅ **Use middleware for:**
- Cross-cutting concerns affecting all requests
- Request/response logging
- Security headers
- Authentication checks
- Performance monitoring
- Rate limiting

❌ **Don't use middleware for:**
- View-specific logic (use decorators)
- Business logic (use services)
- Model operations (use signals)

### Quick Start

```python
from django.utils.deprecation import MiddlewareMixin

class SimpleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """Called before view"""
        print(f"Request: {request.method} {request.path}")
        return None  # Continue processing
    
    def process_response(self, request, response):
        """Called after view"""
        print(f"Response: {response.status_code}")
        return response  # Must return response

# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'myapp.middleware.SimpleMiddleware',  # Add here
    # ... other middleware
]
```

---

## Middleware Basics

### Middleware Structure

```python
class MyMiddleware(MiddlewareMixin):
    """
    Middleware with all hook methods
    """
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Called on each request, before Django determines which view to execute.
        Return None to continue processing, or HttpResponse to short-circuit.
        """
        return None
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Called just before Django calls the view.
        Return None to continue, or HttpResponse to short-circuit.
        """
        return None
    
    def process_template_response(self, request, response):
        """
        Called after view if response has render() method.
        Must return response object.
        """
        return response
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Called on all responses before returning to browser.
        Must return HttpResponse object.
        """
        return response
    
    def process_exception(self, request: HttpRequest, exception: Exception) -> Optional[HttpResponse]:
        """
        Called when view raises an exception.
        Return None to let exception bubble up, or HttpResponse to handle it.
        """
        return None
```

### Execution Order

**Request Phase (top to bottom):**
```
1. process_request (first middleware first)
2. process_view (first middleware first)
3. View executes
```

**Response Phase (bottom to top):**
```
4. process_template_response (last middleware first)
5. process_response (last middleware first)
```

**Exception (bottom to top):**
```
process_exception (last middleware first)
```

### Example Flow

```python
MIDDLEWARE = [
    'middleware.FirstMiddleware',
    'middleware.SecondMiddleware',
]

# Request flow:
FirstMiddleware.process_request()
SecondMiddleware.process_request()
View executes
SecondMiddleware.process_response()
FirstMiddleware.process_response()
```

---

## Request Logging Middleware

### Basic Request Logging

```python
import logging
import uuid
from time import time
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all HTTP requests and responses"""
    
    def process_request(self, request: HttpRequest) -> None:
        """Log incoming request"""
        # Generate unique request ID
        request.request_id = str(uuid.uuid4())
        request.request_start_time = time()
        
        # Log request details
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
        # Calculate request duration
        duration = (time() - getattr(request, "request_start_time", time())) * 1000  # ms
        
        # Set log level based on status code
        log_level = logging.INFO
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        
        # Log response
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
        """Extract client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "")
        return ip
```

**What it does:**
- Generates unique request ID
- Logs request method, path, user
- Calculates request duration
- Logs response status code
- Adds X-Request-ID header

**Log Output:**

```
INFO: GET /api/articles/ {"request_id": "abc-123", "method": "GET", ...}
INFO: GET /api/articles/ 200 {"request_id": "abc-123", "duration_ms": 45.2, ...}
```

**Use Cases:**
- Debugging production issues
- Request tracing
- Performance analysis
- Security auditing

---

## Performance Monitoring

### Performance Monitoring Middleware

```python
from time import time
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse
import logging

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Monitor request/response performance"""
    
    SLOW_REQUEST_THRESHOLD = 1000  # 1 second in milliseconds
    
    def process_request(self, request: HttpRequest) -> None:
        """Start performance timer"""
        request.start_time = time()
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Monitor response time"""
        # Calculate duration
        duration = (time() - getattr(request, "start_time", time())) * 1000  # ms
        
        # Log slow requests
        if duration > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"Slow request: {request.method} {request.path}",
                extra={
                    "duration_ms": duration,
                    "path": request.path,
                    "method": request.method,
                    "user_id": request.user.id if request.user.is_authenticated else None,
                },
            )
        
        # Add performance header
        response["X-Response-Time"] = f"{duration:.2f}ms"
        
        return response
```

**What it does:**
- Tracks request execution time
- Warns on slow requests (>1s)
- Adds X-Response-Time header
- Helps identify performance bottlenecks

**Response Headers:**

```
X-Response-Time: 245.67ms
```

**Advanced Version with Metrics:**

```python
class AdvancedPerformanceMiddleware(MiddlewareMixin):
    """Performance monitoring with metrics"""
    
    def process_request(self, request):
        request.start_time = time()
        request.db_queries_start = len(connection.queries)
        return None
    
    def process_response(self, request, response):
        duration = (time() - getattr(request, "start_time", time())) * 1000
        
        # Count database queries
        db_queries = len(connection.queries) - getattr(request, "db_queries_start", 0)
        
        # Log detailed metrics
        logger.info(
            f"Performance: {request.path}",
            extra={
                "duration_ms": duration,
                "db_queries": db_queries,
                "path": request.path,
                "method": request.method,
            }
        )
        
        # Add headers
        response["X-Response-Time"] = f"{duration:.2f}ms"
        response["X-DB-Queries"] = str(db_queries)
        
        return response
```

**Use Cases:**
- Performance optimization
- Identifying slow endpoints
- Database query monitoring
- Production monitoring

---

## Security Middleware

### Security Headers Middleware

```python
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse


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
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add security headers"""
        for header, value in self.SECURITY_HEADERS.items():
            if header not in response:
                response[header] = value
        
        return response
```

**Security Headers Explained:**

| Header | Purpose | Value |
|--------|---------|-------|
| `X-Content-Type-Options` | Prevent MIME sniffing | `nosniff` |
| `X-Frame-Options` | Prevent clickjacking | `DENY` or `SAMEORIGIN` |
| `X-XSS-Protection` | Enable XSS filter | `1; mode=block` |
| `Strict-Transport-Security` | Enforce HTTPS | `max-age=31536000` |
| `Content-Security-Policy` | Control resource loading | `default-src 'self'` |
| `Referrer-Policy` | Control referrer info | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Control browser features | `geolocation=()` |

**Customizable Version:**

```python
class ConfigurableSecurityMiddleware(MiddlewareMixin):
    """Security headers with configuration"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": getattr(settings, "X_FRAME_OPTIONS", "DENY"),
            "X-XSS-Protection": "1; mode=block",
        }
        
        if getattr(settings, "ENABLE_HSTS", True):
            self.headers["Strict-Transport-Security"] = "max-age=31536000"
        
        if csp_policy := getattr(settings, "CSP_POLICY", None):
            self.headers["Content-Security-Policy"] = csp_policy
    
    def process_response(self, request, response):
        for header, value in self.headers.items():
            if header not in response:
                response[header] = value
        return response
```

**Use Cases:**
- Prevent XSS attacks
- Clickjacking protection
- HTTPS enforcement
- Browser security features

---

## Rate Limiting

### Rate Limit Middleware

```python
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limit requests by IP or user"""
    
    RATE_LIMIT_WINDOW = 3600  # 1 hour
    RATE_LIMIT_REQUESTS = 1000
    
    def process_request(self, request) -> Optional[HttpResponse]:
        """Check rate limit"""
        # Get identifier (user ID or IP)
        if request.user.is_authenticated:
            identifier = f"rate_limit:user:{request.user.id}"
        else:
            ip = self.get_client_ip(request)
            identifier = f"rate_limit:ip:{ip}"
        
        # Get current request count
        current_requests = cache.get(identifier, 0)
        
        # Check if limit exceeded
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
        cache.set(
            identifier,
            current_requests + 1,
            self.RATE_LIMIT_WINDOW
        )
        
        return None
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "")
        return ip
```

**Advanced Rate Limiting:**

```python
class TieredRateLimitMiddleware(MiddlewareMixin):
    """Rate limiting with user tiers"""
    
    RATE_LIMITS = {
        "anonymous": (100, 3600),      # 100 requests per hour
        "authenticated": (1000, 3600),  # 1000 requests per hour
        "staff": (10000, 3600),        # 10000 requests per hour
        "premium": (5000, 3600),       # 5000 requests per hour
    }
    
    def process_request(self, request):
        # Determine user tier
        tier = self.get_user_tier(request.user)
        limit, window = self.RATE_LIMITS[tier]
        
        # Check rate limit
        identifier = self.get_identifier(request)
        current = cache.get(identifier, 0)
        
        if current >= limit:
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "window": window,
                    "tier": tier,
                },
                status=429
            )
        
        cache.set(identifier, current + 1, window)
        return None
    
    def get_user_tier(self, user):
        """Determine user tier"""
        if not user.is_authenticated:
            return "anonymous"
        elif user.is_staff:
            return "staff"
        elif hasattr(user, "subscription") and user.subscription.is_premium:
            return "premium"
        else:
            return "authenticated"
    
    def get_identifier(self, request):
        """Get rate limit key"""
        if request.user.is_authenticated:
            return f"rate_limit:user:{request.user.id}"
        else:
            ip = self.get_client_ip(request)
            return f"rate_limit:ip:{ip}"
```

**Use Cases:**
- API protection
- DDoS mitigation
- Fair usage enforcement
- Resource protection

---

## Audit Logging

### Audit Logging Middleware

```python
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(MiddlewareMixin):
    """Log user actions for audit trail"""
    
    AUDIT_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    SKIP_PATHS = ["/health/", "/metrics/", "/api/docs/"]
    
    def process_request(self, request) -> None:
        """Log state-changing requests"""
        # Only log certain methods
        if request.method not in self.AUDIT_METHODS:
            return None
        
        # Skip certain paths
        if any(request.path.startswith(path) for path in self.SKIP_PATHS):
            return None
        
        # Log audit event
        logger.info(
            f"Audit: {request.method} {request.path}",
            extra={
                "method": request.method,
                "path": request.path,
                "user_id": request.user.id if request.user.is_authenticated else None,
                "username": request.user.username if request.user.is_authenticated else "anonymous",
                "ip_address": self.get_client_ip(request),
                "timestamp": timezone.now().isoformat(),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            },
        )
        
        return None
    
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "")
        return ip
```

**Database Audit Logging:**

```python
class DatabaseAuditMiddleware(MiddlewareMixin):
    """Store audit logs in database"""
    
    AUDIT_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    
    def process_request(self, request):
        if request.method not in self.AUDIT_METHODS:
            return None
        
        # Store in database
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=request.method,
            path=request.path,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            timestamp=timezone.now(),
        )
        
        return None
```

**Use Cases:**
- Compliance requirements
- Security investigations
- User activity tracking
- Change history

---

## Error Handling

### Error Handling Middleware

```python
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Handle and log exceptions"""
    
    def process_exception(self, request, exception) -> Optional[JsonResponse]:
        """Handle exceptions"""
        # Log the exception
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
                "message": str(exception) if settings.DEBUG else "An error occurred",
            },
            status=500,
        )
```

**Advanced Error Handler:**

```python
class AdvancedErrorMiddleware(MiddlewareMixin):
    """Enhanced error handling with different error types"""
    
    def process_exception(self, request, exception):
        # Determine error type and status
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
        
        # Log with appropriate level
        log_level = logging.ERROR if status >= 500 else logging.WARNING
        logger.log(
            log_level,
            f"{error_type}: {str(exception)}",
            exc_info=status >= 500,
            extra={
                "error_type": error_type,
                "status_code": status,
                "path": request.path,
                "method": request.method,
            }
        )
        
        # Return formatted error
        return JsonResponse(
            {
                "error": {
                    "type": error_type,
                    "message": str(exception) if settings.DEBUG else "An error occurred",
                    "status": status,
                },
                "request_id": getattr(request, "request_id", ""),
            },
            status=status
        )
```

**Use Cases:**
- Centralized error handling
- Error logging
- User-friendly error messages
- Error tracking integration

---

## API Versioning

### API Version Header Middleware

```python
from django.utils.deprecation import MiddlewareMixin


class APIVersionHeaderMiddleware(MiddlewareMixin):
    """Add API version header to responses"""
    
    API_VERSION = "1.0.0"
    
    def process_response(self, request, response):
        """Add API version header"""
        response["X-API-Version"] = self.API_VERSION
        return response
```

**Advanced Version Management:**

```python
class APIVersionMiddleware(MiddlewareMixin):
    """Handle API versioning with deprecation warnings"""
    
    CURRENT_VERSION = "2.0.0"
    SUPPORTED_VERSIONS = ["1.0.0", "1.5.0", "2.0.0"]
    DEPRECATED_VERSIONS = ["1.0.0"]
    
    def process_request(self, request):
        # Extract requested version from header or URL
        version = (
            request.META.get("HTTP_X_API_VERSION")
            or self.extract_version_from_url(request.path)
            or self.CURRENT_VERSION
        )
        
        # Validate version
        if version not in self.SUPPORTED_VERSIONS:
            return JsonResponse(
                {
                    "error": "Unsupported API version",
                    "requested": version,
                    "supported": self.SUPPORTED_VERSIONS,
                },
                status=400
            )
        
        # Store version on request
        request.api_version = version
        
        # Log if deprecated
        if version in self.DEPRECATED_VERSIONS:
            logger.warning(
                f"Deprecated API version used: {version}",
                extra={
                    "version": version,
                    "path": request.path,
                    "user_id": request.user.id if request.user.is_authenticated else None,
                }
            )
        
        return None
    
    def process_response(self, request, response):
        version = getattr(request, "api_version", self.CURRENT_VERSION)
        response["X-API-Version"] = version
        
        # Add deprecation warning
        if version in self.DEPRECATED_VERSIONS:
            response["X-API-Deprecated"] = "true"
            response["X-API-Sunset-Date"] = "2026-12-31"
        
        return response
    
    @staticmethod
    def extract_version_from_url(path):
        """Extract version from URL like /api/v1/..."""
        import re
        match = re.match(r'/api/v(\d+\.\d+\.\d+)/', path)
        return match.group(1) if match else None
```

**Use Cases:**
- API versioning
- Deprecation warnings
- Version tracking
- Breaking change management

---

## Timezone Handling

### Timezone Middleware

```python
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
import pytz
import logging

logger = logging.getLogger(__name__)


class TimezoneMiddleware(MiddlewareMixin):
    """Set timezone based on user preference or header"""
    
    def process_request(self, request):
        """Activate timezone for request"""
        # Try to get timezone from header
        tz_header = request.META.get("HTTP_X_TIMEZONE")
        
        # Or from authenticated user
        if not tz_header and request.user.is_authenticated:
            tz_header = getattr(request.user, "timezone", None)
        
        # Activate timezone if valid
        if tz_header:
            try:
                timezone.activate(pytz.timezone(tz_header))
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Invalid timezone: {tz_header}")
                timezone.deactivate()
        else:
            timezone.deactivate()
        
        return None
```

**User Preference Version:**

```python
class UserTimezoneMiddleware(MiddlewareMixin):
    """Set timezone from user profile"""
    
    DEFAULT_TIMEZONE = "UTC"
    
    def process_request(self, request):
        if request.user.is_authenticated:
            user_tz = getattr(request.user, "timezone", self.DEFAULT_TIMEZONE)
            try:
                timezone.activate(pytz.timezone(user_tz))
            except:
                timezone.activate(pytz.timezone(self.DEFAULT_TIMEZONE))
        else:
            timezone.activate(pytz.timezone(self.DEFAULT_TIMEZONE))
        
        return None
    
    def process_response(self, request, response):
        timezone.deactivate()
        return response
```

**Use Cases:**
- Multi-timezone applications
- User-specific time display
- International apps
- Timezone-aware scheduling

---

## CORS Middleware

### CORS Middleware

```python
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class CORSMiddleware(MiddlewareMixin):
    """Custom CORS handling"""
    
    ALLOWED_ORIGINS = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
    ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    ALLOWED_HEADERS = "Content-Type, Authorization, X-Requested-With"
    MAX_AGE = 3600
    
    def process_response(self, request, response):
        """Add CORS headers"""
        origin = request.META.get("HTTP_ORIGIN")
        
        # Check if origin is allowed
        if origin in self.ALLOWED_ORIGINS or "*" in self.ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = self.ALLOWED_METHODS
            response["Access-Control-Allow-Headers"] = self.ALLOWED_HEADERS
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Max-Age"] = str(self.MAX_AGE)
        
        return response
    
    def process_request(self, request):
        """Handle preflight OPTIONS requests"""
        if request.method == "OPTIONS":
            response = HttpResponse()
            origin = request.META.get("HTTP_ORIGIN")
            
            if origin in self.ALLOWED_ORIGINS:
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Methods"] = self.ALLOWED_METHODS
                response["Access-Control-Allow-Headers"] = self.ALLOWED_HEADERS
                response["Access-Control-Max-Age"] = str(self.MAX_AGE)
            
            return response
        
        return None
```

**Dynamic CORS:**

```python
class DynamicCORSMiddleware(MiddlewareMixin):
    """CORS with pattern matching"""
    
    def is_origin_allowed(self, origin):
        """Check if origin is allowed"""
        allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        
        # Exact match
        if origin in allowed_origins:
            return True
        
        # Pattern match (*.example.com)
        for pattern in allowed_origins:
            if pattern.startswith("*."):
                domain = pattern[2:]
                if origin.endswith(domain):
                    return True
        
        return False
    
    def process_response(self, request, response):
        origin = request.META.get("HTTP_ORIGIN")
        
        if origin and self.is_origin_allowed(origin):
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
        
        return response
```

**Use Cases:**
- Cross-origin API calls
- SPA frontends
- Mobile app APIs
- Third-party integrations

---

## Request Enhancement

### Request Enhancement Middleware

```python
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
import json


class RequestEnhancementMiddleware(MiddlewareMixin):
    """Add custom attributes to request object"""
    
    def process_request(self, request):
        """Enhance request with additional data"""
        # Add client IP
        request.client_ip = self.get_client_ip(request)
        
        # Add user agent
        request.user_agent = request.META.get("HTTP_USER_AGENT", "")
        
        # Add timestamp
        request.received_at = timezone.now()
        
        # Add device info
        request.is_mobile = self.is_mobile_device(request)
        request.is_tablet = self.is_tablet_device(request)
        
        # Parse request body for logging
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                request.body_data = json.loads(request.body) if request.body else {}
            except (json.JSONDecodeError, ValueError):
                request.body_data = {}
        
        return None
    
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
    
    @staticmethod
    def is_mobile_device(request):
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        mobile_keywords = ["mobile", "android", "iphone", "ipod"]
        return any(keyword in user_agent for keyword in mobile_keywords)
    
    @staticmethod
    def is_tablet_device(request):
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        tablet_keywords = ["tablet", "ipad"]
        return any(keyword in user_agent for keyword in tablet_keywords)
```

**Use Cases:**
- Request context enrichment
- Analytics
- Device-specific logic
- Debugging information

---

## Cache Control

### Cache Control Middleware

```python
from django.utils.deprecation import MiddlewareMixin


class CacheControlMiddleware(MiddlewareMixin):
    """Add appropriate cache control headers"""
    
    CACHE_CONTROL_DEFAULT = "max-age=0, no-cache, no-store, must-revalidate"
    CACHE_TIMEOUT_API = 300  # 5 minutes
    
    def process_response(self, request, response):
        """Add cache control headers"""
        # API endpoints
        if request.path.startswith("/api/"):
            if request.method == "GET":
                # Cache GET requests
                response["Cache-Control"] = f"max-age={self.CACHE_TIMEOUT_API}"
            else:
                # Don't cache mutations
                response["Cache-Control"] = self.CACHE_CONTROL_DEFAULT
        
        # Static files (handled by web server usually)
        elif request.path.startswith("/static/"):
            response["Cache-Control"] = "max-age=31536000, immutable"
        
        # Default: no cache
        else:
            response["Cache-Control"] = self.CACHE_CONTROL_DEFAULT
        
        return response
```

**Advanced Cache Strategy:**

```python
class SmartCacheMiddleware(MiddlewareMixin):
    """Intelligent cache control based on content type"""
    
    CACHE_RULES = {
        # Path patterns and their cache settings
        r"^/api/public/": ("max-age=3600", True),  # 1 hour
        r"^/api/user/": ("max-age=300", True),     # 5 minutes
        r"^/api/private/": ("no-cache", False),    # No cache
        r"^/static/": ("max-age=31536000", True),  # 1 year
    }
    
    def process_response(self, request, response):
        import re
        
        # Find matching rule
        for pattern, (cache_control, cacheable) in self.CACHE_RULES.items():
            if re.match(pattern, request.path):
                if cacheable and request.method == "GET":
                    response["Cache-Control"] = cache_control
                else:
                    response["Cache-Control"] = "no-cache, no-store"
                break
        else:
            # Default: no cache
            response["Cache-Control"] = "no-cache, no-store"
        
        return response
```

**Use Cases:**
- Performance optimization
- CDN integration
- API caching
- Browser caching

---

## Best Practices

### 1. Keep Middleware Lightweight

✅ **Good:**

```python
class LightweightMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.timestamp = timezone.now()
        return None
```

❌ **Bad:**

```python
class HeavyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Complex database queries
        user_data = User.objects.select_related(...).prefetch_related(...)
        request.heavy_data = expensive_computation(user_data)
        return None
```

### 2. Handle Errors Gracefully

✅ **Good:**

```python
class SafeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            request.client_ip = self.get_client_ip(request)
        except Exception as e:
            logger.error(f"Error in middleware: {e}")
            request.client_ip = "unknown"
        return None
```

❌ **Bad:**

```python
class UnsafeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # No error handling - will break all requests if it fails
        request.client_ip = self.get_client_ip(request)
        return None
```

### 3. Order Matters

```python
MIDDLEWARE = [
    # Security first
    'django.middleware.security.SecurityMiddleware',
    
    # Session handling
    'django.contrib.sessions.middleware.SessionMiddleware',
    
    # CORS before authentication
    'myapp.middleware.CORSMiddleware',
    
    # Authentication
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # Request logging after auth (so we have user info)
    'myapp.middleware.RequestLoggingMiddleware',
    
    # Rate limiting after auth (user-based limits)
    'myapp.middleware.RateLimitMiddleware',
]
```

### 4. Return None to Continue Processing

```python
def process_request(self, request):
    # Do some work
    request.custom_attr = "value"
    
    # Return None to continue to next middleware/view
    return None  # Important!
```

### 5. Always Return Response in process_response

```python
def process_response(self, request, response):
    # Modify response
    response["X-Custom-Header"] = "value"
    
    # Must return response
    return response  # Required!
```

### 6. Use Middleware for Cross-Cutting Concerns Only

✅ **Use middleware for:**
- Logging (all requests)
- Security headers (all responses)
- Authentication checks
- Rate limiting

❌ **Don't use middleware for:**
- View-specific logic
- Business logic
- Data processing
- API endpoint logic

### 7. Cache Expensive Operations

```python
class OptimizedMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Cache expensive lookups
        cache_key = f"user_perms:{request.user.id}"
        permissions = cache.get(cache_key)
        
        if permissions is None:
            permissions = self.get_user_permissions(request.user)
            cache.set(cache_key, permissions, 300)
        
        request.user_permissions = permissions
        return None
```

### 8. Log Appropriately

```python
class LoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Info for normal operations
        logger.info(f"Request: {request.path}")
        return None
    
    def process_response(self, request, response):
        # Warning for 4xx errors
        if 400 <= response.status_code < 500:
            logger.warning(f"Client error: {response.status_code}")
        
        # Error for 5xx errors
        elif response.status_code >= 500:
            logger.error(f"Server error: {response.status_code}")
        
        return response
```

---

## Testing Middleware

### Unit Testing

```python
from django.test import TestCase, RequestFactory
from myapp.middleware import RequestLoggingMiddleware


class MiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RequestLoggingMiddleware(lambda x: HttpResponse())
    
    def test_request_id_added(self):
        """Test that request ID is added"""
        request = self.factory.get('/')
        self.middleware.process_request(request)
        
        self.assertTrue(hasattr(request, 'request_id'))
        self.assertIsInstance(request.request_id, str)
    
    def test_response_header_added(self):
        """Test that response header is added"""
        request = self.factory.get('/')
        request.request_id = "test-123"
        response = HttpResponse()
        
        response = self.middleware.process_response(request, response)
        
        self.assertEqual(response['X-Request-ID'], "test-123")
```

### Integration Testing

```python
class MiddlewareIntegrationTest(TestCase):
    def test_middleware_with_view(self):
        """Test middleware with actual view"""
        response = self.client.get('/api/articles/')
        
        # Check middleware added headers
        self.assertIn('X-Request-ID', response)
        self.assertIn('X-Response-Time', response)
```

### Performance Testing

```python
import time

class PerformanceTest(TestCase):
    def test_middleware_performance(self):
        """Ensure middleware doesn't slow requests significantly"""
        start = time.time()
        
        for _ in range(100):
            self.client.get('/api/articles/')
        
        duration = time.time() - start
        avg_time = duration / 100
        
        # Middleware should add <10ms per request
        self.assertLess(avg_time, 0.01)
```

---

## Summary

| Middleware | Purpose | Use Case |
|------------|---------|----------|
| **RequestLogging** | Log all requests/responses | Debugging, monitoring |
| **Performance** | Track response times | Optimization, alerting |
| **Security** | Add security headers | XSS, clickjacking protection |
| **RateLimit** | Throttle requests | API protection, DDoS |
| **AuditLogging** | Track user actions | Compliance, security |
| **ErrorHandling** | Catch exceptions | Error tracking, user feedback |
| **APIVersion** | Version management | API evolution |
| **Timezone** | User timezone support | International apps |
| **CORS** | Cross-origin requests | SPA, mobile APIs |
| **RequestEnhancement** | Add request metadata | Context, analytics |
| **CacheControl** | HTTP caching | Performance |

---

## Next Steps

1. Identify cross-cutting concerns in your app
2. Create appropriate middleware
3. Test thoroughly
4. Order middleware correctly in settings
5. Monitor performance impact
6. Document middleware behavior

---

**Key Takeaways:**

- Use middleware for cross-cutting concerns
- Keep middleware lightweight
- Handle errors gracefully
- Order matters
- Always return `None` or `HttpResponse`
- Test middleware thoroughly
- Log appropriately
- Cache expensive operations