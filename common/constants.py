"""
Ultimate constants and enums
Provides production-grade constants with:
- Enum choices
- Status constants
- Error codes
- Configuration constants
"""

from typing import List, Tuple, Dict
from enum import Enum, IntEnum


# ===========================
# Status Enums
# ===========================

class StatusChoice(str, Enum):
    """Base status choice"""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        """Get choices for model field"""
        return [(item.value, item.name.title()) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        """Get all values"""
        return [item.value for item in cls]


class UserStatusChoice(str, Enum):
    """User account status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING = "pending"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class PaymentStatusChoice(str, Enum):
    """Payment status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]


class OrderStatusChoice(str, Enum):
    """Order status"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]


class SubscriptionStatusChoice(str, Enum):
    """Subscription status"""

    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]


# ===========================
# Priority Enums
# ===========================

class PriorityChoice(IntEnum):
    """Priority levels"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def choices(cls) -> List[Tuple[int, str]]:
        return [(item.value, item.name.title()) for item in cls]

    @classmethod
    def values(cls) -> List[int]:
        return [item.value for item in cls]


# ===========================
# Role Enums
# ===========================

class UserRoleChoice(str, Enum):
    """User roles"""

    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]


class PermissionChoice(str, Enum):
    """Permission types"""

    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    PUBLISH = "publish"
    ADMIN = "admin"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]


# ===========================
# Notification Enums
# ===========================

class NotificationTypeChoice(str, Enum):
    """Notification types"""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.replace("_", " ").title()) for item in cls]


class NotificationStatusChoice(str, Enum):
    """Notification status"""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    OPENED = "opened"
    CLICKED = "clicked"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]


# ===========================
# HTTP Status Enums
# ===========================

class HTTPStatusChoice(IntEnum):
    """HTTP Status codes"""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# ===========================
# Time Unit Constants
# ===========================

class TimeUnit(str, Enum):
    """Time units"""

    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]


# ===========================
# Configuration Constants
# ===========================

class CacheConfig:
    """Cache configuration"""

    TIMEOUT_SHORT = 60  # 1 minute
    TIMEOUT_MEDIUM = 300  # 5 minutes
    TIMEOUT_LONG = 3600  # 1 hour
    TIMEOUT_VERY_LONG = 86400  # 24 hours

    KEY_PREFIX = "app:"


class ValidationConfig:
    """Validation configuration"""

    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    USERNAME_MIN_LENGTH = 3
    USERNAME_MAX_LENGTH = 50
    EMAIL_MAX_LENGTH = 255
    PHONE_MIN_LENGTH = 10
    PHONE_MAX_LENGTH = 20
    NAME_MAX_LENGTH = 100

    SLUG_MAX_LENGTH = 255


class PaginationConfig:
    """Pagination configuration"""

    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1


class FileConfig:
    """File upload configuration"""

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB

    ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png", "gif", "webp"]
    ALLOWED_DOCUMENT_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "txt"]
    ALLOWED_VIDEO_TYPES = ["mp4", "avi", "mov", "mkv", "webm"]


class RateLimitConfig:
    """Rate limiting configuration"""

    DEFAULT_WINDOW = 3600  # 1 hour
    ANONYMOUS_REQUESTS = 100
    AUTHENTICATED_REQUESTS = 1000
    STAFF_REQUESTS = 10000


# ===========================
# Error Codes
# ===========================

class ErrorCode(str, Enum):
    """Standardized error codes"""

    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    NOT_FOUND = "not_found"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    INVALID_REQUEST = "invalid_request"
    INVALID_STATE = "invalid_state"
    OPERATION_NOT_ALLOWED = "operation_not_allowed"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    INTERNAL_ERROR = "internal_error"


# ===========================
# Message Templates
# ===========================

class MessageTemplate(str, Enum):
    """Standard message templates"""

    CREATED = "Successfully created"
    UPDATED = "Successfully updated"
    DELETED = "Successfully deleted"
    NOT_FOUND = "Not found"
    UNAUTHORIZED = "Unauthorized"
    PERMISSION_DENIED = "Permission denied"
    VALIDATION_FAILED = "Validation failed"
    OPERATION_FAILED = "Operation failed"
    SUCCESS = "Success"
    ERROR = "An error occurred"


# ===========================
# Default Values
# ===========================

class Defaults:
    """Default values"""

    PAGINATION_SIZE = 10
    CACHE_TIMEOUT = CacheConfig.TIMEOUT_MEDIUM
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0

    # Timestamps
    TIMEZONE = "UTC"
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    # Email
    FROM_EMAIL = "noreply@example.com"
    EMAIL_TIMEOUT = 30

    # JWT
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_MINUTES = 5
    JWT_REFRESH_EXPIRY_DAYS = 7

    # Celery
    CELERY_TIMEOUT = 1800  # 30 minutes
    CELERY_MAX_RETRIES = 3


# ===========================
# Feature Flags
# ===========================

class FeatureFlags:
    """Feature flag constants"""

    ENABLE_NOTIFICATIONS = True
    ENABLE_EMAIL = True
    ENABLE_SMS = False
    ENABLE_WEBHOOKS = True
    ENABLE_ANALYTICS = True
    ENABLE_AUDIT_LOG = True
    ENABLE_RATE_LIMITING = True
    ENABLE_CACHING = True


# ===========================
# Mapping Functions
# ===========================

def get_status_display(status: str, status_enum) -> str:
    """Get human-readable status display"""
    try:
        return status_enum[status.upper()].name.title()
    except KeyError:
        return status


def get_choice_label(value: str, choices: List[Tuple]) -> str:
    """Get label from choices"""
    for choice_value, label in choices:
        if choice_value == value:
            return label
    return value