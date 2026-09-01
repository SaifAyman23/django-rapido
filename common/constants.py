"""Application-wide enumerations and configuration constants.

Provides reusable choice enums and config containers for status, roles,
pagination, file limits, and feature flags.
"""

from enum import Enum, IntEnum
from typing import List, Tuple

from django.db import models
from django.utils.translation import gettext_lazy as _


class StatusChoice(str, Enum):
    """Base status choice."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        """Get choices for Django model field."""
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        """Get all valid values."""
        return [item.value for item in cls]


class UserStatusChoice(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING = "pending"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class PaymentStatusChoice(str, Enum):
    """Payment status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class OrderStatusChoice(str, Enum):
    """Order fulfillment status.

    Workflow:
        PENDING -> CONFIRMED -> PROCESSING -> SHIPPED -> DELIVERED
    Can cancel from: PENDING, CONFIRMED, PROCESSING
    Can return from: DELIVERED
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class SubscriptionStatusChoice(str, Enum):
    """Subscription lifecycle status."""

    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class PriorityChoice(IntEnum):
    """Priority levels."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def choices(cls) -> List[Tuple[int, str]]:
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[int]:
        return [item.value for item in cls]


class UserRoleChoice(str, Enum):
    """User roles."""

    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class PermissionChoice(str, Enum):
    """Granular permission types."""

    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    PUBLISH = "publish"
    ADMIN = "admin"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class NotificationTypeChoice(str, Enum):
    """Notification delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.replace("_", " ").title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class NotificationStatusChoice(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    OPENED = "opened"
    CLICKED = "clicked"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class HTTPStatusChoice(IntEnum):
    """HTTP response status codes."""

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

    @classmethod
    def choices(cls) -> List[Tuple[int, str]]:
        return [(item.value, _(item.name.replace("_", " ").title())) for item in cls]

    @classmethod
    def values(cls) -> List[int]:
        return [item.value for item in cls]


class TimeUnit(str, Enum):
    """Time duration units."""

    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class CacheConfig:
    """Cache timeout configurations."""

    TIMEOUT_SHORT = 60
    TIMEOUT_MEDIUM = 300
    TIMEOUT_LONG = 3600
    TIMEOUT_VERY_LONG = 86400
    KEY_PREFIX = "app:"


class ValidationConfig:
    """Input validation rules."""

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
    """Pagination settings."""

    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1


class FileConfig:
    """File upload settings."""

    MAX_FILE_SIZE = 5 * 1024 * 1024
    MAX_IMAGE_SIZE = 2 * 1024 * 1024
    MAX_VIDEO_SIZE = 100 * 1024 * 1024
    ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png", "gif", "webp"]
    ALLOWED_DOCUMENT_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "txt"]
    ALLOWED_VIDEO_TYPES = ["mp4", "avi", "mov", "mkv", "webm"]


class RateLimitConfig:
    """Rate limiting settings."""

    DEFAULT_WINDOW = 3600
    ANONYMOUS_REQUESTS = 100
    AUTHENTICATED_REQUESTS = 1000
    STAFF_REQUESTS = 10000


class ErrorCode(str, Enum):
    """Standardized error codes."""

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

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.replace("_", " ").title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class MessageTemplate(str, Enum):
    """Standard user-facing messages."""

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

    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, _(item.name.replace("_", " ").title())) for item in cls]

    @classmethod
    def values(cls) -> List[str]:
        return [item.value for item in cls]


class Defaults:
    """Application-wide default values."""

    PAGINATION_SIZE = 10
    CACHE_TIMEOUT = CacheConfig.TIMEOUT_MEDIUM
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0
    TIMEZONE = "UTC"
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    FROM_EMAIL = "noreply@example.com"
    EMAIL_TIMEOUT = 30
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_MINUTES = 5
    JWT_REFRESH_EXPIRY_DAYS = 7
    CELERY_TIMEOUT = 1800
    CELERY_MAX_RETRIES = 3


class FeatureFlags:
    """Feature flag constants."""

    ENABLE_NOTIFICATIONS = True
    ENABLE_EMAIL = True
    ENABLE_SMS = False
    ENABLE_WEBHOOKS = True
    ENABLE_ANALYTICS = True
    ENABLE_AUDIT_LOG = True
    ENABLE_RATE_LIMITING = True
    ENABLE_CACHING = True
