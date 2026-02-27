# Django Helper Functions & Decorators Guide

**A comprehensive guide to production-grade utility functions and decorators for common Django operations**

---

## Table of Contents

1. [Overview](#overview)
2. [Validation Helpers](#validation-helpers)
3. [String Helpers](#string-helpers)
4. [JSON Helpers](#json-helpers)
5. [Date/Time Helpers](#datetime-helpers)
6. [Email Helpers](#email-helpers)
7. [ID/Token Helpers](#idtoken-helpers)
8. [List/Dict Helpers](#listdict-helpers)
9. [File Helpers](#file-helpers)
10. [Permission & Auth Decorators](#permission--auth-decorators)
11. [Caching Decorators](#caching-decorators)
12. [Database Helpers](#database-helpers)
13. [Best Practices](#best-practices)
14. [Common Patterns](#common-patterns)

---

## Overview

Helper functions and decorators provide reusable utilities for:

- **Data validation** — Email, phone, password, URL, IP address
- **String manipulation** — Truncation, case conversion, slugification, masking
- **JSON operations** — Safe parsing, serialization, merging
- **Date/Time** — Date ranges, timeframes, human-readable durations
- **Email** — Template-based emails, verification, password reset
- **ID/Token generation** — Random tokens and codes
- **List/Dict operations** — Chunking, flattening, extraction
- **File operations** — Extension checking, size formatting
- **Caching** — Result caching, per-request caching, memoization
- **Database** — Bulk soft deletes, restores, audit logging

### Why Use Them?

- **Consistency** across your codebase
- **Less boilerplate** — Reuse instead of rewrite
- **Better error handling** — Safe operations with defaults
- **Performance** — Built-in caching and optimization
- **Security** — Validated inputs and privacy masking

### Quick Start

```python
from .helpers import (
    is_valid_email,
    truncate_string,
    cache_result,
    send_template_email,
)

# Validation
if is_valid_email(user_email):
    send_template_email(...)

# String operations
short_title = truncate_string(title, length=50)

# Caching
@cache_result(timeout=3600)
def expensive_operation():
    return compute_something()
```

---

## Validation Helpers

Validate common data formats safely and consistently.

### Email Validation

```python
from .helpers import is_valid_email

# Basic validation
if is_valid_email("user@example.com"):
    # Email is valid
    pass

# Use case: form validation
def validate_email_field(email):
    if not is_valid_email(email):
        raise ValidationError("Invalid email format")
```

**Pattern:**

```python
pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
```

**Returns:** `True` or `False`

### Phone Validation

```python
from .helpers import is_valid_phone

if is_valid_phone("+1-555-0123"):
    # Phone is valid (accepts formats like +1 555 0123, (555) 0123, etc)
    pass

# Use case: form validation
def validate_phone_field(phone):
    if not is_valid_phone(phone):
        raise ValidationError("Invalid phone format")
```

**Pattern:** Accepts 10+ digits with optional separators: `-`, `+`, `()`, spaces

### URL Validation

```python
from .helpers import is_valid_url

if is_valid_url("https://example.com"):
    # URL is valid (must start with http:// or https://)
    pass

# Use case: external links
def validate_external_link(url):
    if not is_valid_url(url):
        raise ValidationError("Invalid URL format")
```

**Pattern:** `^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`

### IPv4 Validation

```python
from .helpers import is_valid_ipv4

if is_valid_ipv4("192.168.1.1"):
    # IP is valid
    pass

# Use case: IP whitelisting
def is_ip_allowed(ip_address):
    return is_valid_ipv4(ip_address) and ip_address in ALLOWED_IPS
```

**Validation:** Checks format and ensures each octet is 0-255

### Password Strength Validation

```python
from .helpers import is_strong_password

is_valid, errors = is_strong_password("MyPassword123!")

if not is_valid:
    print(errors)
    # ['Password must contain special characters', ...]
```

**Requirements:**

- At least 8 characters
- Contains lowercase letters
- Contains uppercase letters
- Contains numbers
- Contains special characters

**Returns:** `(bool, List[str])` — Valid flag and list of errors

**Use case:** User registration

```python
class UserSerializer(serializers.ModelSerializer):
    def validate_password(self, value):
        is_valid, errors = is_strong_password(value)
        if not is_valid:
            raise ValidationError(errors)
        return value
```

---

## String Helpers

Manipulate and format strings safely.

### Truncate String

```python
from .helpers import truncate_string

title = "This is a very long title that needs to be shortened"
short_title = truncate_string(title, length=30)
# Output: "This is a very long title th..."

# Custom suffix
short_title = truncate_string(title, length=30, suffix=" [more]")
# Output: "This is a very long title [more]"
```

**Use cases:**

- List view display
- Meta descriptions
- Preview text

### Case Conversion

```python
from .helpers import camelcase_to_snakecase, snakecase_to_camelcase

# camelCase → snake_case
camelcase_to_snakecase("firstName")  # "first_name"
camelcase_to_snakecase("HTTPResponse")  # "h_t_t_p_response"

# snake_case → camelCase
snakecase_to_camelcase("first_name")  # "firstName"
snakecase_to_camelcase("user_id")  # "userId"
```

**Use cases:**

- API field name conversion
- Database to JavaScript field names
- Configuration parsing

### Slug Generation

```python
from .helpers import generate_slug

# Basic slug
generate_slug("My Awesome Article")  # "my-awesome-article"

# With unique ID
generate_slug("My Awesome Article", unique_id="abc123def456")
# "my-awesome-article-abc123de"
```

**Use cases:**

- URL-friendly article titles
- Unique identifiers
- SEO-friendly URLs

### Email Masking

```python
from .helpers import mask_email

mask_email("john.doe@example.com")  # "j*****e@example.com"
mask_email("admin@example.com")  # "a***n@example.com"
mask_email("u@example.com")  # "*@example.com"
```

**Use cases:**

- Privacy in logs
- Admin email display
- User listings

### Phone Masking

```python
from .helpers import mask_phone

mask_phone("+1-555-0123")  # "***0123"
mask_phone("5550123456")  # "******3456"
```

**Use cases:**

- Privacy in logs
- Confirmation screens
- User data protection

---

## JSON Helpers

Handle JSON safely with fallbacks.

### Safe JSON Loading

```python
from .helpers import safe_json_loads

# Normal parsing
data = safe_json_loads('{"key": "value"}')
# {"key": "value"}

# With invalid JSON
data = safe_json_loads('invalid json', default={})
# {} (default returned, warning logged)

# With None
data = safe_json_loads(None, default=None)
# None
```

**Advantages:**

- Won't raise JSONDecodeError
- Logs warnings for debugging
- Provides default fallback

**Use cases:**

- External API responses
- Stored JSON fields
- Configuration parsing

### Safe JSON Serialization

```python
from .helpers import safe_json_dumps

# Normal serialization
json_str = safe_json_dumps({"key": "value"})
# '{"key": "value"}'

# With datetime objects
json_str = safe_json_dumps({
    "created": datetime.now(),
    "count": 42
})
# '{"created": "2025-02-27 10:30:45.123456", "count": 42}'

# With invalid data
json_str = safe_json_dumps(some_object, default='{}')
# '{}' (default returned, warning logged)
```

**Advantages:**

- Converts datetime automatically (via `default=str`)
- Won't raise TypeError
- Logs warnings
- Provides fallback

### Deep Dictionary Merge

```python
from .helpers import deep_merge

dict1 = {
    "user": {"name": "John", "age": 30},
    "settings": {"theme": "dark"}
}

dict2 = {
    "user": {"email": "john@example.com"},
    "settings": {"notifications": True}
}

merged = deep_merge(dict1, dict2)
# {
#   "user": {"name": "John", "age": 30, "email": "john@example.com"},
#   "settings": {"theme": "dark", "notifications": True}
# }
```

**Advantages:**

- Recursive merging of nested dicts
- Preserves original dicts (non-mutating)
- Later dict values override earlier ones

**Use cases:**

- Configuration merging
- Settings inheritance
- API response combining

---

## Date/Time Helpers

Handle dates and times consistently.

### Date Range Generation

```python
from .helpers import get_date_range

# Last 7 days
start_date, end_date = get_date_range(days=7)

# Last 30 days
start_date, end_date = get_date_range(days=30)

# Use in queryset
articles = Article.objects.filter(
    created_at__gte=start_date,
    created_at__lte=end_date
)
```

**Returns:** `(datetime, datetime)` — Both are timezone-aware

**Use cases:**

- Analytics queries
- Recent activity
- Date filtering

### Timeframe Checking

```python
from .helpers import is_within_timeframe

# Check if timestamp is within last 24 hours
if is_within_timeframe(user.last_login, hours=24):
    # User logged in recently
    pass

# Check if token is still valid (1 hour)
if is_within_timeframe(token.created_at, hours=1):
    # Token is still valid
    pass
```

**Use cases:**

- Token expiration
- Recent activity detection
- Rate limiting

### Human-Readable Timedelta

```python
from .helpers import humanize_timedelta
from datetime import timedelta

# Seconds
td = timedelta(seconds=45)
humanize_timedelta(td)  # "45 seconds"

# Hours
td = timedelta(hours=3)
humanize_timedelta(td)  # "3 hours"

# Days
td = timedelta(days=5)
humanize_timedelta(td)  # "5 days"

# Mixed
td = timedelta(days=1, hours=2, minutes=30)
humanize_timedelta(td)  # "1 day" (shows largest unit)
```

**Use cases:**

- "Posted 3 hours ago"
- "Last updated 2 days ago"
- Duration display

**Example:**

```python
class ArticleSerializer(serializers.ModelSerializer):
    time_since_created = serializers.SerializerMethodField()
    
    def get_time_since_created(self, obj):
        delta = timezone.now() - obj.created_at
        return humanize_timedelta(delta)
```

---

## Email Helpers

Send templated emails consistently.

### Template-Based Email

```python
from .helpers import send_template_email

success = send_template_email(
    subject="Welcome to our site",
    template_name="emails/welcome.html",
    context={
        "user": user,
        "site_name": "My Site",
    },
    recipient_list=[user.email],
    from_email="noreply@example.com"  # Optional
)

if not success:
    logger.error("Email failed to send")
```

**Template file** (`templates/emails/welcome.html`):

```html
<h1>Welcome, {{ user.first_name }}!</h1>
<p>Thanks for joining {{ site_name }}.</p>
```

**Advantages:**

- Uses Django templates
- Automatic error logging
- Returns success status
- Better than plain text

**Use cases:**

- Welcome emails
- Notifications
- Confirmations

### Email Verification

```python
from .helpers import send_verification_email

# Send verification email
token = generate_token()
success = send_verification_email(
    user=user,
    token=token,
    base_url="https://example.com"
)

# User clicks link in email
# Your view receives: /verify-email/{token}/

# Template automatically includes:
# - {{ verification_url }}
# - {{ token }}
# - {{ user }}
```

**Template file** (`templates/emails/verification.html`):

```html
<h1>Verify your email</h1>
<p>Click <a href="{{ verification_url }}">here</a> to verify.</p>
<p>Or use code: {{ token }}</p>
```

### Password Reset Email

```python
from .helpers import send_password_reset_email

success = send_password_reset_email(
    user=user,
    base_url="https://example.com"
)

# Email includes:
# - {{ reset_url }}
# - {{ user }}
```

**Template file** (`templates/emails/password_reset.html`):

```html
<h1>Reset your password</h1>
<p>
    <a href="{{ reset_url }}">Click here to reset your password</a>
</p>
<p>This link expires in 24 hours.</p>
```

**Flow:**

1. User requests password reset
2. Generate token using `default_token_generator`
3. Send email with reset link
4. User clicks link and verifies token
5. Allow password change

---

## ID/Token Helpers

Generate random tokens and codes.

### Random Token Generation

```python
from .helpers import generate_token

# 32-character token (default)
token = generate_token()
# "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

# Custom length
token = generate_token(length=16)
# "a1b2c3d4e5f6g7h8"

# Store in database
user.email_verification_token = token
user.save()
```

**Uses:** UUID hex encoding for randomness

**Use cases:**

- Email verification tokens
- Password reset tokens
- API tokens
- One-time codes

### Code Generation

```python
from .helpers import generate_code

# Simple code
code = generate_code()
# "A1B2C3"

# With prefix
code = generate_code(prefix="INV")
# "INV-A1B2C3"

# Custom length
code = generate_code(prefix="ORDER", length=8)
# "ORDER-A1B2C3D4"
```

**Use cases:**

- Invoice numbers
- Order codes
- Coupon codes
- Reference numbers

**Example:**

```python
class Invoice(models.Model):
    code = models.CharField(max_length=20, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code(prefix="INV")
        super().save(*args, **kwargs)
```

---

## List/Dict Helpers

Manipulate collections efficiently.

### List Chunking

```python
from .helpers import chunk_list

items = list(range(1, 11))  # [1, 2, 3, ..., 10]

chunks = chunk_list(items, chunk_size=3)
# [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]

# Batch processing
for batch in chunk_list(users, chunk_size=100):
    send_email_batch(batch)
```

**Use cases:**

- Batch processing
- Pagination
- API rate limiting
- Database bulk operations

### List Flattening

```python
from .helpers import flatten_list

nested = [[1, 2], [3, [4, 5]], [6]]
flat = flatten_list(nested)
# [1, 2, 3, 4, 5, 6]

# Use case: extract all values
tags = [post.tags.all() for post in posts]
flat_tags = flatten_list(tags)
```

### Query String Conversion

```python
from .helpers import dict_to_querystring

params = {
    "search": "django",
    "page": 1,
    "limit": 10,
    "filters": None  # Ignored
}

query_string = dict_to_querystring(params)
# "search=django&page=1&limit=10"

# Build redirect URL
redirect_url = f"/search?{query_string}"
```

### Dictionary Key Extraction

```python
from .helpers import extract_dict_keys

data = {
    "username": "john",
    "email": "john@example.com",
    "password": "secret123",
    "first_name": "John"
}

# Extract only specific keys
safe_data = extract_dict_keys(data, ["username", "email", "first_name"])
# {"username": "john", "email": "john@example.com", "first_name": "John"}

# Use case: safe data exposure
def get_public_user_data(user):
    data = user.__dict__
    return extract_dict_keys(data, ["username", "email", "first_name"])
```

---

## File Helpers

Handle file operations safely.

### File Extension

```python
from .helpers import get_file_extension, is_allowed_file_type

filename = "document.pdf"
ext = get_file_extension(filename)  # "pdf"

# Check if allowed
allowed = ["pdf", "docx", "txt"]
if is_allowed_file_type(filename, allowed):
    process_file(filename)
```

**Use case:** File upload validation

```python
class DocumentSerializer(serializers.ModelSerializer):
    def validate_file(self, value):
        allowed = ["pdf", "doc", "docx"]
        if not is_allowed_file_type(value.name, allowed):
            raise ValidationError("Only PDF and Word documents allowed")
        return value
```

### File Size Formatting

```python
from .helpers import format_file_size

format_file_size(512)        # "0.50 KB"
format_file_size(1024)       # "1.00 KB"
format_file_size(1024*1024)  # "1.00 MB"
format_file_size(1024*1024*1024)  # "1.00 GB"
```

**Use cases:**

- Display file sizes
- Upload progress
- Storage information

**Example:**

```python
class FileListSerializer(serializers.ModelSerializer):
    file_size_display = serializers.SerializerMethodField()
    
    def get_file_size_display(self, obj):
        return format_file_size(obj.file.size)
```

---

## Permission & Auth Decorators

Check permissions and authenticate users with decorators.

### Check Permissions Decorator

```python
from .decorators import check_permissions
from rest_framework.exceptions import PermissionDenied

@check_permissions(['articles.view_article', 'articles.change_article'])
def my_view(self, request):
    """Only users with both permissions can access"""
    pass
```

**Features:**

- Check multiple permissions at once
- Automatic authentication check
- Raises `PermissionDenied` if missing
- Works on view methods

**How it works:**

1. Checks if user is authenticated
2. Checks each required permission
3. Raises error if any missing
4. Otherwise allows access

**Use Cases:**

- Admin actions
- Bulk operations
- Dangerous operations
- Role-based access

**Example:**

```python
class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    
    @check_permissions(['articles.delete_article'])
    @action(detail=True, methods=['delete'])
    def permanent_delete(self, request, pk=None):
        """Only users with delete permission"""
        article = self.get_object()
        article.delete()
        return Response(status=204)
```

### Check Object Permissions Decorator

```python
from .decorators import check_object_permissions

@check_object_permissions
def my_view(self, request, pk=None):
    """Only users with object-level permissions can access"""
    pass
```

**Features:**

- Checks object-level permissions
- Uses DRF's permission system
- Gets object automatically
- Raises error if denied

**Use Cases:**

- Ownership checks
- Row-level security
- Custom permission logic

**Example:**

```python
class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    
    @check_object_permissions
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Only object owner can publish"""
        article = self.get_object()
        article.publish()
        return Response({"status": "published"})
```

### Log Action Decorator

```python
from .decorators import log_action

@log_action("PUBLISH_ARTICLE")
def my_view(self, request):
    """Log this action with user context"""
    pass
```

**Features:**

- Logs action type
- Includes user ID
- Includes HTTP method
- Includes request path

**Output:**

```
PUBLISH_ARTICLE: ArticleViewSet
user_id=123, method=POST, path=/articles/1/publish/
```

**Use Cases:**

- Audit trails
- Activity logging
- Admin actions
- Important operations

**Example:**

```python
class ArticleViewSet(viewsets.ModelViewSet):
    @log_action("CREATE_ARTICLE")
    def create(self, request, *args, **kwargs):
        logger.info("Creating article")
        return super().create(request, *args, **kwargs)
    
    @log_action("DELETE_ARTICLE")
    def destroy(self, request, *args, **kwargs):
        logger.info("Deleting article")
        return super().destroy(request, *args, **kwargs)
```

---

## Caching Decorators

Cache function results for performance.

### Result Caching

```python
from .helpers import cache_result

@cache_result(timeout=3600)  # 1 hour
def get_expensive_data(user_id):
    # This computation only happens once per hour
    return ExpensiveModel.objects.filter(
        user_id=user_id
    ).aggregate(...)

# Call it multiple times - only computes once
result1 = get_expensive_data(123)  # Computed
result2 = get_expensive_data(123)  # From cache
result3 = get_expensive_data(456)  # Computed (different arg)

# Clear cache when needed
get_expensive_data.clear_cache()
```

**Features:**

- Arguments included in cache key
- Automatic MD5 hashing for args/kwargs
- Debug logging
- Manual cache clearing

**Use cases:**

- Database queries
- API calls
- Complex calculations
- Report generation

**How it works:**

```
Cache key = module.function:md5(args):md5(kwargs)
Example: myapp.helpers.get_expensive_data:a1b2c3:d4e5f6
```

### Per-Request Caching

```python
from .helpers import cache_per_request

class ArticleViewSet(viewsets.ModelViewSet):
    @cache_per_request()
    def get_queryset(self, request):
        # Queryset is computed once per request
        return Article.objects.filter(owner=request.user)
    
    def list(self, request, *args, **kwargs):
        # Called twice, but cached
        qs1 = self.get_queryset(request)  # Computed
        qs2 = self.get_queryset(request)  # From cache
        ...
```

**Use cases:**

- Avoid repeated database queries in one request
- View permissions check caching
- Queryset computation

### Retry with Exponential Backoff

```python
from .helpers import retry_on_exception

@retry_on_exception(max_retries=3, delay=1.0)
def call_external_api():
    # If it fails, retry up to 3 times with backoff
    # Delays: 1s, 2s, 4s
    return requests.get("https://api.example.com")

# Use cases: external APIs, database operations
```

**Backoff Schedule:**

- Attempt 1: Immediate
- Attempt 2: Delay * 2^0 = 1 second
- Attempt 3: Delay * 2^1 = 2 seconds
- Attempt 4: Delay * 2^2 = 4 seconds

### Memoization (In-Memory Cache)

```python
from .helpers import memoize

@memoize
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# First call: computes fibonacci(100)
result = fibonacci(100)

# Second call: returns cached result
result = fibonacci(100)

# Access cache
fibonacci.cache  # {(100,): result, ...}

# Clear cache
fibonacci.clear_cache()
```

**Differences from `@cache_result`:**

| Feature | @cache_result | @memoize |
|---------|---------------|----------|
| Storage | Redis/cache | In-memory dict |
| Timeout | Yes | No (until cleared) |
| Persistence | Across restarts | Per-process |
| Use case | Expensive DB queries | Pure functions |

**Use case:** Pure recursive functions, mathematical calculations

---

## Database Helpers

Handle common database operations.

### Bulk Soft Delete

```python
from .helpers import bulk_soft_delete

# Soft delete articles
articles = Article.objects.filter(author=user)
count, details = bulk_soft_delete(articles)

# count: 5
# details: {"app.Article": 5}

# Usage: mark as deleted without removing
```

**Requirements:** Model must have `deleted_at` field

```python
class Article(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)
```

**Features:**

- Atomic transaction
- Logs the operation
- Returns count and breakdown

### Bulk Restore

```python
from .helpers import bulk_restore

# Restore soft-deleted articles
articles = Article.objects.filter(deleted_at__isnull=False)
count = bulk_restore(articles)

# Articles are restored (deleted_at = None)
```

### Audit Logging

```python
from .helpers import log_audit

# After creating an article
article = Article.objects.create(
    title="New Article",
    author=user
)

log_audit(
    action="create",
    instance=article,
    user=user,
    ip_address=request.META.get('REMOTE_ADDR'),
    user_agent=request.META.get('HTTP_USER_AGENT')
)
```

**Audit Log Fields:**

```python
AuditLog(
    action="create",          # create, update, delete, restore, publish
    content_object=article,   # The instance being audited
    object_id="123",          # Instance PK
    object_repr="Article: New Article",  # str(instance)
    changes={"title": "New Article"},    # Optional
    user=user,                # Who did it
    ip_address="192.168.1.1", # Request IP
    user_agent="Mozilla/..."  # Browser info
)
```

**Use cases:**

- Compliance tracking
- Change history
- User activity logs
- Security auditing

**In ViewSets:**

```python
class ArticleViewSet(BaseViewSet):
    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            action="create",
            instance=instance,
            user=self.request.user,
            changes=serializer.validated_data,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
```

---

## Best Practices

### 1. Always Use Safe JSON Operations

```python
# ✅ Good - won't crash on invalid data
data = safe_json_loads(api_response, default={})

# ❌ Bad - crashes on invalid JSON
data = json.loads(api_response)
```

### 2. Validate User Input

```python
# ✅ Good - validate before processing
if not is_valid_email(email):
    raise ValidationError("Invalid email")

# ❌ Bad - assume input is valid
send_email(email)  # Might fail silently
```

### 3. Use Appropriate Caching

```python
# ✅ Good - cache DB queries
@cache_result(timeout=3600)
def get_category_stats(category_id):
    return expensiveDB_query()

# ❌ Bad - cache too long
@cache_result(timeout=86400)  # 24 hours
def get_current_user_data(user_id):
    return User.objects.get(id=user_id)
```

### 4. Log Sensitive Operations

```python
# ✅ Good - audit everything
log_audit(
    action="delete",
    instance=user,
    user=admin_user,
    ip_address=request.META.get('REMOTE_ADDR')
)

# ❌ Bad - no audit trail
user.delete()
```

### 5. Mask Sensitive Data in Logs

```python
# ✅ Good - mask before logging
logger.info(f"Email: {mask_email(user.email)}")

# ❌ Bad - logs full email
logger.info(f"Email: {user.email}")
```

### 6. Use Chunking for Bulk Operations

```python
# ✅ Good - process in batches
for batch in chunk_list(users, chunk_size=100):
    send_notification_batch(batch)

# ❌ Bad - all at once
send_notification_batch(all_users)  # Memory issues
```

### 7. Handle Email Failures Gracefully

```python
# ✅ Good - check return value
if send_template_email(...):
    user.email_verified = True
    user.save()
else:
    logger.error("Email failed to send")
    # Don't mark as verified if email failed

# ❌ Bad - assume success
send_template_email(...)
user.email_verified = True
user.save()
```

### 8. Use Retry for Unreliable Operations

```python
# ✅ Good - retry flaky external API
@retry_on_exception(max_retries=3, delay=1.0)
def sync_with_external_api():
    return external_api.sync()

# ❌ Bad - fail immediately
def sync_with_external_api():
    return external_api.sync()
```

---

## Common Patterns

### Pattern 1: Complete User Registration

```python
class UserSerializer(serializers.ModelSerializer):
    def validate_email(self, value):
        if not is_valid_email(value):
            raise ValidationError("Invalid email")
        return value
    
    def validate_password(self, value):
        is_valid, errors = is_strong_password(value)
        if not is_valid:
            raise ValidationError(errors)
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        
        # Send verification email
        token = generate_token()
        user.email_verification_token = token
        user.save()
        
        send_verification_email(
            user=user,
            token=token,
            base_url="https://example.com"
        )
        
        # Log the action
        log_audit(
            action="create",
            instance=user,
            changes={"email": user.email}
        )
        
        return user
```

### Pattern 2: Audit Trail for Updates

```python
class ArticleViewSet(BaseViewSet):
    def perform_update(self, serializer):
        instance = serializer.instance
        old_data = {
            "title": instance.title,
            "content": instance.content,
            "status": instance.status,
        }
        
        instance = serializer.save()
        
        changes = {}
        for key in old_data:
            old_val = old_data[key]
            new_val = getattr(instance, key)
            if old_val != new_val:
                changes[key] = {"old": old_val, "new": new_val}
        
        if changes:
            log_audit(
                action="update",
                instance=instance,
                user=self.request.user,
                changes=changes,
                ip_address=self.request.META.get('REMOTE_ADDR')
            )
```

### Pattern 3: Cached API Integration

```python
@cache_result(timeout=3600)
def get_exchange_rates(from_currency, to_currency):
    """Get exchange rates from external API"""
    response = requests.get(
        f"https://api.exchangerate.com/latest?from={from_currency}"
    )
    data = safe_json_loads(response.text, default={})
    return data.get("rates", {}).get(to_currency)

# Cache is invalidated hourly
# Or manually: get_exchange_rates.clear_cache()
```

### Pattern 4: Batch Email Sending

```python
def send_newsletter(newsletter, recipients):
    """Send newsletter to recipients in batches"""
    for batch in chunk_list(recipients, chunk_size=50):
        for user in batch:
            success = send_template_email(
                subject=newsletter.subject,
                template_name="emails/newsletter.html",
                context={
                    "user": user,
                    "content": newsletter.content,
                    "unsubscribe_url": f"https://example.com/unsubscribe/{user.id}"
                },
                recipient_list=[user.email]
            )
            
            if not success:
                logger.error(f"Newsletter failed for {mask_email(user.email)}")
```

### Pattern 5: Secure Data Export

```python
def export_user_data(user):
    """Export user data with sensitive info masked"""
    from .helpers import extract_dict_keys, mask_email, mask_phone
    
    # Define safe fields
    safe_fields = ["id", "username", "first_name", "last_name", "created_at"]
    
    # Extract safe data
    data = extract_dict_keys(user.__dict__, safe_fields)
    
    # Add masked sensitive data
    data["email"] = mask_email(user.email)
    data["phone"] = mask_phone(user.phone) if user.phone else None
    
    return data
```

---

## Summary

| Helper | Purpose |
|--------|---------|
| **is_valid_*** | Validate email, phone, URL, IP, password |
| **truncate_string** | Shorten strings safely |
| **case conversion** | Change naming conventions |
| **generate_slug** | URL-friendly identifiers |
| **mask_*** | Privacy protection |
| **safe_json_*** | Safe JSON operations |
| **deep_merge** | Merge nested dicts |
| **get_date_range** | Query last N days |
| **is_within_timeframe** | Check time windows |
| **humanize_timedelta** | "3 hours ago" |
| **send_template_email** | Templated emails |
| **send_verification_email** | Email verification |
| **send_password_reset_email** | Password reset |
| **generate_token** | Random tokens |
| **generate_code** | Random codes |
| **chunk_list** | Batch processing |
| **flatten_list** | Nested to flat |
| **dict_to_querystring** | Build URLs |
| **extract_dict_keys** | Safe data extraction |
| **format_file_size** | Human-readable sizes |
| **@check_permissions** | Check multiple permissions |
| **@check_object_permissions** | Check object-level permissions |
| **@log_action** | Log view actions |
| **@cache_result** | Cache DB queries |
| **@cache_per_request** | Per-request cache |
| **@retry_on_exception** | Retry with backoff |
| **@memoize** | In-memory cache |
| **bulk_soft_delete** | Batch soft deletes |
| **bulk_restore** | Batch restores |
| **log_audit** | Audit trail |

---

## Next Steps

1. Import helpers in your views/serializers
2. Use validation for all user input
3. Add caching to expensive operations
4. Log important actions
5. Mask sensitive data in logs

---

## Questions?

Refer to:
1. **Validation Helpers** for input validation
2. **String Helpers** for text manipulation
3. **Caching Decorators** for performance
4. **Email Helpers** for user communication
5. **Common Patterns** for real examples