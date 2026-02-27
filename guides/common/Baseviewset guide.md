# Django REST Framework BaseViewSet Guide

**A comprehensive guide to understanding and using the production-grade BaseViewSetMixin and BaseViewSet**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Error Handling](#error-handling)
4. [Hooks & Lifecycle](#hooks--lifecycle)
5. [Common Patterns](#common-patterns)
6. [Advanced Features](#advanced-features)
7. [Best Practices](#best-practices)
8. [Examples](#examples)

---

## Overview

The **BaseViewSetMixin** provides centralized, production-grade error handling and lifecycle hooks. The **BaseViewSet** builds on top of it, adding filtering, permissions, soft deletes, publishing, ratings, and bulk operations.

### Why Use It?

- **Consistent error responses** across your entire API
- **Automatic error mapping** from Django/DRF exceptions
- **Lifecycle hooks** for custom logic before/after CRUD operations
- **Safe database error handling** (no SQL leaks)
- **Built-in request/response logging**
- **Request/response validation** via contextmanagers
- **Audit logging** for compliance
- **Soft delete support**
- **Dynamic permissions** based on action
- **Bulk operations**

### Quick Start

```python
from rest_framework import viewsets
from .mixins import BaseViewSetMixin
from .serializers import ArticleSerializer
from .models import Article

class ArticleViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

That's it. You now have:
- Unified error handling
- Audit logging
- Performance hooks
- Request logging (optional)

---

## Architecture

### The Inheritance Chain

```python
class ArticleViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    pass
```

**MRO (Method Resolution Order) matters:**

```
ArticleViewSet
  ↓
BaseViewSetMixin          ← Error handling, hooks, logging
  ↓
ModelViewSet             ← list, retrieve, create, update, destroy
  ↓
ViewSetMixin            ← Basic viewset functionality
```

**Why BaseViewSetMixin first?** It overrides `handle_exception()` so all exceptions flow through its sophisticated error mapper before reaching DRF's default handler.

### Two-Layer Design

| Layer | Responsibility |
|-------|-----------------|
| **BaseViewSetMixin** | Error handling, lifecycle hooks, logging, safe queryset access |
| **BaseViewSet** | Filtering, permissions, audit logging, soft deletes, publishing, bulk ops |

Both work together, but you can use just the mixin if you only need error handling.

---

## Error Handling

### How It Works

All exceptions raised in your viewset flow through `handle_exception()`:

```
Exception raised
    ↓
handle_exception()
    ↓
Map to specific error code
    ↓
Return standardized JSON response
    ↓
Log with appropriate level (debug, warning, critical)
```

### Error Response Format

Every error returns this structure:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input.",
    "details": {
      "email": ["This field is required."]
    }
  }
}
```

### Exception Mapping

#### DRF Exceptions (Handled Automatically)

| Exception | Status | Code |
|-----------|--------|------|
| `DRFValidationError` | 400 | `validation_error` |
| `ParseError` | 400 | `parse_error` |
| `NotAuthenticated` | 401 | `authentication_error` |
| `AuthenticationFailed` | 401 | `authentication_error` |
| `DRFPermissionDenied` | 403 | `permission_denied` |
| `NotFound` | 404 | `not_found` |
| `MethodNotAllowed` | 405 | `method_not_allowed` |
| `Throttled` | 429 | `throttled` |

#### Django Exceptions (Handled Automatically)

| Exception | Status | Code |
|-----------|--------|------|
| `Http404` | 404 | `not_found` |
| `ObjectDoesNotExist` | 404 | `not_found` |
| `PermissionDenied` | 403 | `permission_denied` |
| `ValidationError` | 400 | `validation_error` |

#### Database Exceptions (Handled Automatically)

| Exception | Status | Code |
|-----------|--------|------|
| `IntegrityError` | 409 | `integrity_error` |
| `ProtectedError` | 409 | `protected_object` |
| `RestrictedError` | 409 | `protected_object` |
| `DataError` | 400 | `data_error` |
| `OperationalError` | 503 | `db_operational_error` |
| `ProgrammingError` | 500 | `db_error` |

#### Unhandled Exceptions

Anything else returns a generic 500 error and logs with `exc_info=True`.

### Safe Database Error Handling

**Problem:** Database errors can leak SQL details.

**Solution:** Use `SAFE_DB_ERRORS = True` (default):

```python
# With SAFE_DB_ERRORS = True (safe)
IntegrityError → "A database integrity constraint was violated."

# With SAFE_DB_ERRORS = False (debug only)
IntegrityError → "UNIQUE constraint failed: users.email"
```

Set it per viewset:

```python
class ArticleViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    SAFE_DB_ERRORS = False  # Only for local development
```

---

## Hooks & Lifecycle

### Create Lifecycle

```python
def create(self, request, *args, **kwargs):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    self.perform_create(serializer)  # → Your hooks called here
    return Response(serializer.data, status=201)
```

**Hook Order:**

1. `before_perform_create(serializer)` — Before save
2. `serializer.save(**get_create_kwargs())` — Save to DB
3. `after_perform_create(instance, serializer)` — After save

**Override any of these:**

```python
class ArticleViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_create_kwargs(self, serializer):
        """Add owner to new articles"""
        return {"owner": self.request.user}

    def before_perform_create(self, serializer):
        """Validate business logic before save"""
        if self.request.user.articles.count() >= 10:
            raise ValidationError("Cannot create more than 10 articles")

    def after_perform_create(self, instance, serializer):
        """Send notification after save"""
        send_email_notification(instance.owner, instance)
```

### Update Lifecycle

```python
def update(self, request, *args, **kwargs):
    instance = self.get_object()
    serializer = self.get_serializer(instance, data=request.data)
    serializer.is_valid(raise_exception=True)
    self.perform_update(serializer)  # → Your hooks called here
    return Response(serializer.data)
```

**Hook Order:**

1. `before_perform_update(serializer)` — Before save
2. `serializer.save(**get_update_kwargs())` — Save to DB
3. `after_perform_update(instance, serializer)` — After save

```python
def before_perform_update(self, serializer):
    """Prevent certain updates"""
    instance = serializer.instance
    if instance.is_published and "status" in serializer.validated_data:
        raise PermissionDenied("Cannot change status of published articles")

def after_perform_update(self, instance, serializer):
    """Cache invalidation"""
    cache.delete(f"article:{instance.id}")
```

### Delete Lifecycle

```python
def destroy(self, request, *args, **kwargs):
    instance = self.get_object()
    self.perform_destroy(instance)  # → Your hooks called here
    return Response(status=204)
```

**Hook Order:**

1. `before_perform_destroy(instance)` — Before delete
2. `instance.delete()` — Delete from DB
3. `after_perform_destroy(instance)` — After delete

```python
def before_perform_destroy(self, instance):
    """Prevent deletion of published articles"""
    if instance.is_published:
        raise PermissionDenied("Cannot delete published articles")

def after_perform_destroy(self, instance):
    """Cleanup associated files"""
    for attachment in instance.attachments.all():
        attachment.file.delete()
```

### List Lifecycle

```python
def filter_queryset(self, queryset):
    queryset = self.before_perform_list(queryset)
    queryset = super().filter_queryset(queryset)  # Apply filters
    queryset = self.after_perform_list(queryset)  # Post-process
    return queryset
```

**Hook Order:**

1. `before_perform_list(queryset)` — Before filtering
2. Standard filtering applied
3. `after_perform_list(queryset)` — After filtering

```python
def before_perform_list(self, queryset):
    """Filter by user"""
    return queryset.filter(owner=self.request.user)

def after_perform_list(self, queryset):
    """Optimize queries"""
    return queryset.select_related('owner').prefetch_related('tags')
```

### Retrieve Lifecycle

```python
def retrieve(self, request, *args, **kwargs):
    instance = self.get_object()
    self.before_perform_retrieve(instance)
    serializer = self.get_serializer(instance)
    self.after_perform_retrieve(instance)
    return Response(serializer.data)
```

**Hook Order:**

1. `before_perform_retrieve(instance)` — After get_object()
2. Serialization
3. `after_perform_retrieve(instance)` — Before response

```python
def before_perform_retrieve(self, instance):
    """Increment view count"""
    instance.views += 1
    instance.save(update_fields=['views'])

def after_perform_retrieve(self, instance):
    """Log access"""
    logger.info(f"Article {instance.id} viewed by {self.request.user.id}")
```

---

## Common Patterns

### Pattern 1: Automatic User Assignment

Attach the current user to new objects:

```python
class ArticleViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_create_kwargs(self, serializer):
        return {"owner": self.request.user}
```

### Pattern 2: Soft Deletes

Prevent hard deletes in favor of soft deletes:

```python
def before_perform_destroy(self, instance):
    """Use soft delete instead"""
    if hasattr(instance, 'soft_delete'):
        instance.soft_delete()
        raise DjangoValidationError("Object marked as deleted")
```

Or use the built-in `SoftDeleteViewSet`:

```python
class ArticleViewSet(SoftDeleteViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

### Pattern 3: Audit Trail

Log all modifications:

```python
def after_perform_create(self, instance, serializer):
    AuditLog.objects.create(
        user=self.request.user,
        action='create',
        model='Article',
        object_id=instance.id
    )

def after_perform_update(self, instance, serializer):
    AuditLog.objects.create(
        user=self.request.user,
        action='update',
        model='Article',
        object_id=instance.id,
        changes=serializer.validated_data
    )
```

### Pattern 4: Cache Invalidation

Clear cache after modifications:

```python
def after_perform_update(self, instance, serializer):
    cache.delete(f"article:{instance.id}")
    cache.delete("articles:list")  # Invalidate list cache

def after_perform_destroy(self, instance):
    cache.delete(f"article:{instance.id}")
    cache.delete("articles:list")
```

### Pattern 5: Validation Before Save

Check business logic constraints:

```python
def before_perform_create(self, serializer):
    user = self.request.user
    if Article.objects.filter(owner=user, status='draft').count() >= 5:
        raise ValidationError({
            'draft_limit': 'You can have at most 5 draft articles'
        })
```

**Note:** For permission checking, use the `@check_permissions` decorator from helpers instead.

### Pattern 6: Dynamic Serializer Selection

Use different serializers per action:

```python
class ArticleViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleDetailSerializer
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        elif self.action == 'create':
            return ArticleCreateSerializer
        return self.serializer_class
```

### Pattern 7: Query Optimization

Optimize queries per action:

```python
def get_queryset(self):
    queryset = super().get_queryset()
    if self.action == 'list':
        return queryset.select_related('owner').prefetch_related('tags')
    elif self.action == 'retrieve':
        return queryset.select_related('owner').prefetch_related('comments')
    return queryset
```

### Pattern 8: Error Boundary for Custom Actions

Use error_boundary() in @action methods:

```python
@action(detail=True, methods=['post'])
def publish(self, request, pk=None):
    with self.error_boundary():
        article = self.get_object()
        if not article.can_publish():
            raise ValidationError("Article not ready to publish")
        article.publish()
        return self.success_response(
            data=ArticleSerializer(article).data,
            message="Article published successfully"
        )
```

---

## Advanced Features

### BaseViewSet Extra Features

Beyond the mixin, `BaseViewSet` adds:

#### 1. Soft Deletes

Use `SoftDeleteViewSet` for soft-delete support:

```python
class ArticleViewSet(SoftDeleteViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

**Available endpoints:**
- `GET /articles/deleted/` — View soft-deleted articles (staff only)
- `POST /articles/{id}/restore/` — Restore a soft-deleted article
- `POST /articles/bulk_restore/` — Restore multiple articles (staff only)

#### 2. Publishing

Use `PublishableViewSet` for publish/unpublish:

```python
class ArticleViewSet(PublishableViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

**Available endpoints:**
- `POST /articles/{id}/publish/` — Publish an article
- `POST /articles/{id}/unpublish/` — Unpublish an article
- `GET /articles/published/` — Get only published articles

#### 3. Ratings

Use `RatableViewSet` for rating support:

```python
class ProductViewSet(RatableViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
```

**Available endpoints:**
- `POST /products/{id}/rate/` — Rate a product
  ```json
  {"rating": 4.5}
  ```

#### 4. Bulk Operations

Use `BulkOperationViewSet` for bulk CRUD:

```python
class ArticleViewSet(BulkOperationViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

**Available endpoints:**
- `POST /articles/bulk_create/` — Create multiple articles
- `PATCH /articles/bulk_update/` — Update multiple articles
- `DELETE /articles/bulk_delete/` — Delete multiple articles

**Examples:**

```bash
# Bulk create
curl -X POST /articles/bulk_create/ \
  -d '[
    {"title": "Article 1", "content": "..."},
    {"title": "Article 2", "content": "..."}
  ]'

# Bulk update
curl -X PATCH /articles/bulk_update/ \
  -d '[
    {"id": 1, "status": "published"},
    {"id": 2, "status": "draft"}
  ]'

# Bulk delete
curl -X DELETE /articles/bulk_delete/ \
  -d '{"ids": [1, 2, 3]}'
```

#### 5. Advanced Filtering

Dynamic filtering, searching, and ordering:

```python
class ArticleViewSet(BaseViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    
    # Enable Django Filter
    filterset_fields = ['status', 'owner', 'created_at']
    
    # Enable full-text search
    search_fields = ['title', 'content', 'owner__username']
    
    # Enable ordering
    ordering_fields = ['created_at', 'updated_at', 'title']
```

**Usage:**

```bash
# Filter
curl /articles/?status=published&owner=1

# Search
curl /articles/?search=django

# Order
curl /articles/?ordering=-created_at
```

#### 6. Permission Handling

Dynamic permissions per action:

```python
class ArticleViewSet(BaseViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    
    def get_permissions(self):
        """
        - Anyone can list/retrieve
        - Must be authenticated to create/update
        - Must be staff to delete
        """
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAuthenticated()]
        elif self.action == 'destroy':
            return [IsAuthenticated(), IsAdminUser()]
        return [AllowAny()]
```

### Request/Response Logging

Enable logging for debugging:

```python
class ArticleViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    LOG_REQUESTS = True  # Enable request/response logging
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

**Output:**

```
→ POST /articles/ | user=123 | data={'title': '...'}
← POST /articles/ | status=201
```

### Success Response Helper

Consistent success responses:

```python
@action(detail=True, methods=['post'])
def publish(self, request, pk=None):
    article = self.get_object()
    article.status = 'published'
    article.save()
    
    return self.success_response(
        data=ArticleSerializer(article).data,
        message="Article published successfully",
        status_code=status.HTTP_200_OK
    )
```

**Output:**

```json
{
  "message": "Article published successfully",
  "data": {
    "id": 1,
    "title": "...",
    ...
  }
}
```

---

## Best Practices

### 1. Always Use get_create_kwargs / get_update_kwargs

```python
# ✅ Good
def get_create_kwargs(self, serializer):
    return {"owner": self.request.user}

# ❌ Don't do this
def perform_create(self, serializer):
    serializer.save(owner=self.request.user)
```

The hook approach is cleaner and more intentional.

### 2. Use Validation in before_perform_* Hooks

```python
# ✅ Good - fails early before DB hit
def before_perform_create(self, serializer):
    if not self.request.user.can_create_articles():
        raise PermissionDenied("Not allowed")

# ❌ Risky - validation at DB level
def perform_create(self, serializer):
    serializer.save()
```

### 3. Keep Hooks Focused

```python
# ✅ Good - one responsibility
def after_perform_create(self, instance, serializer):
    send_notification(instance.owner)

# ❌ Bad - too many responsibilities
def after_perform_create(self, instance, serializer):
    send_notification(instance.owner)
    update_analytics(instance)
    invalidate_caches()
    log_to_external_service()
```

### 4. Always Wrap External Service Calls

```python
# ✅ Good - errors don't break the response
def after_perform_create(self, instance, serializer):
    try:
        send_notification(instance.owner)
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        # Don't re-raise - user still got their data

# ❌ Bad - external service failure breaks the API
def after_perform_create(self, instance, serializer):
    send_notification(instance.owner)  # If this fails, 500 error
```

### 5. Use error_boundary() for Custom Actions

```python
# ✅ Good - errors are caught and formatted
@action(detail=True, methods=['post'])
def publish(self, request, pk=None):
    with self.error_boundary():
        article = self.get_object()
        article.publish()
        return Response({"status": "published"})

# ❌ Bad - errors won't be formatted
@action(detail=True, methods=['post'])
def publish(self, request, pk=None):
    article = self.get_object()
    article.publish()
    return Response({"status": "published"})
```

### 6. Use select_related / prefetch_related

```python
# ✅ Good - optimized queries
def get_queryset(self):
    queryset = super().get_queryset()
    if self.action == 'retrieve':
        return queryset.select_related('owner')
    return queryset

# ❌ Bad - N+1 queries
def get_queryset(self):
    return super().get_queryset()
```

### 7. Don't Override handle_exception Lightly

The mixin's `handle_exception()` is comprehensive. Only override if you need custom behavior:

```python
# ✅ Good - extend the base behavior
def handle_exception(self, exc):
    if isinstance(exc, CustomError):
        return _error_response(...)
    return super().handle_exception(exc)

# ❌ Bad - breaks error handling
def handle_exception(self, exc):
    return Response({"error": str(exc)})
```

### 8. Use Transactions for Multi-Step Operations

```python
# ✅ Good - all-or-nothing
from django.db import transaction

@transaction.atomic
def perform_create(self, serializer):
    instance = serializer.save(**self.get_create_kwargs(serializer))
    # Any error here rolls back the whole transaction
    self.after_perform_create(instance, serializer)

# ❌ Risky - partial updates if error occurs
def perform_create(self, serializer):
    instance = serializer.save(**self.get_create_kwargs(serializer))
    self.after_perform_create(instance, serializer)
```

---

## Examples

### Example 1: Blog Article Viewset

```python
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .mixins import BaseViewSetMixin
from .models import Article
from .serializers import ArticleSerializer, ArticleDetailSerializer

class ArticleViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    """Complete article management with soft deletes and publishing"""
    
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    LOG_REQUESTS = True  # Debug mode
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ArticleDetailSerializer
        return self.serializer_class
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Staff can see all articles
        if self.request.user.is_staff:
            return queryset
        
        # Regular users see only their published articles + their drafts
        if self.request.user.is_authenticated:
            return queryset.filter(
                models.Q(owner=self.request.user) | 
                models.Q(status='published')
            )
        
        # Anonymous users see only published
        return queryset.filter(status='published')
    
    def get_create_kwargs(self, serializer):
        return {"owner": self.request.user}
    
    def before_perform_create(self, serializer):
        """Validate article creation constraints"""
        user = self.request.user
        draft_count = Article.objects.filter(
            owner=user, 
            status='draft'
        ).count()
        
        if draft_count >= 5:
            raise ValidationError({
                'draft_limit': 'Max 5 draft articles per user'
            })
    
    def after_perform_create(self, instance, serializer):
        """Send notification after creation"""
        try:
            send_article_created_email(instance.owner, instance)
        except Exception as e:
            logger.error(f"Email failed: {e}")
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish an article"""
        with self.error_boundary():
            article = self.get_object()
            
            if article.status == 'published':
                raise ValidationError("Already published")
            
            article.status = 'published'
            article.published_at = now()
            article.save()
            
            return self.success_response(
                data=ArticleDetailSerializer(article).data,
                message="Article published successfully"
            )
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Soft delete an article"""
        with self.error_boundary():
            article = self.get_object()
            
            # Only owner or staff can archive
            if article.owner != request.user and not request.user.is_staff:
                raise PermissionDenied("Cannot archive this article")
            
            article.is_archived = True
            article.save()
            
            return self.success_response(
                message="Article archived successfully"
            )
```

### Example 2: User Management Viewset

```python
class UserViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    """Complete user management with audit logging"""
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'username']
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        elif self.action in ['update', 'partial_update']:
            return [IsAuthenticated()]
        elif self.action == 'destroy':
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    def before_perform_create(self, serializer):
        """Validate email uniqueness with custom message"""
        email = serializer.validated_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError({
                'email': 'This email is already registered'
            })
    
    def after_perform_create(self, instance, serializer):
        """Log user creation"""
        AuditLog.objects.create(
            user=instance,
            action='created',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        send_welcome_email(instance)
    
    def after_perform_update(self, instance, serializer):
        """Log user updates"""
        AuditLog.objects.create(
            user=instance,
            action='updated',
            changes=list(serializer.validated_data.keys()),
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
    
    def after_perform_destroy(self, instance):
        """Log user deletion"""
        AuditLog.objects.create(
            user=instance,
            action='deleted',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Change user password"""
        with self.error_boundary():
            user = self.get_object()
            
            if user != request.user and not request.user.is_staff:
                raise PermissionDenied("Cannot change another user's password")
            
            old_password = request.data.get('old_password')
            new_password = request.data.get('new_password')
            
            if not user.check_password(old_password):
                raise ValidationError({'old_password': 'Incorrect'})
            
            user.set_password(new_password)
            user.save()
            
            return self.success_response(
                message="Password changed successfully"
            )
```

### Example 3: Product with Bulk Operations

```python
class ProductViewSet(BulkOperationViewSet):
    """Product management with bulk operations and ratings"""
    
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_fields = ['category', 'status', 'price']
    search_fields = ['name', 'description', 'sku']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by price range if provided
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        return queryset
    
    def before_perform_create(self, serializer):
        """Validate SKU uniqueness"""
        sku = serializer.validated_data.get('sku')
        if Product.objects.filter(sku=sku).exists():
            raise ValidationError({'sku': 'SKU must be unique'})
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Rate a product"""
        with self.error_boundary():
            product = self.get_object()
            rating = request.data.get('rating')
            comment = request.data.get('comment', '')
            
            if not rating or not (1 <= float(rating) <= 5):
                raise ValidationError({'rating': 'Rating must be 1-5'})
            
            Review.objects.create(
                product=product,
                user=request.user,
                rating=float(rating),
                comment=comment
            )
            
            # Update product average rating
            avg_rating = product.reviews.aggregate(
                avg=Avg('rating')
            )['avg']
            product.average_rating = avg_rating
            product.save(update_fields=['average_rating'])
            
            return self.success_response(
                message="Rating submitted successfully",
                data={'average_rating': product.average_rating}
            )
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def bulk_create_from_csv(self, request):
        """Create products from CSV upload"""
        csv_file = request.FILES.get('file')
        if not csv_file:
            raise ValidationError({'file': 'CSV file required'})
        
        import csv
        reader = csv.DictReader(csv_file)
        products = []
        
        for row in reader:
            products.append(Product(
                name=row['name'],
                sku=row['sku'],
                price=row['price'],
                category_id=row['category_id']
            ))
        
        created = Product.objects.bulk_create(products)
        
        return self.success_response(
            message=f"Created {len(created)} products",
            data={'count': len(created)},
            status_code=status.HTTP_201_CREATED
        )
```

---

## Troubleshooting

### Problem: Errors not being caught

**Check:** Are you using `error_boundary()`?

```python
# ✅ Correct
@action(detail=True, methods=['post'])
def custom_action(self, request, pk=None):
    with self.error_boundary():
        # Your code here
```

### Problem: N+1 queries in list endpoint

**Check:** Are you optimizing the queryset?

```python
# ✅ Correct
def get_queryset(self):
    queryset = super().get_queryset()
    if self.action == 'list':
        return queryset.select_related('owner').prefetch_related('tags')
    return queryset
```

### Problem: Database errors leaking SQL

**Check:** Is `SAFE_DB_ERRORS = True`?

```python
class MyViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    SAFE_DB_ERRORS = True  # Default, but verify
```

### Problem: Permissions not working

**Check:** Are you overriding `get_permissions()`?

```python
# ✅ Correct
def get_permissions(self):
    if self.action in ['create', 'update']:
        return [IsAuthenticated()]
    return [AllowAny()]
```

### Problem: Custom action not seeing hooks

**Check:** Are you calling `perform_*` methods?

```python
# ❌ Wrong - doesn't call hooks
@action(detail=True, methods=['post'])
def custom(self, request, pk=None):
    instance = self.get_object()
    instance.do_something()
    instance.save()

# ✅ Right - uses hooks
@action(detail=True, methods=['post'])
def custom(self, request, pk=None):
    with self.error_boundary():
        instance = self.get_object()
        instance.do_something()
        instance.save()
```

---

## Summary

| Feature | What It Does |
|---------|--------------|
| **BaseViewSetMixin** | Centralized error handling, lifecycle hooks, logging |
| **BaseViewSet** | Everything above + filtering, permissions, soft deletes, publishing, ratings, bulk ops |
| **error_boundary()** | Catch exceptions in custom @action methods |
| **Hooks** | `before_perform_*` / `after_perform_*` for custom logic |
| **get_*_kwargs()** | Extra arguments to `serializer.save()` |
| **LOG_REQUESTS** | Enable request/response logging for debugging |
| **success_response()** | Standardized success envelope |

Use these patterns in combination to build production-grade APIs with minimal boilerplate.

---

## Questions?

If you have questions, refer back to:
1. **Error Handling** section for exception mapping
2. **Hooks & Lifecycle** section for CRUD hooks
3. **Common Patterns** section for real-world examples
4. **Examples** section for complete viewsets