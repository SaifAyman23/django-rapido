# Django REST Framework Serializers Guide

**A comprehensive guide to production-grade DRF serializers with validation, audit logging, and field customization**

---

## Table of Contents

1. [Overview](#overview)
2. [Base Serializers](#base-serializers)
3. [Field Serializers](#field-serializers)
4. [User Serializers](#user-serializers)
5. [Bulk Operations](#bulk-operations)
6. [Validation](#validation)
7. [Audit Logging](#audit-logging)
8. [Mixins](#mixins)
9. [Common Patterns](#common-patterns)
10. [Best Practices](#best-practices)

---

## Overview

Serializers convert Django model instances to/from JSON, with validation and error handling.

### Why These Serializers?

- **Reusable base classes** — DRY principle for serializers
- **Integrated validation** — Email, passwords, phone numbers
- **Audit logging** — Track all changes automatically
- **Dynamic fields** — Include/exclude fields per request
- **Permission-based** — Hide sensitive fields based on permissions
- **Field customization** — Specialized fields for colors, prices, slugs

### Quick Start

```python
from .serializers import TimestampedSerializer

class ArticleSerializer(TimestampedSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author', 'created_at', 'updated_at']
```

**Features automatically included:**
- ✅ Audit logging on create/update
- ✅ Timestamp fields
- ✅ Dynamic field selection (`?fields=id,title`)
- ✅ Request metadata (IP, user agent)

---

## Base Serializers

Foundation classes with common functionality.

### DynamicFieldsSerializer

Allow clients to request specific fields.

```python
class ArticleSerializer(DynamicFieldsSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author', 'created_at']
```

**Usage:**

```bash
# Get all fields
GET /articles/1/

# Get only specific fields
GET /articles/1/?fields=id,title,author

# Exclude expensive fields
GET /articles/?fields=id,title
```

**Response (with fields parameter):**

```json
{
  "id": 1,
  "title": "Django Tips",
  "author": 3
}
```

**Advantages:**

- Reduce response size
- Optimize bandwidth
- Client-controlled data fetching
- Exclude expensive computations

**Implementation Details:**

```python
request = self.context.get("request")
if request:
    fields_param = request.query_params.get("fields")
    if fields_param:
        # Keep only requested fields
        allowed_fields = set(fields_param.split(","))
        fields_to_remove = set(self.fields.keys()) - allowed_fields
        for field in fields_to_remove:
            self.fields.pop(field)
```

### AuditableSerializer

Automatically log create/update operations using helpers.

```python
class ArticleSerializer(AuditableSerializer):
    class Meta:
        model = Article
        fields = '__all__'
```

**Automatic Audit Logging:**

On create:
```
Action: create
Instance: Article #1
User: john@example.com
Changes: {title: "New Article", content: "..."}
IP: 192.168.1.1
User Agent: Mozilla/5.0...
```

On update:
```
Action: update
Instance: Article #1
User: john@example.com
Changes: {
  title: {old: "Old Title", new: "New Title"},
  status: {old: "draft", new: "published"}
}
```

**Helpers Used:**

- `log_audit()` from helpers
- Automatically extracts IP, user agent from request
- Transaction-safe with `@transaction.atomic`

**Configuration:**

```python
class AuditableSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
```

### TimestampedSerializer

Combines dynamic fields + audit logging + timestamps.

```python
class ArticleSerializer(TimestampedSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'created_at', 'updated_at']
```

**Includes:**
- Dynamic field selection (`?fields=id,title`)
- Automatic audit logging
- `created_at` and `updated_at` fields
- Request metadata tracking

**Use Cases:**

- Blog articles
- Comments
- Any entity needing audit trail
- Mobile apps (bandwidth-conscious)

### ListRetrieveSerializer

Different serializer behavior for list vs detail views.

```python
class ArticleSerializer(ListRetrieveSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'author']
        list_exclude_fields = ['content']  # Exclude from list view
```

**Behavior:**

```
GET /articles/ → Returns: id, title, author (no content)
GET /articles/1/ → Returns: id, title, content, author
```

**Advantages:**

- Faster list responses (exclude expensive fields)
- Detailed view shows everything
- Bandwidth optimization
- Database query optimization

---

## Field Serializers

Specialized field types for common use cases.

### ColorField

For hex color values.

```python
class ThemeSerializer(serializers.ModelSerializer):
    primary_color = ColorField()
    
    class Meta:
        model = Theme
        fields = ['primary_color', 'secondary_color']
```

**Input:**
```json
{"primary_color": "FF5733"}  // With or without #
```

**Output:**
```json
{"primary_color": "#FF5733"}  // Always with #
```

**Features:**

- Auto-adds `#` prefix if missing
- Normalizes to uppercase
- Validates hex format

### SlugField

Auto-generate slugs from other fields.

```python
class ArticleSerializer(serializers.ModelSerializer):
    slug = SlugField(auto_generate_from='title')
    
    class Meta:
        model = Article
        fields = ['title', 'slug']
```

**Behavior:**

```json
{
  "title": "My Awesome Article",
  "slug": ""  // Will auto-generate
}
→
{
  "title": "My Awesome Article",
  "slug": "my-awesome-article"
}
```

**Manual slug:**

```json
{
  "title": "My Awesome Article",
  "slug": "custom-slug"  // Use provided slug
}
```

### JSONSerializerField

For JSON columns with validation.

```python
class ConfigSerializer(serializers.ModelSerializer):
    settings = JSONSerializerField()
    
    class Meta:
        model = Config
        fields = ['settings']
```

**Usage:**

```python
# Validate JSON
data = {"settings": {"theme": "dark", "notifications": True}}
serializer = ConfigSerializer(data=data)
serializer.is_valid()  # True
```

**Features:**

- Returns empty dict `{}` for null values
- Validates JSON structure
- Safe serialization using helpers

### PriceField

For decimal price values.

```python
class ProductSerializer(serializers.ModelSerializer):
    price = PriceField()
    discount_price = PriceField()
    
    class Meta:
        model = Product
        fields = ['price', 'discount_price']
```

**Default Settings:**

```python
max_digits = 10  # Max number of digits
decimal_places = 2  # Cents
coerce_to_string = False  # Return as float
```

**Output:**

```json
{"price": 19.99, "discount_price": 14.99}
```

### EnumField

For Django choice fields.

```python
class TaskSerializer(serializers.ModelSerializer):
    priority = EnumField(enum_choices=Task.PRIORITY_CHOICES)
    
    class Meta:
        model = Task
        fields = ['priority']
```

---

## User Serializers

Complete user management serializers.

### UserCreateSerializer

User registration with password validation.

```python
class UserSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm', 'first_name', 'last_name']
```

**Validation (using helpers):**

1. **Email validation** — `is_valid_email()` helper
2. **Password strength** — `is_strong_password()` helper
3. **Password match** — Confirms match

**Features:**

- Write-only password fields
- Strong password validation (8+ chars, uppercase, lowercase, numbers, special)
- Automatic password hashing
- Audit logging

**Usage:**

```python
data = {
    "email": "user@example.com",
    "username": "john",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
}

serializer = UserCreateSerializer(data=data)
if serializer.is_valid():
    user = serializer.save()
    # Automatically logged to audit trail
```

**Validation Response:**

```json
{
  "password": [
    "Password must contain uppercase letters",
    "Password must contain special characters"
  ]
}
```

### UserDetailSerializer

Complete user profile view.

```python
class ProfileSerializer(UserDetailSerializer):
    pass
```

**Fields:**

- `id`, `username`, `email`
- `first_name`, `last_name`, `full_name`
- `phone_number`, `avatar`, `bio`
- `email_verified`, `is_active`
- `created_at`, `updated_at`

**Features:**

- Computed `full_name` field
- Read-only timestamps
- Dynamic field selection supported

### UserListSerializer

Lightweight serializer for list views.

```python
class UserListSerializer(DynamicFieldsSerializer):
    pass
```

**Fields (small payload):**

```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "avatar": "https://...",
  "is_verified": true
}
```

**Use for:**

- User listings
- Team members
- Search results
- Author avatars

### UserUpdateSerializer

Profile updates (non-password).

```python
# In viewset
class UserViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'update' or self.action == 'partial_update':
            return UserUpdateSerializer
        return UserDetailSerializer
```

**Updatable Fields:**

- `first_name`, `last_name`
- `phone_number`, `avatar`, `bio`

**Avatar Validation:**

```python
def validate_avatar(self, value):
    # Max 5MB
    if value.size > 5 * 1024 * 1024:
        raise ValidationError("Image too large")
    return value
```

### UserPasswordChangeSerializer

Secure password change.

```python
data = {
    "old_password": "OldPass123!",
    "new_password": "NewPass456!",
    "new_password_confirm": "NewPass456!"
}

serializer = UserPasswordChangeSerializer(data=data, context={'request': request})
if serializer.is_valid():
    user = serializer.save()
    # Automatically logged to audit trail
```

**Validation:**

1. Verify old password is correct
2. Validate new password strength
3. Confirm passwords match
4. Update password securely
5. Log to audit trail

---

## Bulk Operations

Efficient bulk create/update with audit logging.

### BulkCreateSerializer

Create many instances at once.

```python
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'slug']
        list_serializer_class = BulkCreateSerializer
```

**Usage:**

```json
POST /tags/
[
  {"name": "django", "slug": "django"},
  {"name": "python", "slug": "python"},
  {"name": "rest", "slug": "rest"}
]
```

**Response:**

```json
[
  {"id": 1, "name": "django", "slug": "django"},
  {"id": 2, "name": "python", "slug": "python"},
  {"id": 3, "name": "rest", "slug": "rest"}
]
```

**Benefits:**

- Single database transaction
- Bulk insert (faster than loop)
- Automatic audit logging for each
- Error handling on any item fails whole transaction

**Features:**

- `bulk_create()` for performance
- Audit logging via `log_audit()` helper
- Automatic IP/user tracking
- Transactional safety

### BulkUpdateSerializer

Update many instances at once.

```python
class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'status']
        list_serializer_class = BulkUpdateSerializer
```

**Usage:**

```json
PATCH /articles/
[
  {"id": 1, "status": "published"},
  {"id": 2, "status": "archived"},
  {"id": 3, "status": "draft"}
]
```

**Response:**

```json
[
  {"id": 1, "title": "...", "status": "published"},
  {"id": 2, "title": "...", "status": "archived"},
  {"id": 3, "title": "...", "status": "draft"}
]
```

**Features:**

- Match by ID
- Bulk update (single query)
- Audit logging for each
- Transactional

---

## Validation

Custom validation using helpers.

### Email Validation

```python
class SubscriberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        # Use helper function
        if not is_valid_email(value):
            raise ValidationError("Invalid email format")
        return value
```

### Password Strength Validation

```python
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    def validate_password(self, value):
        # Use helper function
        is_valid, errors = is_strong_password(value)
        if not is_valid:
            raise ValidationError(errors)
        return value
```

**Helper returns:**

```python
is_valid = False
errors = [
    "Password must be at least 8 characters",
    "Password must contain special characters"
]
```

### Cross-Field Validation

```python
def validate(self, data):
    # Validate multiple fields together
    if data['password'] != data['password_confirm']:
        raise ValidationError({'password': 'Passwords do not match'})
    
    if data['start_date'] > data['end_date']:
        raise ValidationError({'end_date': 'Must be after start date'})
    
    return data
```

---

## Audit Logging

Automatic audit trail for all changes.

### How It Works

Every create/update automatically:

1. **Captures changes** — Old → New values
2. **Logs action** — create, update
3. **Records user** — Who made the change
4. **Tracks request** — IP address, user agent
5. **Stores in database** — Via `log_audit()` helper

### Example Audit Trail

```python
# Create
log_audit(
    action="create",
    instance=article,
    user=request.user,
    changes={"title": "New Article", "content": "..."},
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0..."
)

# Update
log_audit(
    action="update",
    instance=article,
    user=request.user,
    changes={
        "title": {"old": "Old Title", "new": "New Title"},
        "status": {"old": "draft", "new": "published"}
    },
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0..."
)
```

### View Audit Trail

```python
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filterset_fields = ['user', 'action', 'content_type']
    ordering = ['-timestamp']
```

---

## Mixins

Reusable functionality for serializers.

### SlugRelatedFieldMixin

Convert PKs to slug fields.

```python
class ArticleSerializer(SlugRelatedFieldMixin, serializers.ModelSerializer):
    slug_field = "slug"  # Use slug instead of ID
    
    class Meta:
        model = Article
        fields = ['title', 'author', 'category']
```

**Input:**

```json
{"title": "Article", "author": "john", "category": "tech"}
```

**vs (without mixin):**

```json
{"title": "Article", "author": 1, "category": 2}
```

### PermissionMixin

Hide sensitive fields based on permissions.

```python
class UserSerializer(PermissionMixin, serializers.ModelSerializer):
    permission_fields = {
        'email': 'users.view_email',
        'phone_number': 'users.view_phone',
        'ssn': 'users.view_ssn',
    }
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'ssn']
```

**Behavior:**

- User without `view_email` permission → email field not returned
- User with `view_email` permission → email field returned
- Automatic on serialization

**Usage:**

```python
# Admin sees all fields
admin_serializer = UserSerializer(user, context={'request': admin_request})
# Returns: id, username, email, phone_number, ssn

# Regular user sees limited fields
user_serializer = UserSerializer(user, context={'request': user_request})
# Returns: id, username (email, phone_number hidden)
```

---

## Common Patterns

### Pattern 1: Nested Creation

Create parent + children in one request.

```python
class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'text', 'author']

class ArticleSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Article
        fields = ['title', 'content', 'comments']
```

### Pattern 2: Dynamic Serializer Selection

Different serializers per action.

```python
class ArticleViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        elif self.action == 'create':
            return ArticleCreateSerializer
        elif self.action == 'update':
            return ArticleUpdateSerializer
        return ArticleDetailSerializer
```

### Pattern 3: Conditional Field Serialization

Show fields based on context.

```python
class ProductSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    
    def get_price(self, obj):
        # Show internal cost only for staff
        if self.context['request'].user.is_staff:
            return {'retail': obj.price, 'cost': obj.cost}
        return obj.price
```

### Pattern 4: Validation with Multiple Fields

```python
def validate(self, data):
    # If discount set, discount_price required
    if data.get('has_discount') and not data.get('discount_price'):
        raise ValidationError({'discount_price': 'Required when discount is set'})
    
    # Discount price must be less than regular price
    if data.get('discount_price', 0) >= data.get('price', 0):
        raise ValidationError({'discount_price': 'Must be less than regular price'})
    
    return data
```

---

## Best Practices

### 1. Use Appropriate Base Class

```python
# ✅ Good - audit logging needed
class ArticleSerializer(TimestampedSerializer):
    pass

# ✅ Good - read-only, no audit needed
class ArticleListSerializer(DynamicFieldsSerializer):
    pass

# ❌ Bad - missing functionality
class ArticleSerializer(serializers.ModelSerializer):
    pass
```

### 2. Validate with Helpers

```python
# ✅ Good - uses helpers
def validate_email(self, value):
    if not is_valid_email(value):
        raise ValidationError("Invalid email")
    return value

# ❌ Bad - manual validation
def validate_email(self, value):
    if '@' not in value:
        raise ValidationError("Invalid email")
    return value
```

### 3. Separate Serializers by Action

```python
# ✅ Good - different serializers
class UserViewSet:
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer  # Lightweight
        return UserDetailSerializer  # Full details

# ❌ Bad - one serializer for everything
class UserViewSet:
    serializer_class = UserDetailSerializer
```

### 4. Use Dynamic Fields for Mobile

```python
# ✅ Good - extend DynamicFieldsSerializer
class ArticleSerializer(DynamicFieldsSerializer):
    pass

# Usage: GET /articles/?fields=id,title (no content)

# ❌ Bad - return all fields always
class ArticleSerializer(serializers.ModelSerializer):
    pass
```

### 5. Set Read-Only Appropriately

```python
# ✅ Good
class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'title', 'created_at', 'author']
        read_only_fields = ['id', 'created_at', 'author']

# ❌ Bad - users could modify protected fields
class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = '__all__'
```

### 6. Use Transactions for Bulk

```python
# ✅ Good - atomic
@transaction.atomic
def create(self, validated_data):
    instances = [Item(**data) for data in validated_data]
    return Item.objects.bulk_create(instances)

# ❌ Bad - not atomic
def create(self, validated_data):
    for item_data in validated_data:
        Item.objects.create(**item_data)
```

### 7. Log Important Actions

```python
# ✅ Good - audit logged
class UserCreateSerializer(TimestampedSerializer):
    def create(self, validated_data):
        user = super().create(validated_data)
        log_audit(
            action="create",
            instance=user,
            user=self._get_user_from_context(),
        )
        return user

# ❌ Bad - no audit trail
def create(self, validated_data):
    return super().create(validated_data)
```

---

## Summary

| Class | Use When |
|-------|----------|
| **DynamicFieldsSerializer** | Need field selection |
| **AuditableSerializer** | Need change tracking |
| **TimestampedSerializer** | Need both above + timestamps |
| **ListRetrieveSerializer** | Different list/detail needs |
| **UserCreateSerializer** | User registration |
| **UserDetailSerializer** | User profile |
| **UserListSerializer** | User listings |
| **BulkCreateSerializer** | Bulk create |
| **BulkUpdateSerializer** | Bulk update |
| **PermissionMixin** | Permission-based fields |
| **SlugRelatedFieldMixin** | Slug relationships |

---

## Next Steps

1. Extend from appropriate base serializer
2. Add validation using helpers
3. Configure `list_exclude_fields` for performance
4. Set `permission_fields` for sensitive data
5. Test with different user permissions

---

## Questions?

Refer to:
1. **Base Serializers** for foundation classes
2. **Field Serializers** for custom fields
3. **User Serializers** for authentication
4. **Bulk Operations** for batch operations
5. **Best Practices** for dos and don'ts