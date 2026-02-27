# Django Constants & Enums Guide

**A comprehensive guide to implementing production-grade constants and enumerations**

---

## Table of Contents

1. [Overview](#overview)
2. [Why Use Enums](#why-use-enums)
3. [Status Enums](#status-enums)
4. [Priority & Rating Enums](#priority--rating-enums)
5. [Role & Permission Enums](#role--permission-enums)
6. [Notification Enums](#notification-enums)
7. [HTTP Status Enums](#http-status-enums)
8. [Time Unit Enums](#time-unit-enums)
9. [Configuration Constants](#configuration-constants)
10. [Error Codes](#error-codes)
11. [Message Templates](#message-templates)
12. [Default Values](#default-values)
13. [Feature Flags](#feature-flags)
14. [Best Practices](#best-practices)
15. [Usage Examples](#usage-examples)

---

## Overview

Constants and enums provide type-safe, maintainable configuration values for Django applications. They eliminate magic strings, reduce bugs, and improve code readability.

### Quick Start

```python
from enum import Enum

class StatusChoice(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    
    @classmethod
    def choices(cls):
        return [(item.value, item.name.title()) for item in cls]

# Usage in models
class Article(models.Model):
    status = models.CharField(
        max_length=20,
        choices=StatusChoice.choices(),
        default=StatusChoice.DRAFT.value
    )
```

### Benefits

- **Type Safety** — IDE autocomplete and type checking
- **Maintainability** — Change values in one place
- **Validation** — Prevent invalid values
- **Documentation** — Self-documenting code
- **DRY** — Don't repeat yourself

---

## Why Use Enums

### Problem: Magic Strings

❌ **Bad Approach:**

```python
# Scattered throughout codebase
article.status = "published"
if article.status == "publshed":  # Typo! Bug!
    send_notification()

# What are valid statuses? Nobody knows!
```

✅ **Good Approach:**

```python
# Centralized, type-safe
article.status = StatusChoice.PUBLISHED.value
if article.status == StatusChoice.PUBLISHED.value:
    send_notification()

# IDE autocompletes: DRAFT, PUBLISHED, ARCHIVED
# Typos caught immediately
```

### Advantages Over Constants

| Approach | Type Safety | IDE Support | Validation | Iteration |
|----------|-------------|-------------|------------|-----------|
| Strings | ❌ | ❌ | ❌ | ❌ |
| Constants | ⚠️ | ⚠️ | ❌ | ❌ |
| Enums | ✅ | ✅ | ✅ | ✅ |

---

## Status Enums

### StatusChoice (Base)

General-purpose status enum for any entity.

```python
class StatusChoice(str, Enum):
    """Base status choice"""
    
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DELETED = "deleted"
    
    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        """Get choices for Django model field"""
        return [(item.value, item.name.title()) for item in cls]
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all valid values"""
        return [item.value for item in cls]
```

**Returns:**

```python
StatusChoice.choices()
# [('draft', 'Draft'), ('published', 'Published'), 
#  ('archived', 'Archived'), ('deleted', 'Deleted')]

StatusChoice.values()
# ['draft', 'published', 'archived', 'deleted']
```

**Model Usage:**

```python
class Article(models.Model):
    status = models.CharField(
        max_length=20,
        choices=StatusChoice.choices(),
        default=StatusChoice.DRAFT.value
    )
```

**Business Logic:**

```python
# Check status
if article.status == StatusChoice.PUBLISHED.value:
    article.publish_date = timezone.now()

# Validate status
def can_edit(article):
    return article.status in [
        StatusChoice.DRAFT.value,
        StatusChoice.ARCHIVED.value
    ]

# Status transitions
def archive_article(article):
    if article.status == StatusChoice.PUBLISHED.value:
        article.status = StatusChoice.ARCHIVED.value
        article.save()
```

**Use Cases:**

- Blog posts
- Documents
- Content items
- Generic entities
- Workflow stages

### UserStatusChoice

User account status tracking.

```python
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
```

**Model Usage:**

```python
class User(AbstractUser):
    status = models.CharField(
        max_length=20,
        choices=UserStatusChoice.choices(),
        default=UserStatusChoice.PENDING.value
    )
```

**Business Logic:**

```python
# Permission checks
def can_login(user):
    return user.status == UserStatusChoice.ACTIVE.value

def is_restricted(user):
    return user.status in [
        UserStatusChoice.SUSPENDED.value,
        UserStatusChoice.BANNED.value
    ]

# Status changes
def activate_user(user):
    user.status = UserStatusChoice.ACTIVE.value
    user.save()
    send_welcome_email(user)

def suspend_user(user, reason):
    user.status = UserStatusChoice.SUSPENDED.value
    user.suspension_reason = reason
    user.save()
    notify_suspension(user, reason)
```

**Use Cases:**

- User account management
- Access control
- Moderation systems
- Onboarding flows

### PaymentStatusChoice

Payment transaction tracking.

```python
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
```

**Model Usage:**

```python
class Payment(models.Model):
    status = models.CharField(
        max_length=20,
        choices=PaymentStatusChoice.choices(),
        default=PaymentStatusChoice.PENDING.value
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
```

**Business Logic:**

```python
# Payment processing
def process_payment(payment):
    payment.status = PaymentStatusChoice.PROCESSING.value
    payment.save()
    
    try:
        charge_customer(payment)
        payment.status = PaymentStatusChoice.COMPLETED.value
    except PaymentError:
        payment.status = PaymentStatusChoice.FAILED.value
    
    payment.save()

# Query payments
completed_payments = Payment.objects.filter(
    status=PaymentStatusChoice.COMPLETED.value
)

# Refund logic
def refund_payment(payment):
    if payment.status == PaymentStatusChoice.COMPLETED.value:
        process_refund(payment)
        payment.status = PaymentStatusChoice.REFUNDED.value
        payment.save()
```

**Use Cases:**

- E-commerce
- Subscription billing
- Payment gateways
- Transaction tracking

### OrderStatusChoice

Order fulfillment tracking.

```python
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
```

**Workflow:**

```
PENDING → CONFIRMED → PROCESSING → SHIPPED → DELIVERED
   ↓                      ↓            ↓
CANCELLED            CANCELLED    RETURNED
```

**Business Logic:**

```python
# Order lifecycle
def confirm_order(order):
    if order.status == OrderStatusChoice.PENDING.value:
        order.status = OrderStatusChoice.CONFIRMED.value
        order.confirmed_at = timezone.now()
        order.save()
        send_confirmation_email(order)

def ship_order(order):
    if order.status == OrderStatusChoice.PROCESSING.value:
        order.status = OrderStatusChoice.SHIPPED.value
        order.shipped_at = timezone.now()
        order.save()
        send_tracking_email(order)

# Status validation
def can_cancel(order):
    return order.status in [
        OrderStatusChoice.PENDING.value,
        OrderStatusChoice.CONFIRMED.value,
        OrderStatusChoice.PROCESSING.value
    ]
```

**Use Cases:**

- E-commerce platforms
- Inventory management
- Fulfillment systems
- Order tracking

### SubscriptionStatusChoice

Subscription lifecycle management.

```python
class SubscriptionStatusChoice(str, Enum):
    """Subscription status"""
    
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    
    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]
```

**Business Logic:**

```python
# Subscription checks
def has_access(user):
    subscription = user.subscription
    return subscription.status == SubscriptionStatusChoice.ACTIVE.value

def pause_subscription(subscription):
    subscription.status = SubscriptionStatusChoice.PAUSED.value
    subscription.paused_at = timezone.now()
    subscription.save()

# Expiration check (Celery task)
@shared_task
def check_expired_subscriptions():
    today = timezone.now().date()
    expired = Subscription.objects.filter(
        end_date__lt=today,
        status=SubscriptionStatusChoice.ACTIVE.value
    )
    expired.update(status=SubscriptionStatusChoice.EXPIRED.value)
```

**Use Cases:**

- SaaS platforms
- Membership sites
- Content subscriptions
- Premium features

---

## Priority & Rating Enums

### PriorityChoice

Task/issue priority levels.

```python
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
```

**Model Usage:**

```python
class Task(models.Model):
    priority = models.IntegerField(
        choices=PriorityChoice.choices(),
        default=PriorityChoice.MEDIUM.value
    )
```

**Sorting & Filtering:**

```python
# Sort by priority (high to low)
tasks = Task.objects.order_by('-priority')

# Critical tasks only
critical = Task.objects.filter(
    priority=PriorityChoice.CRITICAL.value
)

# Priority-based notifications
if task.priority >= PriorityChoice.HIGH.value:
    send_urgent_notification(task)
```

**Color Coding:**

```python
PRIORITY_COLORS = {
    PriorityChoice.LOW.value: "green",
    PriorityChoice.MEDIUM.value: "yellow",
    PriorityChoice.HIGH.value: "orange",
    PriorityChoice.CRITICAL.value: "red",
}

def get_priority_badge(task):
    color = PRIORITY_COLORS[task.priority]
    return f'<span class="badge badge-{color}">{task.get_priority_display()}</span>'
```

**Use Cases:**

- Task management
- Issue tracking
- Support tickets
- Bug reports

---

## Role & Permission Enums

### UserRoleChoice

User role definitions.

```python
class UserRoleChoice(str, Enum):
    """User roles"""
    
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"
    
    @classmethod
    def choices(cls) -> List[Tuple[str, str]]:
        return [(item.value, item.name.title()) for item in cls]
```

**Permission Hierarchy:**

```python
ROLE_HIERARCHY = {
    UserRoleChoice.ADMIN.value: 4,
    UserRoleChoice.MODERATOR.value: 3,
    UserRoleChoice.USER.value: 2,
    UserRoleChoice.GUEST.value: 1,
}

def has_higher_role(user, required_role):
    user_level = ROLE_HIERARCHY.get(user.role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level
```

**Access Control:**

```python
# View decorator
def require_role(required_role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not has_higher_role(request.user, required_role):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

@require_role(UserRoleChoice.MODERATOR.value)
def moderate_content(request):
    # Only moderators and admins can access
    pass
```

**Use Cases:**

- Access control
- Role-based permissions
- Admin interfaces
- Multi-tenant apps

### PermissionChoice

Granular permission types.

```python
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
```

**Permission Matrix:**

```python
ROLE_PERMISSIONS = {
    UserRoleChoice.ADMIN.value: [
        PermissionChoice.VIEW.value,
        PermissionChoice.CREATE.value,
        PermissionChoice.EDIT.value,
        PermissionChoice.DELETE.value,
        PermissionChoice.PUBLISH.value,
        PermissionChoice.ADMIN.value,
    ],
    UserRoleChoice.MODERATOR.value: [
        PermissionChoice.VIEW.value,
        PermissionChoice.EDIT.value,
        PermissionChoice.DELETE.value,
        PermissionChoice.PUBLISH.value,
    ],
    UserRoleChoice.USER.value: [
        PermissionChoice.VIEW.value,
        PermissionChoice.CREATE.value,
        PermissionChoice.EDIT.value,
    ],
    UserRoleChoice.GUEST.value: [
        PermissionChoice.VIEW.value,
    ],
}

def has_permission(user, permission):
    user_perms = ROLE_PERMISSIONS.get(user.role, [])
    return permission in user_perms
```

**Use Cases:**

- Fine-grained access control
- Permission systems
- RBAC implementation
- Feature flags per role

---

## Notification Enums

### NotificationTypeChoice

Notification delivery channels.

```python
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
```

**Multi-channel Notifications:**

```python
def send_notification(user, message, channels=None):
    """Send notification through multiple channels"""
    channels = channels or [
        NotificationTypeChoice.EMAIL.value,
        NotificationTypeChoice.IN_APP.value
    ]
    
    for channel in channels:
        if channel == NotificationTypeChoice.EMAIL.value:
            send_email_notification(user, message)
        elif channel == NotificationTypeChoice.SMS.value:
            send_sms_notification(user, message)
        elif channel == NotificationTypeChoice.PUSH.value:
            send_push_notification(user, message)
        elif channel == NotificationTypeChoice.IN_APP.value:
            create_in_app_notification(user, message)
        elif channel == NotificationTypeChoice.WEBHOOK.value:
            trigger_webhook(user, message)
```

**User Preferences:**

```python
class UserNotificationPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    
    def get_enabled_channels(self):
        channels = []
        if self.email_enabled:
            channels.append(NotificationTypeChoice.EMAIL.value)
        if self.sms_enabled:
            channels.append(NotificationTypeChoice.SMS.value)
        if self.push_enabled:
            channels.append(NotificationTypeChoice.PUSH.value)
        return channels
```

### NotificationStatusChoice

Notification delivery tracking.

```python
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
```

**Delivery Tracking:**

```python
class Notification(models.Model):
    status = models.CharField(
        max_length=20,
        choices=NotificationStatusChoice.choices(),
        default=NotificationStatusChoice.PENDING.value
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)

# Mark as sent
notification.status = NotificationStatusChoice.SENT.value
notification.sent_at = timezone.now()
notification.save()

# Track opens (email pixel, push open)
notification.status = NotificationStatusChoice.OPENED.value
notification.opened_at = timezone.now()
notification.save()
```

**Use Cases:**

- Email campaigns
- Push notifications
- SMS alerts
- In-app messaging
- Webhook delivery

---

## HTTP Status Enums

### HTTPStatusChoice

HTTP response status codes.

```python
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
```

**API Response Helpers:**

```python
from rest_framework.response import Response

def success_response(data, status=HTTPStatusChoice.OK):
    return Response(data, status=status.value)

def error_response(message, status=HTTPStatusChoice.BAD_REQUEST):
    return Response(
        {"error": message},
        status=status.value
    )

def created_response(data):
    return Response(
        data,
        status=HTTPStatusChoice.CREATED.value
    )
```

**API Views:**

```python
class ArticleViewSet(viewsets.ModelViewSet):
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=HTTPStatusChoice.CREATED.value
            )
        return Response(
            serializer.errors,
            status=HTTPStatusChoice.BAD_REQUEST.value
        )
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        instance.delete()
        return Response(
            status=HTTPStatusChoice.NO_CONTENT.value
        )
```

**Use Cases:**

- REST APIs
- Status code constants
- Response helpers
- Testing

---

## Time Unit Enums

### TimeUnit

Time duration units.

```python
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
```

**Duration Calculations:**

```python
from datetime import timedelta

TIME_DELTAS = {
    TimeUnit.SECONDS.value: lambda x: timedelta(seconds=x),
    TimeUnit.MINUTES.value: lambda x: timedelta(minutes=x),
    TimeUnit.HOURS.value: lambda x: timedelta(hours=x),
    TimeUnit.DAYS.value: lambda x: timedelta(days=x),
    TimeUnit.WEEKS.value: lambda x: timedelta(weeks=x),
}

def calculate_duration(amount, unit):
    """Calculate timedelta from amount and unit"""
    return TIME_DELTAS[unit](amount)

# Usage
expiry = timezone.now() + calculate_duration(30, TimeUnit.DAYS.value)
reminder = timezone.now() + calculate_duration(2, TimeUnit.HOURS.value)
```

**Scheduling:**

```python
class ScheduledTask(models.Model):
    interval = models.IntegerField()
    interval_unit = models.CharField(
        max_length=20,
        choices=TimeUnit.choices()
    )
    
    def get_next_run(self):
        delta = calculate_duration(self.interval, self.interval_unit)
        return self.last_run + delta
```

**Use Cases:**

- Task scheduling
- Subscription periods
- Expiration times
- Reminder intervals

---

## Configuration Constants

### CacheConfig

Cache timeout configurations.

```python
class CacheConfig:
    """Cache configuration"""
    
    TIMEOUT_SHORT = 60          # 1 minute
    TIMEOUT_MEDIUM = 300        # 5 minutes
    TIMEOUT_LONG = 3600         # 1 hour
    TIMEOUT_VERY_LONG = 86400   # 24 hours
    
    KEY_PREFIX = "app:"
```

**Usage:**

```python
from django.core.cache import cache

# Cache user profile
cache.set(
    f"{CacheConfig.KEY_PREFIX}user:{user.id}",
    user_data,
    CacheConfig.TIMEOUT_MEDIUM
)

# Cache static content
cache.set(
    f"{CacheConfig.KEY_PREFIX}homepage",
    homepage_html,
    CacheConfig.TIMEOUT_LONG
)

# Cache frequently accessed data
cache.set(
    f"{CacheConfig.KEY_PREFIX}settings",
    app_settings,
    CacheConfig.TIMEOUT_VERY_LONG
)
```

### ValidationConfig

Input validation rules.

```python
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
```

**Validators:**

```python
from django.core.exceptions import ValidationError

def validate_username(value):
    if len(value) < ValidationConfig.USERNAME_MIN_LENGTH:
        raise ValidationError(
            f"Username must be at least {ValidationConfig.USERNAME_MIN_LENGTH} characters"
        )
    if len(value) > ValidationConfig.USERNAME_MAX_LENGTH:
        raise ValidationError(
            f"Username cannot exceed {ValidationConfig.USERNAME_MAX_LENGTH} characters"
        )

def validate_password(value):
    if len(value) < ValidationConfig.PASSWORD_MIN_LENGTH:
        raise ValidationError(
            f"Password must be at least {ValidationConfig.PASSWORD_MIN_LENGTH} characters"
        )
```

**Model Usage:**

```python
class User(AbstractUser):
    username = models.CharField(
        max_length=ValidationConfig.USERNAME_MAX_LENGTH,
        validators=[validate_username]
    )
    phone = models.CharField(
        max_length=ValidationConfig.PHONE_MAX_LENGTH,
        blank=True
    )
```

### PaginationConfig

Pagination settings.

```python
class PaginationConfig:
    """Pagination configuration"""
    
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1
```

**Usage:**

```python
from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = PaginationConfig.DEFAULT_PAGE_SIZE
    max_page_size = PaginationConfig.MAX_PAGE_SIZE
```

### FileConfig

File upload settings.

```python
class FileConfig:
    """File upload configuration"""
    
    MAX_FILE_SIZE = 5 * 1024 * 1024        # 5MB
    MAX_IMAGE_SIZE = 2 * 1024 * 1024       # 2MB
    MAX_VIDEO_SIZE = 100 * 1024 * 1024     # 100MB
    
    ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png", "gif", "webp"]
    ALLOWED_DOCUMENT_TYPES = ["pdf", "doc", "docx", "xls", "xlsx", "txt"]
    ALLOWED_VIDEO_TYPES = ["mp4", "avi", "mov", "mkv", "webm"]
```

**Validators:**

```python
def validate_file_size(file):
    if file.size > FileConfig.MAX_FILE_SIZE:
        raise ValidationError(f"File size cannot exceed {FileConfig.MAX_FILE_SIZE / (1024*1024)}MB")

def validate_image_type(file):
    ext = file.name.split('.')[-1].lower()
    if ext not in FileConfig.ALLOWED_IMAGE_TYPES:
        raise ValidationError(f"Invalid file type. Allowed: {', '.join(FileConfig.ALLOWED_IMAGE_TYPES)}")
```

### RateLimitConfig

Rate limiting settings.

```python
class RateLimitConfig:
    """Rate limiting configuration"""
    
    DEFAULT_WINDOW = 3600           # 1 hour
    ANONYMOUS_REQUESTS = 100
    AUTHENTICATED_REQUESTS = 1000
    STAFF_REQUESTS = 10000
```

**Usage:**

```python
def get_rate_limit(user):
    if user.is_staff:
        return RateLimitConfig.STAFF_REQUESTS
    elif user.is_authenticated:
        return RateLimitConfig.AUTHENTICATED_REQUESTS
    else:
        return RateLimitConfig.ANONYMOUS_REQUESTS
```

---

## Error Codes

### ErrorCode

Standardized error codes.

```python
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
```

**Error Responses:**

```python
def error_response(code, message, details=None):
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }

# Usage
return Response(
    error_response(
        ErrorCode.VALIDATION_ERROR.value,
        "Invalid input data",
        {"field": "email", "issue": "Invalid format"}
    ),
    status=400
)
```

**Exception Mapping:**

```python
EXCEPTION_ERROR_CODES = {
    ValidationError: ErrorCode.VALIDATION_ERROR.value,
    PermissionDenied: ErrorCode.PERMISSION_ERROR.value,
    ObjectDoesNotExist: ErrorCode.NOT_FOUND.value,
}

def get_error_code(exception):
    return EXCEPTION_ERROR_CODES.get(
        type(exception),
        ErrorCode.INTERNAL_ERROR.value
    )
```

---

## Message Templates

### MessageTemplate

Standard user-facing messages.

```python
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
```

**Usage:**

```python
# Success messages
messages.success(request, MessageTemplate.CREATED.value)
messages.info(request, MessageTemplate.UPDATED.value)

# Error messages
messages.error(request, MessageTemplate.PERMISSION_DENIED.value)
messages.warning(request, MessageTemplate.VALIDATION_FAILED.value)

# API responses
return Response({
    "message": MessageTemplate.SUCCESS.value,
    "data": serializer.data
})
```

**Customization:**

```python
def get_message(template, **kwargs):
    """Get message with variable substitution"""
    messages = {
        "created": "Successfully created {item}",
        "updated": "Successfully updated {item}",
        "deleted": "Successfully deleted {item}",
    }
    return messages[template].format(**kwargs)

# Usage
message = get_message("created", item="article")
# "Successfully created article"
```

---

## Default Values

### Defaults

Application-wide defaults.

```python
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
    CELERY_TIMEOUT = 1800      # 30 minutes
    CELERY_MAX_RETRIES = 3
```

**Usage:**

```python
# Pagination
paginator = Paginator(queryset, Defaults.PAGINATION_SIZE)

# Date formatting
formatted_date = timezone.now().strftime(Defaults.DATE_FORMAT)

# Email sending
send_mail(
    subject="Welcome",
    message="Hello!",
    from_email=Defaults.FROM_EMAIL,
    recipient_list=[user.email],
    timeout=Defaults.EMAIL_TIMEOUT
)

# JWT generation
payload = {
    'user_id': user.id,
    'exp': datetime.now() + timedelta(minutes=Defaults.JWT_EXPIRY_MINUTES)
}
token = jwt.encode(payload, settings.SECRET_KEY, algorithm=Defaults.JWT_ALGORITHM)
```

---

## Feature Flags

### FeatureFlags

Toggle features on/off.

```python
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
```

**Conditional Logic:**

```python
# Feature checks
if FeatureFlags.ENABLE_NOTIFICATIONS:
    send_notification(user, message)

if FeatureFlags.ENABLE_ANALYTICS:
    track_event("user_login", user_id=user.id)

# Middleware
class RateLimitMiddleware:
    def process_request(self, request):
        if not FeatureFlags.ENABLE_RATE_LIMITING:
            return None
        # Rate limiting logic...
```

**Template Usage:**

```python
# Context processor
def feature_flags(request):
    return {
        'FEATURES': {
            'notifications': FeatureFlags.ENABLE_NOTIFICATIONS,
            'analytics': FeatureFlags.ENABLE_ANALYTICS,
        }
    }

# Template
{% if FEATURES.notifications %}
    <div class="notification-bell">...</div>
{% endif %}
```

**Environment-based:**

```python
import os

class FeatureFlags:
    ENABLE_NOTIFICATIONS = os.getenv('ENABLE_NOTIFICATIONS', 'true').lower() == 'true'
    ENABLE_SMS = os.getenv('ENABLE_SMS', 'false').lower() == 'true'
```

---

## Best Practices

### 1. Use String Enums for Database Values

✅ **Good:**

```python
class StatusChoice(str, Enum):
    DRAFT = "draft"  # Stored as "draft" in DB
    PUBLISHED = "published"
```

❌ **Bad:**

```python
class StatusChoice(Enum):
    DRAFT = 1  # Harder to debug, less readable in DB
    PUBLISHED = 2
```

### 2. Provide Helper Methods

✅ **Good:**

```python
class StatusChoice(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    
    @classmethod
    def choices(cls):
        return [(item.value, item.name.title()) for item in cls]
    
    @classmethod
    def values(cls):
        return [item.value for item in cls]
```

### 3. Group Related Constants

✅ **Good:**

```python
class CacheConfig:
    TIMEOUT_SHORT = 60
    TIMEOUT_MEDIUM = 300
    TIMEOUT_LONG = 3600
```

❌ **Bad:**

```python
CACHE_TIMEOUT_SHORT = 60
CACHE_TIMEOUT_MEDIUM = 300
CACHE_TIMEOUT_LONG = 3600
```

### 4. Use Descriptive Names

✅ **Good:**

```python
class UserStatusChoice(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
```

❌ **Bad:**

```python
class UserStatusChoice(str, Enum):
    A = "active"
    S = "suspended"
```

### 5. Document Complex Enums

```python
class OrderStatusChoice(str, Enum):
    """Order fulfillment status
    
    Workflow:
        PENDING → CONFIRMED → PROCESSING → SHIPPED → DELIVERED
        
    Can cancel from: PENDING, CONFIRMED, PROCESSING
    Can return from: DELIVERED
    """
    PENDING = "pending"
    CONFIRMED = "confirmed"
    # ...
```

### 6. Create Mapping Dictionaries

```python
PRIORITY_COLORS = {
    PriorityChoice.LOW.value: "green",
    PriorityChoice.MEDIUM.value: "yellow",
    PriorityChoice.HIGH.value: "orange",
    PriorityChoice.CRITICAL.value: "red",
}
```

### 7. Use Environment Variables for Sensitive Defaults

```python
class Defaults:
    FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@example.com')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
```

### 8. Keep Enums Immutable

```python
# ✅ Enums are naturally immutable
StatusChoice.DRAFT = "something"  # Raises error

# ❌ Don't use mutable data structures
STATUS_DICT = {"draft": 1, "published": 2}  # Can be modified
```

---

## Usage Examples

### Example 1: Blog Post Management

```python
from enum import Enum

class PostStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    
    @classmethod
    def choices(cls):
        return [(item.value, item.name.title()) for item in cls]

class Post(models.Model):
    title = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20,
        choices=PostStatus.choices(),
        default=PostStatus.DRAFT.value
    )
    
    def publish(self):
        if self.status == PostStatus.DRAFT.value:
            self.status = PostStatus.PUBLISHED.value
            self.published_at = timezone.now()
            self.save()
    
    def archive(self):
        if self.status == PostStatus.PUBLISHED.value:
            self.status = PostStatus.ARCHIVED.value
            self.save()
```

### Example 2: User Management with Roles

```python
class UserRole(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    
    @classmethod
    def choices(cls):
        return [(item.value, item.name.title()) for item in cls]

class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices(),
        default=UserRole.USER.value
    )
    
    def is_admin(self):
        return self.role == UserRole.ADMIN.value
    
    def is_moderator_or_admin(self):
        return self.role in [UserRole.MODERATOR.value, UserRole.ADMIN.value]

# Permission decorator
def require_admin(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin():
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
```

### Example 3: Order Processing

```python
class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    
    @classmethod
    def choices(cls):
        return [(item.value, item.name.title()) for item in cls]

class Order(models.Model):
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices(),
        default=OrderStatus.PENDING.value
    )
    
    def can_cancel(self):
        return self.status in [
            OrderStatus.PENDING.value,
            OrderStatus.CONFIRMED.value,
            OrderStatus.PROCESSING.value
        ]
    
    def cancel(self):
        if not self.can_cancel():
            raise ValueError(f"Cannot cancel order in {self.status} status")
        self.status = OrderStatus.CANCELLED.value
        self.save()
```

### Example 4: Feature Flags

```python
class Features:
    ENABLE_COMMENTS = True
    ENABLE_RATINGS = True
    ENABLE_SOCIAL_SHARE = False

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    context = {
        'post': post,
        'show_comments': Features.ENABLE_COMMENTS,
        'show_ratings': Features.ENABLE_RATINGS,
        'show_social': Features.ENABLE_SOCIAL_SHARE,
    }
    
    return render(request, 'post_detail.html', context)
```

### Example 5: Configuration Constants

```python
class EmailConfig:
    FROM_EMAIL = "noreply@example.com"
    ADMIN_EMAIL = "admin@example.com"
    TIMEOUT = 30
    MAX_RETRIES = 3

def send_welcome_email(user):
    send_mail(
        subject="Welcome!",
        message=f"Hello {user.username}",
        from_email=EmailConfig.FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
        timeout=EmailConfig.TIMEOUT
    )
```

---

## Summary

| Component | Purpose | Example |
|-----------|---------|---------|
| **Status Enums** | Entity lifecycle states | DRAFT, PUBLISHED, ARCHIVED |
| **Priority Enums** | Task importance levels | LOW, MEDIUM, HIGH, CRITICAL |
| **Role Enums** | User access levels | ADMIN, MODERATOR, USER |
| **Permission Enums** | Action types | VIEW, CREATE, EDIT, DELETE |
| **Notification Enums** | Delivery channels | EMAIL, SMS, PUSH, IN_APP |
| **HTTP Status Enums** | API response codes | 200, 201, 400, 404, 500 |
| **Time Unit Enums** | Duration units | SECONDS, MINUTES, HOURS, DAYS |
| **Cache Config** | Cache timeouts | SHORT (60s), MEDIUM (5m), LONG (1h) |
| **Validation Config** | Input validation rules | MIN_LENGTH, MAX_LENGTH |
| **File Config** | Upload settings | MAX_SIZE, ALLOWED_TYPES |
| **Error Codes** | Standardized errors | VALIDATION_ERROR, NOT_FOUND |
| **Message Templates** | User messages | CREATED, UPDATED, DELETED |
| **Defaults** | Application defaults | PAGINATION_SIZE, TIMEZONE |
| **Feature Flags** | Feature toggles | ENABLE_NOTIFICATIONS, ENABLE_SMS |

---

## Next Steps

1. Identify magic strings in your codebase
2. Create appropriate enums
3. Replace strings with enum values
4. Add validation using enum values
5. Document enum workflows
6. Set up feature flags
7. Configure constants for your environment

---

**Key Takeaways:**

- Use enums instead of magic strings
- Provide helper methods (`.choices()`, `.values()`)
- Group related constants in classes
- Use descriptive names
- Document complex workflows
- Keep enums immutable
- Use environment variables for sensitive defaults