# Django REST Framework Permissions Guide

**A comprehensive guide to implementing production-grade permission classes**

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication Permissions](#authentication-permissions)
3. [Role-Based Permissions](#role-based-permissions)
4. [Ownership Permissions](#ownership-permissions)
5. [HTTP Method Permissions](#http-method-permissions)
6. [Complex Permissions](#complex-permissions)
7. [Rate Limiting](#rate-limiting)
8. [Custom Permission Rules](#custom-permission-rules)
9. [Permission Factories](#permission-factories)
10. [Best Practices](#best-practices)

---

## Overview

DRF permissions determine whether a request should be granted or denied access. They provide fine-grained access control for your API.

### Permission Flow

```
Request → Authentication → Permissions → View
```

### Permission Types

- **View-level**: `has_permission()` - Check before view executes
- **Object-level**: `has_object_permission()` - Check on specific object

### Quick Start

```python
from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

# Usage in ViewSet
class ArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwner]
```

---

## Authentication Permissions

### IsAuthenticated

```python
class IsAuthenticated(BasePermission):
    """User must be authenticated"""
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
```

**Usage:**

```python
class ArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
```

### IsAnonymous

```python
class IsAnonymous(BasePermission):
    """User must NOT be authenticated"""
    
    def has_permission(self, request, view):
        return not request.user or not request.user.is_authenticated
```

**Use Case:** Public registration endpoints

### IsAuthenticatedOrReadOnly

```python
class IsAuthenticatedOrReadOnly(BasePermission):
    """Authenticated users can do anything, others can only read"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True
        return bool(request.user and request.user.is_authenticated)
```

**Use Case:** Public blog where anyone can read, but must login to comment

---

## Role-Based Permissions

### IsAdmin

```python
class IsAdmin(BasePermission):
    """User must be admin/staff"""
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)
```

**Usage:**

```python
class UserManagementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
```

### IsSuperUser

```python
class IsSuperUser(BasePermission):
    """User must be superuser"""
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
```

### IsInGroup

```python
class IsInGroup(BasePermission):
    """User must be in specified group(s)"""
    
    required_groups = []  # Override in subclass
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not self.required_groups:
            return True
        
        user_groups = request.user.groups.values_list("name", flat=True)
        return any(group in user_groups for group in self.required_groups)
```

**Usage:**

```python
class ModeratorPermission(IsInGroup):
    required_groups = ['Moderators', 'Admins']

class ContentViewSet(viewsets.ModelViewSet):
    permission_classes = [ModeratorPermission]
```

### HasPermission

```python
class HasPermission(BasePermission):
    """User must have specific Django permission(s)"""
    
    required_permissions = []  # e.g., ['app.add_model', 'app.change_model']
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not self.required_permissions:
            return True
        
        return all(
            request.user.has_perm(perm)
            for perm in self.required_permissions
        )
```

**Usage:**

```python
class ArticlePublishPermission(HasPermission):
    required_permissions = ['articles.publish_article']

class ArticleViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == 'publish':
            return [ArticlePublishPermission()]
        return [IsAuthenticated()]
```

---

## Ownership Permissions

### IsOwner

```python
class IsOwner(BasePermission):
    """User must be the object owner"""
    
    owner_field = "user"  # Override if different
    
    def has_object_permission(self, request, view, obj):
        try:
            owner = getattr(obj, self.owner_field)
            return owner == request.user
        except AttributeError:
            logger.error(f"Owner field '{self.owner_field}' not found")
            return False
```

**Usage:**

```python
class Article(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

class ArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwner]
```

### IsOwnerOrReadOnly

```python
class IsOwnerOrReadOnly(BasePermission):
    """Owner can edit, others can only read"""
    
    owner_field = "user"
    
    def has_object_permission(self, request, view, obj):
        # Allow read for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow write for owner only
        try:
            owner = getattr(obj, self.owner_field)
            return owner == request.user
        except AttributeError:
            return False
```

**Use Case:** Public profiles where only owner can edit

### IsOwnerOrAdmin

```python
class IsOwnerOrAdmin(BasePermission):
    """Owner or admin can edit"""
    
    owner_field = "user"
    
    def has_object_permission(self, request, view, obj):
        # Admin can do anything
        if request.user and request.user.is_staff:
            return True
        
        # Owner can edit their own
        try:
            owner = getattr(obj, self.owner_field)
            return owner == request.user
        except AttributeError:
            return False
```

---

## HTTP Method Permissions

### IsReadOnly

```python
class IsReadOnly(BasePermission):
    """Only allow safe methods (GET, HEAD, OPTIONS)"""
    
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
```

### AllowGet

```python
class AllowGet(BasePermission):
    """Only allow GET requests"""
    
    def has_permission(self, request, view):
        return request.method == "GET"
```

### AllowPost

```python
class AllowPost(BasePermission):
    """Only allow POST requests"""
    
    def has_permission(self, request, view):
        return request.method == "POST"
```

---

## Complex Permissions

### MultiplePermissionsRequired (AND logic)

```python
class MultiplePermissionsRequired(BasePermission):
    """Require all specified permissions"""
    
    permissions = []  # List of permission classes
    
    def has_permission(self, request, view):
        if not self.permissions:
            return True
        
        for perm_class in self.permissions:
            perm = perm_class()
            if not perm.has_permission(request, view):
                return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        if not self.permissions:
            return True
        
        for perm_class in self.permissions:
            perm = perm_class()
            if not perm.has_object_permission(request, view, obj):
                return False
        
        return True
```

**Usage:**

```python
class PublishArticlePermission(MultiplePermissionsRequired):
    permissions = [IsAuthenticated, IsOwner, HasPermission]

class ArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [PublishArticlePermission]
```

### AnyPermissionRequired (OR logic)

```python
class AnyPermissionRequired(BasePermission):
    """Require any one of specified permissions"""
    
    permissions = []
    
    def has_permission(self, request, view):
        if not self.permissions:
            return True
        
        return any(
            perm().has_permission(request, view)
            for perm in self.permissions
        )
    
    def has_object_permission(self, request, view, obj):
        if not self.permissions:
            return True
        
        return any(
            perm().has_object_permission(request, view, obj)
            for perm in self.permissions
        )
```

**Usage:**

```python
class EditArticlePermission(AnyPermissionRequired):
    permissions = [IsOwner, IsAdmin]
    # Either owner OR admin can edit

class ArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [EditArticlePermission]
```

---

## Rate Limiting

### RateLimitPermission

```python
from django.core.cache import cache
from datetime import timedelta

class RateLimitPermission(BasePermission):
    """Rate limit based on user tier"""
    
    RATE_LIMITS = {
        "anonymous": (100, 3600),      # 100 requests per hour
        "authenticated": (1000, 3600),  # 1000 requests per hour
        "staff": (10000, 3600),        # 10000 requests per hour
    }
    
    def has_permission(self, request, view):
        # Determine tier
        if not request.user.is_authenticated:
            tier = "anonymous"
        elif request.user.is_staff:
            tier = "staff"
        else:
            tier = "authenticated"
        
        limit, window = self.RATE_LIMITS[tier]
        
        # Get cache key
        if request.user.is_authenticated:
            cache_key = f"rate_limit:user:{request.user.id}"
        else:
            ip = self.get_client_ip(request)
            cache_key = f"rate_limit:ip:{ip}"
        
        # Check limit
        current = cache.get(cache_key, 0)
        
        if current >= limit:
            logger.warning(f"Rate limit exceeded: {tier}")
            return False
        
        # Increment
        cache.set(cache_key, current + 1, window)
        return True
    
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
```

---

## Custom Permission Rules

### CustomPermissionRule

```python
class CustomPermissionRule(BasePermission):
    """Apply custom permission function"""
    
    rule_function = None  # Override with callable
    
    def has_permission(self, request, view):
        if self.rule_function is None:
            return True
        
        try:
            return self.rule_function(request, view, None)
        except Exception as e:
            logger.error(f"Error in permission rule: {e}")
            return False
    
    def has_object_permission(self, request, view, obj):
        if self.rule_function is None:
            return True
        
        try:
            return self.rule_function(request, view, obj)
        except Exception as e:
            logger.error(f"Error in permission rule: {e}")
            return False
```

**Usage:**

```python
def can_edit_article(request, view, obj):
    """Custom logic for editing articles"""
    if obj is None:
        return True
    
    # Owner can always edit
    if obj.user == request.user:
        return True
    
    # Editors can edit if not published
    if request.user.groups.filter(name='Editors').exists():
        return obj.status != 'published'
    
    return False

class ArticleEditPermission(CustomPermissionRule):
    rule_function = staticmethod(can_edit_article)
```

---

## Permission Factories

### Create Group Permission

```python
def create_group_permission(group_name: str) -> type:
    """Factory to create permission for specific group"""
    
    class GroupPermission(IsInGroup):
        required_groups = [group_name]
    
    GroupPermission.__name__ = f"Is{group_name.title()}"
    return GroupPermission

# Usage
IsModerator = create_group_permission("Moderators")
IsEditor = create_group_permission("Editors")

class ArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsModerator]
```

### Create Permission Check

```python
def create_permission_check(perm_string: str) -> type:
    """Factory to create permission for Django permission"""
    
    class PermissionCheck(HasPermission):
        required_permissions = [perm_string]
    
    PermissionCheck.__name__ = f"Has{perm_string.replace('.', '_').title()}"
    return PermissionCheck

# Usage
CanPublishArticle = create_permission_check("articles.publish_article")

class ArticleViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == 'publish':
            return [CanPublishArticle()]
        return super().get_permissions()
```

### Combine Permissions

```python
def combine_permissions(*permission_classes: type) -> type:
    """Combine multiple permissions with AND logic"""
    
    class CombinedPermission(MultiplePermissionsRequired):
        permissions = list(permission_classes)
    
    CombinedPermission.__name__ = "Combined" + "And".join(
        perm.__name__ for perm in permission_classes
    )
    return CombinedPermission

# Usage
EditArticle = combine_permissions(IsAuthenticated, IsOwner)

class ArticleViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in ['update', 'partial_update']:
            return [EditArticle()]
        return super().get_permissions()
```

---

## Best Practices

### 1. Use Action-Specific Permissions

✅ **Good:**

```python
class ArticleViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        elif self.action == 'create':
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwner()]
        elif self.action == 'publish':
            return [IsOwner(), HasPermission()]
        return super().get_permissions()
```

❌ **Bad:**

```python
class ArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]  # Same for all actions
```

### 2. Log Permission Denials

```python
class BasePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        result = self.check_access(request, view)
        if not result:
            logger.warning(
                f"Permission denied: {self.__class__.__name__}",
                extra={"user": request.user.id, "path": request.path}
            )
        return result
```

### 3. Test Permissions Thoroughly

```python
class PermissionTest(TestCase):
    def test_is_owner(self):
        """Test owner permission"""
        user1 = User.objects.create(username="user1")
        user2 = User.objects.create(username="user2")
        article = Article.objects.create(user=user1, title="Test")
        
        # Owner can access
        request = self.factory.get('/')
        request.user = user1
        self.assertTrue(IsOwner().has_object_permission(request, None, article))
        
        # Non-owner cannot
        request.user = user2
        self.assertFalse(IsOwner().has_object_permission(request, None, article))
```

### 4. Combine Permissions Logically

```python
# ✅ Clear logic
class ArticleViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == 'publish':
            # Must be owner AND have publish permission
            return [IsOwner(), HasPublishPermission()]
        return [IsAuthenticated()]

# ❌ Unclear
permission_classes = [IsOwner, HasPublishPermission, IsAuthenticated]
```

### 5. Handle Edge Cases

```python
class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Handle missing user
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Handle missing owner field
        try:
            owner = getattr(obj, self.owner_field)
        except AttributeError:
            logger.error(f"Owner field missing on {obj}")
            return False
        
        # Handle None owner
        if owner is None:
            return False
        
        return owner == request.user
```

---

## Summary

| Permission | Level | Use Case |
|------------|-------|----------|
| **IsAuthenticated** | View | Require login |
| **IsAdmin** | View | Admin only |
| **IsOwner** | Object | Own resources only |
| **IsOwnerOrReadOnly** | Object | Public read, owner write |
| **IsOwnerOrAdmin** | Object | Owner or admin edit |
| **IsReadOnly** | View | Read-only access |
| **MultiplePermissionsRequired** | Both | AND logic |
| **AnyPermissionRequired** | Both | OR logic |
| **RateLimitPermission** | View | Rate limiting |
| **CustomPermissionRule** | Both | Custom logic |

---

**Key Takeaways:**

- Use view-level for general access
- Use object-level for specific resources
- Combine permissions logically
- Log permission denials
- Test all permission scenarios
- Use factories for reusability
- Handle edge cases gracefully
- Document permission requirements