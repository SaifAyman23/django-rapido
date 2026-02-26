# Ultimate Django Reusable Components Guide 🚀

**Complete production-grade component library for rapid Django development**

Last Updated: February 26, 2026  
Django Version: 5.2 LTS / 6.0  
Status: Production Ready ✅

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Component Breakdown](#component-breakdown)
3. [Quick Start](#quick-start)
4. [Usage Examples](#usage-examples)
5. [Performance Tips](#performance-tips)
6. [Error Handling](#error-handling)
7. [Testing](#testing)
8. [Best Practices](#best-practices)

---

## Overview

This is the **ultimate production-grade component library** for Django REST Framework with:

✅ **Error Handling** - Comprehensive exception classes with logging  
✅ **Performance Optimization** - Caching, query optimization, pagination  
✅ **Rapid Development** - Reusable base classes reduce 80% of boilerplate  
✅ **Security** - Permissions, rate limiting, audit logging  
✅ **Database** - Soft deletes, change tracking, audit trails  
✅ **API Features** - Filtering, searching, pagination, bulk operations  
✅ **Admin** - Enhanced Django admin with custom actions  
✅ **Logging** - Request/response logging, performance monitoring  

---

## Component Breakdown

### 1. `models.py` - Database Layer (850+ lines)

**Features:**
- UUID primary keys
- Soft delete support
- Change tracking
- Publishable models
- SEO optimization
- View counting
- Rating system
- Audit logging

**Key Classes:**

```python
# Base models
UUIDModel                  # UUID primary key
TimestampedModel          # Created/Updated timestamps
SoftDeleteModel           # Soft delete with restore
ChangeTrackingModel       # Track field changes
PublishableModel          # Draft/Published status
SEOModel                  # SEO fields (title, description, keywords)
ViewableModel             # View counting
RateableModel             # Rating system
CustomUser                # Enhanced user model
AuditLog                  # Audit trail

# Managers
CustomUserManager         # User creation/auth
SoftDeleteManager         # Soft delete queries
TimestampedManager        # Time-based queries

# Querysets
SoftDeleteQuerySet        # Soft delete filtering
TimestampedQuerySet       # Recent/older queries
```

**Usage:**

```python
from common.models import SoftDeleteModel, PublishableModel, CustomUser

class Article(SoftDeleteModel, PublishableModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    # Automatically get:
    # - id (UUID)
    # - created_at, updated_at
    # - deleted_at (soft delete)
    # - status, published_at
    # - Objects manager with .active(), .deleted(), .restore()

# Query operations
Article.objects.active()                    # Non-deleted
Article.objects.deleted()                   # Only deleted
Article.objects.published()                 # Published only
article.soft_delete()                       # Soft delete
article.restore()                           # Restore
```

---

### 2. `serializers.py` - API Serialization (600+ lines)

**Features:**
- Dynamic field selection
- Audit trail integration
- Bulk operations
- Custom field types
- Nested relationships
- Permission-based visibility

**Key Classes:**

```python
# Base serializers
DynamicFieldsSerializer          # ?fields=id,name,email
AuditableSerializer              # Create/update logging
TimestampedSerializer            # Combine both

# Field types
ColorField                       # Hex colors
SlugField                        # URL-friendly slugs
JSONSerializerField              # JSON validation
EnumField                        # Choice fields
PriceField                       # Decimal prices

# User serializers
UserCreateSerializer             # Registration with validation
UserDetailSerializer             # Full user info
UserListSerializer               # Lightweight list view
UserUpdateSerializer             # Profile updates
UserPasswordChangeSerializer     # Password reset

# Bulk operations
BulkCreateSerializer             # Create multiple
BulkUpdateSerializer             # Update multiple
NestedCreateSerializer           # Nested relationships

# Utilities
PaginationSerializer             # Pagination metadata
ErrorSerializer                  # Error responses
SuccessResponseSerializer        # Success responses
```

**Usage:**

```python
from common.serializers import DynamicFieldsSerializer, AuditableSerializer

class ArticleSerializer(DynamicFieldsSerializer, AuditableSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author', 'created_at', 'updated_at']

# Dynamic fields: ?fields=id,title
# Automatic audit logging on create/update
# Soft delete support
```

---

### 3. `viewsets.py` - API Views (700+ lines)

**Features:**
- Bulk create/update/delete
- Soft delete support
- Publishing workflows
- Ratings
- Advanced filtering
- Caching
- Audit logging

**Key Classes:**

```python
# Base viewsets
BaseViewSet                      # Core CRUD with logging
SoftDeleteViewSet               # Soft delete operations
PublishableViewSet              # Publish/unpublish actions
RatableViewSet                  # Rating endpoints
BulkOperationViewSet            # Bulk operations
UserViewSet                     # User management
CachedViewSet                   # Response caching

# Decorators
@log_action("CREATE")           # Action logging
@check_permissions(['perm1'])   # Permission checks
@check_object_permissions       # Object-level permissions
```

**Usage:**

```python
from common.viewsets import BaseViewSet, SoftDeleteViewSet

class ArticleViewSet(SoftDeleteViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    search_fields = ['title', 'content']
    
    # Automatically get:
    # - Full CRUD
    # - .deleted() - soft deleted records
    # - /restore/ - restore action
    # - /bulk_restore/ - bulk restore
    # - Audit logging
    # - Error handling
```

**Endpoints:**

```
POST   /api/articles/                    # Create
GET    /api/articles/                    # List
GET    /api/articles/{id}/               # Retrieve
PUT    /api/articles/{id}/               # Update
DELETE /api/articles/{id}/               # Delete

# Soft delete endpoints
GET    /api/articles/deleted/            # View deleted
POST   /api/articles/{id}/restore/       # Restore one
POST   /api/articles/bulk_restore/       # Restore many
DELETE /api/articles/bulk_delete/        # Delete many

# Filtering
GET    /api/articles/?search=django      # Search
GET    /api/articles/?ordering=-created_at
GET    /api/articles/?page_size=20
GET    /api/articles/?fields=id,title
```

---

### 4. `permissions.py` - Access Control (500+ lines)

**Features:**
- Role-based access control
- Owner-based permissions
- Custom rules
- Rate limiting
- Permission caching
- Two-factor verification

**Key Classes:**

```python
# Authentication
IsAuthenticated                  # Must be logged in
IsAnonymous                      # Must NOT be logged in
IsAuthenticatedOrReadOnly       # Auth required for write

# Roles
IsAdmin                         # Staff/admin users
IsSuperUser                     # Superuser only
IsInGroup                       # Group membership

# Ownership
IsOwner                         # User == owner
IsOwnerOrReadOnly               # Owner can edit
IsOwnerOrAdmin                  # Owner or admin

# Features
IsVerified                      # Email verified
HasTwoFactorEnabled             # 2FA enabled
IsObjectPublished               # Object is published

# Advanced
MultiplePermissionsRequired     # AND logic
AnyPermissionRequired           # OR logic
CustomPermissionRule            # Custom functions
RateLimitPermission             # Rate limiting
CachedPermission                # Permission caching

# Factories
create_group_permission()       # Generate group check
create_permission_check()       # Generate perm check
combine_permissions()           # Combine classes
```

**Usage:**

```python
from common.permissions import IsOwnerOrReadOnly, IsVerified

class ArticleViewSet(BaseViewSet):
    permission_classes = [IsOwnerOrReadOnly, IsVerified]
    # Owner can edit, others read-only
    # User must be verified
```

---

### 5. `exceptions.py` - Error Handling (400+ lines)

**Features:**
- Standardized error responses
- Automatic logging
- HTTP status codes
- Error context
- Recovery suggestions

**Key Classes:**

```python
# Authentication
AuthenticationError             # 401
InvalidCredentialsError         # Wrong password
TokenExpiredError              # Token expired
EmailNotVerifiedError          # Email not verified

# Permissions
PermissionError                # 403
InsufficientPermissionsError   # Missing permissions
AdminOnlyError                 # Admin required
RateLimitExceededError         # 429

# Resources
ResourceNotFoundError          # 404
UserNotFoundError              # User missing
DuplicateError                 # 409
DuplicateEmailError            # Email exists

# Business Logic
BusinessLogicError             # 422
InvalidStateTransitionError    # Invalid state change
OperationNotAllowedError       # Not allowed now
InsufficientFundsError         # Not enough balance

# External Services
ExternalServiceError           # 502
PaymentProcessingError         # Payment failed
EmailServiceError              # Email service down

# Utilities
validate_or_raise()            # Conditional raise
validate_required_fields()     # Required field check
handle_exception()             # Convert any exception
```

**Usage:**

```python
from common.exceptions import (
    validate_or_raise,
    InvalidStateTransitionError,
    DuplicateEmailError,
)

# Conditional validation
validate_or_raise(
    user.is_verified,
    EmailNotVerifiedError,
    "Please verify your email first"
)

# State validation
validate_or_raise(
    current_status == "draft",
    InvalidStateTransitionError(current_status, "published"),
)

# Duplicate check
if User.objects.filter(email=email).exists():
    raise DuplicateEmailError()
```

---

### 6. `pagination.py` - Result Pagination (400+ lines)

**Features:**
- Multiple strategies (page, cursor, offset)
- Performance optimization
- Dynamic sizing
- Cache integration
- Progressive loading

**Key Classes:**

```python
# Page-based
StandardPagination              # 10 items/page
LargePagination                # 50 items/page
SmallPagination                # 5 items/page
DynamicPagination              # Adjust by device

# Cursor-based (performant)
StandardCursorPagination       # Cursor pagination
TimestampCursorPagination      # By created_at
IdCursorPagination             # By ID

# Offset-based
StandardLimitOffsetPagination  # Limit/offset

# Performance
OptimizedPagination            # With caching
NoCountPagination              # Skips count()
SearchPagination               # For search results
ProgressivePagination          # Progressive load
```

**Usage:**

```python
class ArticleViewSet(BaseViewSet):
    pagination_class = StandardPagination
    # Automatic pagination with page_size=10

# Query options
GET /api/articles/?page=2
GET /api/articles/?page_size=20
GET /api/articles/?cursor=abc123
GET /api/articles/?limit=50&offset=100
```

---

### 7. `filters.py` - Advanced Filtering (400+ lines)

**Features:**
- Multiple field types
- Range filtering
- Date filtering
- Search optimization
- Tag filtering
- Composite filters

**Key Classes:**

```python
# Field filters
CharInFilter                    # Multiple values
UUIDInFilter                    # Multiple UUIDs
DateRangeFilter                 # Date range
StatusFilter                    # Status values
VerifiedFilter                  # Verification status
ActiveFilter                    # Active status

# Composite
SearchableFilterSet             # Multi-field search
RangeFilter                     # Min/max values
RecentFilter                    # Last N days
PublishedFilter                 # Published/draft
AuthorFilter                    # By author
TagFilter                       # By tags
PriceRangeFilter               # Price range
RatingFilter                    # By rating
DeletedFilter                   # Include deleted

# Pre-built
StandardUserFilter              # User filtering
StandardContentFilter           # Content filtering
```

**Usage:**

```python
from common.filters import SearchableFilterSet

class ArticleFilter(SearchableFilterSet):
    search_fields = ['title', 'content', 'slug']
    
    class Meta:
        model = Article
        fields = ['status', 'author', 'created_at']

# Query
GET /api/articles/?search=django&status=published&author=john
GET /api/articles/?start_date=2024-01-01&end_date=2024-12-31
```

---

### 8. `helpers.py` - Utility Functions (500+ lines)

**Features:**
- Caching decorators
- Validation helpers
- String utilities
- Email templates
- File handling
- Token generation

**Key Functions:**

```python
# Caching
@cache_result(timeout=300)       # Cache result
@cache_per_request()             # Per-request cache
@retry_on_exception(max_retries=3)
@memoize                         # In-memory cache

# Validation
is_valid_email()                # Email format
is_valid_phone()                # Phone format
is_valid_url()                  # URL format
is_valid_ipv4()                 # IPv4 format
is_strong_password()            # Password strength

# String operations
truncate_string()               # Shorten text
camelcase_to_snakecase()        # Case conversion
generate_slug()                 # URL slugs
mask_email()                    # Privacy
mask_phone()                    # Privacy

# JSON
safe_json_loads()               # Safe parsing
safe_json_dumps()               # Safe serialization
deep_merge()                    # Merge dicts

# Email
send_template_email()           # Template emails
send_verification_email()       # Verification
send_password_reset_email()     # Password reset

# Utilities
generate_token()                # Random tokens
generate_code()                 # Random codes
chunk_list()                    # Split lists
format_file_size()              # Bytes to MB
```

**Usage:**

```python
from common.helpers import (
    cache_result,
    is_valid_email,
    send_verification_email,
    generate_token,
)

@cache_result(timeout=3600)
def get_popular_articles():
    return Article.objects.filter(view_count__gte=100)

# Email
send_verification_email(
    user=user,
    token=generate_token(),
    base_url="https://example.com"
)

# Validation
if not is_valid_email(email):
    raise InvalidEmailError()
```

---

### 9. `constants.py` - Enums & Constants (400+ lines)

**Features:**
- Status enums
- Choice fields
- Error codes
- Config constants
- Message templates

**Key Enums:**

```python
# Status
StatusChoice                    # Draft/Published/Archived
UserStatusChoice                # Active/Inactive/Suspended
PaymentStatusChoice             # Pending/Completed/Failed
OrderStatusChoice               # Pending/Shipped/Delivered
SubscriptionStatusChoice        # Active/Paused/Cancelled

# Other
PriorityChoice                  # Low/Medium/High/Critical
UserRoleChoice                  # Admin/Moderator/User
NotificationTypeChoice          # Email/SMS/Push
HTTPStatusChoice                # 200/400/500 etc.

# Configs
CacheConfig                     # Timeout values
ValidationConfig                # Min/max lengths
PaginationConfig                # Page sizes
FileConfig                      # File limits
RateLimitConfig                 # Request limits

# Utilities
get_status_display()            # Readable status
get_choice_label()              # Label from choice
```

**Usage:**

```python
from common.constants import StatusChoice, CacheConfig

class Article(models.Model):
    status = models.CharField(
        max_length=20,
        choices=StatusChoice.choices(),
        default=StatusChoice.DRAFT
    )

# Cache timeout
from django.core.cache import cache
cache.set('key', value, CacheConfig.TIMEOUT_LONG)  # 1 hour
```

---

### 10. `middleware.py` - HTTP Processing (500+ lines)

**Features:**
- Request/response logging
- Performance monitoring
- Security headers
- Rate limiting
- Error tracking
- CORS handling
- Timezone support

**Key Classes:**

```python
# Logging
RequestLoggingMiddleware        # Log all requests
PerformanceMonitoringMiddleware # Monitor response time
AuditLoggingMiddleware          # Audit trail

# Security
SecurityHeadersMiddleware       # Add security headers
RateLimitMiddleware             # Rate limiting
CORSMiddleware                  # CORS handling

# Enhancement
RequestEnhancementMiddleware    # Add metadata
TimezoneMiddleware              # Timezone support
CacheControlMiddleware          # Cache headers
APIVersionHeaderMiddleware      # API version

# Error handling
ErrorHandlingMiddleware         # Exception logging
```

**Usage:**

```python
# settings/base.py
MIDDLEWARE = [
    # ... Django middleware ...
    'common.middleware.RequestLoggingMiddleware',
    'common.middleware.PerformanceMonitoringMiddleware',
    'common.middleware.SecurityHeadersMiddleware',
    'common.middleware.RateLimitMiddleware',
]
```

---

### 11. `admin.py` - Django Admin (400+ lines)

**Features:**
- Enhanced display
- Bulk actions
- Soft delete management
- Publishing workflows
- Audit logging
- Permission checks

**Key Classes:**

```python
# Base
BaseModelAdmin                  # Core admin features
SoftDeleteModelAdmin            # Soft delete management
PublishableModelAdmin           # Publish/unpublish actions

# Specific
CustomUserAdmin                 # User management
AuditLogAdmin                   # Audit trail view
```

**Usage:**

```python
from common.admin import PublishableModelAdmin

@admin.register(Article)
class ArticleAdmin(PublishableModelAdmin):
    list_display = ['title', 'status', 'author']
    search_fields = ['title', 'content']
    
    # Automatically get:
    # - Publish/unpublish actions
    # - Status display with colors
    # - Audit logging
    # - Permission checks
```

---

## Quick Start

### 1. Copy Components to Your Project

```bash
cp -r common/ /path/to/your/django/project/
```

### 2. Register in `settings.py`

```python
INSTALLED_APPS = [
    # ...
    'accounts',
    'common',
    'api',
]

AUTH_USER_MODEL = 'accounts.CustomUser'

MIDDLEWARE = [
    # ... Django middleware ...
    'common.middleware.RequestLoggingMiddleware',
    'common.middleware.PerformanceMonitoringMiddleware',
]
```

### 3. Update Models

```python
# accounts/models.py
from common.models import CustomUser

# Already registered in admin

# api/models.py
from common.models import SoftDeleteModel, PublishableModel

class Article(SoftDeleteModel, PublishableModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
```

### 4. Create Serializers

```python
# api/serializers.py
from common.serializers import TimestampedSerializer

class ArticleSerializer(TimestampedSerializer):
    class Meta:
        model = Article
        fields = '__all__'
```

### 5. Create ViewSets

```python
# api/viewsets.py
from common.viewsets import SoftDeleteViewSet

class ArticleViewSet(SoftDeleteViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

### 6. Create Admin

```python
# api/admin.py
from common.admin import PublishableModelAdmin

@admin.register(Article)
class ArticleAdmin(PublishableModelAdmin):
    pass
```

---

## Usage Examples

### Example 1: Creating a Complete API

```python
# models.py
from common.models import SoftDeleteModel, PublishableModel, CustomUser

class BlogPost(SoftDeleteModel, PublishableModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    slug = models.SlugField(unique=True)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    tags = models.ManyToManyField('Tag')
    view_count = models.PositiveIntegerField(default=0)

# serializers.py
from common.serializers import TimestampedSerializer, DynamicFieldsSerializer

class BlogPostSerializer(DynamicFieldsSerializer, TimestampedSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    tags = serializers.StringRelatedField(many=True)
    
    class Meta:
        model = BlogPost
        fields = ['id', 'title', 'content', 'slug', 'author', 'author_name', 
                 'tags', 'status', 'view_count', 'created_at', 'updated_at']

# viewsets.py
from common.viewsets import SoftDeleteViewSet
from common.filters import SearchableFilterSet
from common.permissions import IsOwnerOrReadOnly

class BlogPostFilter(SearchableFilterSet):
    search_fields = ['title', 'content', 'slug']
    
    class Meta:
        model = BlogPost
        fields = ['status', 'author']

class BlogPostViewSet(SoftDeleteViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    filterset_class = BlogPostFilter
    permission_classes = [IsOwnerOrReadOnly]
    search_fields = ['title', 'content', 'slug']
    ordering_fields = ['-created_at', 'title']

# Results:
# - Full CRUD ✓
# - Soft delete ✓
# - Publishing ✓
# - Search/filter ✓
# - Ownership ✓
# - Audit logging ✓
# - Caching ready ✓
```

### Example 2: User Management

```python
# viewsets.py
from common.viewsets import UserViewSet as BaseUserViewSet
from accounts.serializers import UserDetailSerializer

class UserViewSet(BaseUserViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserDetailSerializer

# Automatically includes:
# - /register/ - user registration
# - /me/ - current user
# - /change_password/ - password change
# - /active/ - active users
# - /verified/ - verified users
# - Full search/filter
```

### Example 3: Advanced Filtering

```python
from common.filters import SearchableFilterSet, RangeFilter, DateRangeFilter

class ProductFilter(SearchableFilterSet):
    search_fields = ['name', 'description', 'sku']
    
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')
    
    class Meta:
        model = Product
        fields = ['status', 'category', 'price_min', 'price_max']

# Usage:
# GET /api/products/?search=laptop&price_min=500&price_max=1500&status=published
```

---

## Performance Tips

### 1. Query Optimization

```python
class ArticleViewSet(SoftDeleteViewSet):
    select_related_fields = ['author', 'category']
    prefetch_related_fields = ['tags', 'comments']
    
    # Automatically optimized with select_related/prefetch_related
```

### 2. Caching

```python
from common.helpers import cache_result

@cache_result(timeout=3600)  # 1 hour
def get_popular_articles():
    return Article.objects.filter(view_count__gte=100)

# Or per-request
from common.helpers import cache_per_request

@cache_per_request()
def get_current_user(self, request):
    return request.user
```

### 3. Pagination

```python
from common.pagination import NoCountPagination

class ArticleViewSet(SoftDeleteViewSet):
    pagination_class = NoCountPagination  # Skips expensive count()
    
    # Much faster for large datasets
```

### 4. Cursor Pagination

```python
from common.pagination import TimestampCursorPagination

class ArticleViewSet(SoftDeleteViewSet):
    pagination_class = TimestampCursorPagination  # Best for large datasets
    
    # Pagination via cursor instead of offset
```

---

## Error Handling

### Automatic Error Response Format

```python
from common.exceptions import (
    ValidationError,
    AuthenticationError,
    PermissionError,
    ResourceNotFoundError,
)

# All exceptions return consistent format:
{
    "error": {
        "code": "validation_error",
        "message": "Invalid email format",
        "status": 400
    },
    "context": {
        "field": "email",
        "value": "invalid"
    }
}
```

### Validation in ViewSets

```python
from common.exceptions import validate_or_raise, InvalidStateTransitionError

def perform_update(self, serializer):
    obj = serializer.instance
    
    # Validate state transition
    validate_or_raise(
        obj.status == 'draft',
        InvalidStateTransitionError('draft', 'published'),
        context={'current_status': obj.status}
    )
    
    super().perform_update(serializer)
```

---

## Testing

```python
from django.test import TestCase
from rest_framework.test import APIClient
from common.models import CustomUser

class ArticleAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_article(self):
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/articles/', {
            'title': 'Test',
            'content': 'Content',
        })
        
        assert response.status_code == 201
        assert Article.objects.count() == 1
    
    def test_soft_delete(self):
        article = Article.objects.create(
            title='Test',
            author=self.user
        )
        
        article.delete()
        
        assert article.is_deleted
        assert Article.objects.active().count() == 0
        assert Article.objects.deleted().count() == 1
```

---

## Best Practices

### 1. Use Inheritance Properly

```python
# ✓ Good: Compose multiple features
class Article(SoftDeleteModel, PublishableModel, ViewableModel):
    pass

# ✗ Bad: Over-inheritance
class Article(SoftDeleteModel, PublishableModel, ViewableModel, 
              RateableModel, SEOModel, ChangeTrackingModel):
    pass  # Pick what you need
```

### 2. Proper Permissions

```python
# ✓ Good: Clear, granular
class ArticleViewSet(BaseViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

# ✗ Bad: Too permissive
class ArticleViewSet(BaseViewSet):
    permission_classes = [AllowAny]
```

### 3. Audit Logging

```python
# ✓ Good: Let viewsets handle it
class ArticleViewSet(BaseViewSet):
    # Automatic logging of all CRUD operations
    pass

# ✗ Bad: Duplicate logging
def create(self, request, *args, **kwargs):
    # Manual logging + BaseViewSet logging
    logger.info("Creating...")
    return super().create(request, *args, **kwargs)
```

### 4. Cache Strategically

```python
# ✓ Good: Cache expensive operations
@cache_result(timeout=3600)
def get_popular_items():
    return ExpensiveQuery()

# ✗ Bad: Cache frequently changing data
@cache_result(timeout=3600)
def get_current_user():  # Never stays the same!
    return request.user
```

---

## Summary

| Component | Lines | Key Features |
|-----------|-------|--------------|
| models.py | 850 | UUID, soft delete, audit, change tracking |
| serializers.py | 600 | Dynamic fields, bulk ops, validation |
| viewsets.py | 700 | CRUD, soft delete, publishing, ratings |
| permissions.py | 500 | RBAC, ownership, custom rules |
| exceptions.py | 400 | 20+ exception types, logging |
| pagination.py | 400 | Multiple strategies, caching, performance |
| filters.py | 400 | Advanced filtering, search, composable |
| helpers.py | 500 | Caching, validation, email, tokens |
| constants.py | 400 | Enums, configs, error codes |
| middleware.py | 500 | Logging, monitoring, security, rate limit |
| admin.py | 400 | Enhanced admin, bulk actions |
| **TOTAL** | **5,650** | **Production-ready, fully typed** |

---

## Dependencies

```
Django==5.2.11
djangorestframework==3.16.1
django-filter==24.3
django-cors-headers==4.4.0
django-redis==5.4.0
django-unfold==0.42.0
drf-spectacular==0.29.0
djangorestframework_simplejwt==5.4.0
```

---

**Created:** February 2025  
**Version:** 1.0.0  