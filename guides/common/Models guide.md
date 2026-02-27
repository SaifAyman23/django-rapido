# Django Abstract Models & Utilities Guide

**A comprehensive guide to building production-grade Django models with reusable components**

---

## Table of Contents

1. [Overview](#overview)
2. [Core Managers](#core-managers)
3. [Abstract Base Models](#abstract-base-models)
4. [Custom User Model](#custom-user-model)
5. [Audit Trail System](#audit-trail-system)
6. [Usage Patterns](#usage-patterns)
7. [Performance Optimization](#performance-optimization)
8. [Testing Strategies](#testing-strategies)
9. [Best Practices](#best-practices)

---

## Overview

This guide covers production-grade abstract models, managers, and mixins that provide:

- **UUID Primary Keys** — Distributed-friendly IDs
- **Soft Deletes** — Safe deletion with restore capability
- **Change Tracking** — Automatic field change logging
- **Time-based Queries** — Built-in time filtering
- **Audit Logging** — Complete action history
- **Enhanced User Model** — Extended Django user

### Why Use These Base Classes?

- **Consistency** — Uniform behavior across models
- **Productivity** — Write less code, do more
- **Maintainability** — Single source of truth
- **Production-Ready** — Battle-tested patterns
- **Security** — Built-in audit and tracking

### Quick Start

```python
# models.py
from core.models import SoftDeleteModel, PublishableModel, SEOModel

class Article(SoftDeleteModel, PublishableModel, SEOModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    class Meta:
        indexes = [
            models.Index(fields=['title']),
        ]

# Usage
article = Article.objects.create(title="My Article", content="...")
article.publish()  # Inherited from PublishableModel
article.delete()   # Soft delete (inherited)
article.restore()  # Restore from soft delete
```

---

## Core Managers

### SoftDeleteQuerySet

**Purpose:** Provides query methods for soft-deleted records.

```python
class SoftDeleteQuerySet(QuerySet):
    """QuerySet for soft-deleted models"""

    def delete(self) -> Tuple[int, Dict[str, int]]:
        """Soft delete records"""
        return self.update(deleted_at=timezone.now())

    def restore(self) -> int:
        """Restore soft-deleted records"""
        return self.update(deleted_at=None)

    def active(self) -> "SoftDeleteQuerySet":
        """Return only active (non-deleted) records"""
        return self.filter(deleted_at__isnull=True)

    def deleted(self) -> "SoftDeleteQuerySet":
        """Return only deleted records"""
        return self.filter(deleted_at__isnull=False)

    def all_including_deleted(self) -> "SoftDeleteQuerySet":
        """Return all records including deleted"""
        return self.all()
```

**Usage:**

```python
# Get only active records (default)
Article.objects.all()  # Returns active only

# Include deleted records
Article.objects.all_with_deleted()

# Get only deleted records
Article.objects.deleted()

# Bulk operations
Article.objects.filter(status='draft').delete()  # Soft delete
Article.objects.deleted().restore()  # Restore all deleted
```

### SoftDeleteManager

**Purpose:** Default manager that filters out deleted records.

```python
class SoftDeleteManager(Manager):
    """Manager for soft-deleted models"""

    def get_queryset(self) -> SoftDeleteQuerySet:
        """Override to filter out deleted records by default"""
        return SoftDeleteQuerySet(self.model, using=self._db).active()

    def all_with_deleted(self) -> SoftDeleteQuerySet:
        """Include deleted records in query"""
        return SoftDeleteQuerySet(self.model, using=self._db).all_including_deleted()

    def deleted(self) -> SoftDeleteQuerySet:
        """Return only deleted records"""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()

    def restore_all(self) -> int:
        """Restore all deleted records"""
        return self.all_with_deleted().filter(deleted_at__isnull=False).restore()
```

### CustomUserManager

**Purpose:** Enhanced user manager with email as primary identifier.

```python
class CustomUserManager(BaseUserManager):
    """Custom user manager with email as unique identifier"""

    def create_user(
        self, email: str, password: Optional[str] = None, **extra_fields
    ) -> "CustomUser":
        """Create and save regular user"""
        if not email:
            raise ValueError(_("Email address is required"))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: Optional[str] = None, **extra_fields
    ) -> "CustomUser":
        """Create and save superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True"))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True"))

        return self.create_user(email, password, **extra_fields)

    def active(self) -> QuerySet:
        """Return only active users"""
        return self.filter(is_active=True)

    def verified(self) -> QuerySet:
        """Return only verified users"""
        return self.filter(is_verified=True)

    def recently_joined(self, days: int = 7) -> QuerySet:
        """Return users who joined in the last N days"""
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)
```

**Usage:**

```python
# Create users
user = CustomUser.objects.create_user(
    email="user@example.com",
    password="secure123",
    first_name="John",
    last_name="Doe"
)

superuser = CustomUser.objects.create_superuser(
    email="admin@example.com",
    password="admin123"
)

# Query users
active_users = CustomUser.objects.active()
verified_users = CustomUser.objects.verified()
recent_users = CustomUser.objects.recently_joined(days=30)
```

### TimestampedQuerySet & Manager

**Purpose:** Provides time-based query methods.

```python
class TimestampedQuerySet(QuerySet):
    """QuerySet with timestamp-based filtering"""

    def recent(self, days: int = 7) -> "TimestampedQuerySet":
        """Return records from the last N days"""
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)

    def older_than(self, days: int = 30) -> "TimestampedQuerySet":
        """Return records older than N days"""
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(created_at__lt=cutoff_date)

    def updated_since(self, datetime_obj) -> "TimestampedQuerySet":
        """Return records updated since a specific datetime"""
        return self.filter(updated_at__gte=datetime_obj)


class TimestampedManager(Manager):
    """Manager for timestamped models"""

    def get_queryset(self) -> TimestampedQuerySet:
        return TimestampedQuerySet(self.model, using=self._db)

    def recent(self, days: int = 7) -> TimestampedQuerySet:
        """Return records from the last N days"""
        return self.get_queryset().recent(days)

    def older_than(self, days: int = 30) -> TimestampedQuerySet:
        """Return records older than N days"""
        return self.get_queryset().older_than(days)
```

**Usage:**

```python
# Time-based queries
recent_articles = Article.objects.recent(days=7)
old_articles = Article.objects.older_than(days=90)
updated_today = Article.objects.updated_since(timezone.now().replace(hour=0))
```

---

## Abstract Base Models

### UUIDModel

**Purpose:** Base model with UUID primary key instead of auto-incrementing integer.

```python
class UUIDModel(models.Model):
    """Base model with UUID primary key"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier",
    )

    class Meta:
        abstract = True
```

**Why UUID?**

| Feature | Auto-increment | UUID |
|---------|---------------|------|
| **Collision Risk** | Low within single DB | Extremely low globally |
| **Merge Safety** | Conflicts likely | Safe for merges |
| **URL Exposure** | Predictable | Obfuscated |
| **Performance** | Fast (integer) | Slightly slower |
| **Sharding** | Difficult | Easy |

**Usage:**

```python
class Product(UUIDModel):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)

# UUID is auto-generated
product = Product.objects.create(name="Laptop", price=999.99)
print(product.id)  # 550e8400-e29b-41d4-a716-446655440000
```

### TimestampedModel

**Purpose:** Adds created_at and updated_at timestamps to any model.

```python
class TimestampedModel(models.Model):
    """Model with created_at and updated_at timestamps"""

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Creation timestamp",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Last update timestamp",
    )

    objects = TimestampedManager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["-updated_at"]),
        ]
```

**Features:**

- Automatic timestamp on creation and update
- Database indexes for efficient sorting
- Default ordering by creation date (newest first)
- Time-based query methods via manager

**Usage:**

```python
class Comment(TimestampedModel):
    text = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)

# Timestamps are automatic
comment = Comment.objects.create(text="Great post!", author=user)
print(comment.created_at)  # 2025-02-27 10:30:45
print(comment.updated_at)  # Same as created_at initially

comment.text = "Updated comment"
comment.save()
print(comment.updated_at)  # Updated timestamp

# Time-based queries
today_comments = Comment.objects.recent(days=1)
old_comments = Comment.objects.older_than(days=30)
```

### SoftDeleteModel

**Purpose:** Implements soft delete pattern with restore capability.

```python
class SoftDeleteModel(models.Model):
    """Model with soft delete capability"""

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Soft delete timestamp",
    )

    objects = SoftDeleteManager()

    def delete(self, *args, **kwargs) -> Tuple[int, Dict[str, int]]:
        """Override delete to implement soft delete"""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
        return 1, {self._meta.label: 1}

    def hard_delete(self, *args, **kwargs) -> Tuple[int, Dict[str, int]]:
        """Permanently delete the record"""
        return super().delete(*args, **kwargs)

    def restore(self) -> None:
        """Restore soft-deleted record"""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted"""
        return self.deleted_at is not None

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["deleted_at"]),
            models.Index(fields=["-created_at", "deleted_at"]),
        ]
```

**How Soft Delete Works:**

1. **Normal delete** — Sets `deleted_at` timestamp instead of removing record
2. **Hard delete** — Actually removes record from database
3. **Restore** — Sets `deleted_at` back to `None`
4. **Querying** — Default manager excludes deleted records

**Usage:**

```python
class Task(SoftDeleteModel):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)

# Create task
task = Task.objects.create(title="Write documentation")

# Soft delete
task.delete()  # deleted_at set to now
print(task.is_deleted)  # True

# Task is excluded from normal queries
Task.objects.count()  # 0
Task.objects.all_with_deleted().count()  # 1

# Restore
task.restore()
Task.objects.count()  # 1

# Permanently delete
task.hard_delete()
```

**Bulk Operations:**

```python
# Soft delete multiple
Task.objects.filter(completed=True).delete()

# Restore all deleted
Task.objects.deleted().restore()

# Hard delete permanently
Task.objects.deleted().hard_delete()
```

### ChangeTrackingModel

**Purpose:** Automatically tracks field changes and stores them in JSON log.

```python
class ChangeTrackingModel(TimestampedModel):
    """Model that tracks field changes"""

    change_log = models.JSONField(
        default=dict,
        blank=True,
        help_text="Track field changes",
    )

    def get_changed_fields(self) -> Dict[str, Any]:
        """Get fields that have changed since last save"""
        if not self.pk:
            return {}

        try:
            db_instance = self.__class__.objects.get(pk=self.pk)
        except ObjectDoesNotExist:
            return {}

        changed = {}
        for field in self._meta.fields:
            if field.name in ["updated_at", "change_log"]:
                continue

            current_value = getattr(self, field.name)
            db_value = getattr(db_instance, field.name)

            if current_value != db_value:
                changed[field.name] = {
                    "old": str(db_value),
                    "new": str(current_value),
                }

        return changed

    def save(self, *args, **kwargs) -> None:
        """Save and track changes"""
        changed = self.get_changed_fields()
        if changed:
            self.change_log[str(timezone.now().isoformat())] = changed

        super().save(*args, **kwargs)

    class Meta:
        abstract = True
```

**Features:**

- Tracks changes to all fields except `updated_at` and `change_log`
- Stores changes with timestamp in JSON format
- Non-invasive — works automatically on save

**Usage:**

```python
class Document(ChangeTrackingModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, default="draft")

# Create document
doc = Document.objects.create(
    title="Report",
    content="Initial content",
    status="draft"
)

# Change fields
doc.title = "Final Report"
doc.status = "published"
doc.save()

# View change log
print(doc.change_log)
# {
#   "2025-02-27T10:30:45.123Z": {
#     "title": {"old": "Report", "new": "Final Report"},
#     "status": {"old": "draft", "new": "published"}
#   }
# }
```

**Use Cases:**

- Audit requirements
- Debugging user actions
- Undo/redo functionality
- Version history
- Compliance tracking

### PublishableModel

**Purpose:** Implements content publishing workflow with draft/published/archived states.

```python
class PublishableModel(TimestampedModel):
    """Model with draft/published status"""

    STATUS_CHOICES = (
        ("draft", _("Draft")),
        ("published", _("Published")),
        ("archived", _("Archived")),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        db_index=True,
        help_text="Publication status",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Publication timestamp",
    )

    def publish(self) -> None:
        """Publish the record"""
        self.status = "published"
        self.published_at = timezone.now()
        self.save(update_fields=["status", "published_at"])

    def unpublish(self) -> None:
        """Unpublish the record"""
        self.status = "draft"
        self.save(update_fields=["status"])

    def archive(self) -> None:
        """Archive the record"""
        self.status = "archived"
        self.save(update_fields=["status"])

    @property
    def is_published(self) -> bool:
        """Check if record is published"""
        return self.status == "published"

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]
```

**Workflow States:**

```
draft ──publish──> published ──archive──> archived
  ^                    │
  └──unpublish─────────┘
```

**Usage:**

```python
class BlogPost(PublishableModel):
    title = models.CharField(max_length=200)
    content = models.TextField()

# Create as draft (default)
post = BlogPost.objects.create(
    title="My Post",
    content="Content here..."
)
print(post.status)  # "draft"
print(post.is_published)  # False

# Publish
post.publish()
print(post.status)  # "published"
print(post.published_at)  # Timestamp set
print(post.is_published)  # True

# Unpublish
post.unpublish()
print(post.status)  # "draft"

# Archive
post.archive()
print(post.status)  # "archived"

# Query published posts
published_posts = BlogPost.objects.filter(status="published")
```

### SEOModel

**Purpose:** Adds common SEO fields to models for content optimization.

```python
class SEOModel(TimestampedModel):
    """Model with SEO fields"""

    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="URL-friendly slug",
    )
    seo_title = models.CharField(
        max_length=60,
        blank=True,
        help_text="SEO title (60 characters)",
    )
    seo_description = models.CharField(
        max_length=160,
        blank=True,
        help_text="SEO description (160 characters)",
    )
    seo_keywords = models.CharField(
        max_length=255,
        blank=True,
        help_text="SEO keywords (comma-separated)",
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["slug"]),
        ]
```

**SEO Best Practices:**

| Field | Character Limit | Purpose |
|-------|----------------|---------|
| `seo_title` | 60 | Title shown in search results |
| `seo_description` | 160 | Description shown in search results |
| `seo_keywords` | 255 | Keywords for search engines |
| `slug` | 255 | URL-friendly identifier |

**Usage:**

```python
class Product(SEOModel):
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.seo_title:
            self.seo_title = self.name[:60]
        if not self.seo_description:
            self.seo_description = self.description[:160]
        super().save(*args, **kwargs)

product = Product.objects.create(
    name="Wireless Headphones",
    description="High-quality wireless headphones with noise cancellation...",
    seo_keywords="headphones,wireless,audio"
)

# URL uses slug
print(product.slug)  # "wireless-headphones"
```

---

## Custom User Model

### CustomUser

**Purpose:** Enhanced Django user model with modern features.

```python
class CustomUser(AbstractUser):
    """Custom user model with enhanced features"""

    # Identity
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="User phone number",
    )

    # Media & Profile
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/%d/",
        null=True,
        blank=True,
        help_text="User avatar image",
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="User biography",
    )

    # Verification & Security
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Email verified status",
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Email verification timestamp",
    )
    verification_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="Email verification token",
    )
    two_factor_enabled = models.BooleanField(
        default=False,
        help_text="Two-factor authentication status",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_('The groups this user belongs to.'),
        related_name='customuser_set',
        related_query_name='customuser',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='customuser_set',
        related_query_name='customuser',
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_verified"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username}"

    def verify_email(self) -> None:
        """Mark user email as verified"""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.verification_token = ""
        self.save(update_fields=["is_verified", "verified_at", "verification_token"])
        logger.info(f"User {self.id} email verified")

    def get_display_name(self) -> str:
        """Get user's display name"""
        if self.get_full_name():
            return self.get_full_name()
        return self.username or self.email

    @property
    def is_fully_verified(self) -> bool:
        """Check if user is fully verified"""
        return self.is_verified and self.is_active

    def save(self, *args, **kwargs):
        # Ensure ID is stored as string with hyphens
        if self.id and isinstance(self.id, uuid.UUID):
            self.id = str(self.id)  # Convert to string with hyphens
        super().save(*args, **kwargs)
```

**Key Features:**

| Feature | Description |
|---------|-------------|
| **UUID Primary Key** | Non-sequential, globally unique IDs (inherited from AbstractUser) |
| **Email as Username** | Login with email instead of username |
| **Email Verification** | Track verification status and timestamp |
| **Profile Fields** | Avatar, bio, phone number |
| **Security** | Two-factor auth flag, verification tokens |
| **Timestamps** | Created, updated, last login |
| **Audit Logging** | Signal for user creation events |

**Settings Configuration:**

```python
# settings.py

# Custom user model
AUTH_USER_MODEL = 'your_app.CustomUser'

# Media files for avatars
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email verification
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
```

**Usage Examples:**

```python
# Create user (email is primary identifier)
user = CustomUser.objects.create_user(
    email="john@example.com",
    password="secure123",
    first_name="John",
    last_name="Doe",
    phone_number="+1234567890"
)

# Create superuser
admin = CustomUser.objects.create_superuser(
    email="admin@example.com",
    password="admin123",
    username="admin"  # Required by REQUIRED_FIELDS
)

# Email verification
user.verify_email()
print(user.is_verified)  # True
print(user.verified_at)  # Timestamp set

# Display name
print(user.get_display_name())  # "John Doe"
print(user.get_full_name())  # "John Doe"

# Query users
verified_users = CustomUser.objects.verified()
recent_users = CustomUser.objects.recently_joined(days=30)

# Check verification status
if user.is_fully_verified:
    # Allow access to sensitive features
    pass
```

**Signal for Logging:**

```python
@receiver(post_save, sender=CustomUser)
def log_user_creation(sender, instance, created, **kwargs):
    """Log user creation events"""
    if created:
        logger.info(f"New user created: {instance.id} ({instance.email})")
```

---

## Audit Trail System

### AuditLog Model

**Purpose:** Comprehensive audit logging for all model changes.

```python
class AuditLog(TimestampedModel):
    """Track changes to models for compliance and debugging"""

    ACTION_CHOICES = (
        ("create", _("Create")),
        ("update", _("Update")),
        ("delete", _("Delete")),
        ("restore", _("Restore")),
        ("publish", _("Publish")),
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True,
    )
    
    # ContentType fields for generic relation
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=~Q(app_label='common'),  # Optional: restrict to specific apps
        null=True,
        blank=True
    )
    object_id = models.UUIDField(
        null=True, 
        blank=True, 
        db_index=True
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    object_repr = models.CharField(max_length=255)
    changes = models.JSONField(default=dict)
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["object_id", "-timestamp"]),
            models.Index(fields=["content_type", "-timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.object_repr}"
```

**Audit Log Schema:**

| Field | Purpose | Example |
|-------|---------|---------|
| `action` | Type of change | "update" |
| `content_type` | Model type | Article |
| `object_id` | Record ID (UUID) | "550e8400-e29b-41d4-a716-446655440000" |
| `object_repr` | String representation | "Article: My Post" |
| `changes` | Detailed changes | `{"title": {"old": "Draft", "new": "Final"}}` |
| `user` | Who made the change | John Doe |
| `ip_address` | Origin IP | 192.168.1.1 |
| `user_agent` | Browser/client info | "Mozilla/5.0..." |
| `timestamp` | When it happened | 2025-02-27 10:30 |

### Signal Handlers for Audit Logging

```python
# signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
import json
import uuid

@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """Store original values before save"""
    if not instance.pk or sender == AuditLog:
        return
    
    # Store original values in instance's cache
    try:
        original = sender.objects.get(pk=instance.pk)
        instance._original_values = {
            field.name: getattr(original, field.name)
            for field in sender._meta.fields
            if field.name not in ['updated_at']
        }
    except sender.DoesNotExist:
        instance._original_values = {}

@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Log create/update actions"""
    if sender == AuditLog:
        return
    
    # Determine action
    action = "create" if created else "update"
    
    # Get changes if update
    changes = {}
    if not created and hasattr(instance, '_original_values'):
        for field, old_value in instance._original_values.items():
            new_value = getattr(instance, field)
            if old_value != new_value:
                changes[field] = {
                    'old': str(old_value),
                    'new': str(new_value)
                }
    
    # For create, log all fields
    if created:
        changes = {
            field.name: str(getattr(instance, field.name))
            for field in sender._meta.fields
            if field.name not in ['id', 'created_at', 'updated_at']
        }
    
    # Ensure object_id is stored as string with hyphens
    object_id = instance.pk
    if isinstance(object_id, uuid.UUID):
        object_id = str(object_id)
    
    # Create audit log
    AuditLog.objects.create(
        action=action,
        content_type=ContentType.objects.get_for_model(instance),
        object_id=object_id,
        object_repr=str(instance),
        changes=changes,
        user=getattr(instance, '_audit_user', None),  # Pass user context
        ip_address=getattr(instance, '_audit_ip', None),
        user_agent=getattr(instance, '_audit_ua', None),
    )

@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    """Log delete actions"""
    if sender == AuditLog:
        return
    
    # Ensure object_id is stored as string with hyphens
    object_id = instance.pk
    if isinstance(object_id, uuid.UUID):
        object_id = str(object_id)
    
    AuditLog.objects.create(
        action="delete",
        content_type=ContentType.objects.get_for_model(instance),
        object_id=object_id,
        object_repr=str(instance),
        changes={},
        user=getattr(instance, '_audit_user', None),
        ip_address=getattr(instance, '_audit_ip', None),
        user_agent=getattr(instance, '_audit_ua', None),
    )
```

### Context Manager for User Tracking

```python
# context.py
from contextlib import contextmanager

@contextmanager
def audit_context(user=None, ip_address=None, user_agent=None):
    """Context manager to set audit user for model operations"""
    from django.db.models import signals
    from django.dispatch import receiver
    
    # Store original handlers
    original_handlers = {}
    
    # Temporarily attach audit info to models
    for model in models.get_models():
        def make_handler(model):
            @receiver(signals.pre_save, sender=model, weak=False)
            def attach_audit_info(sender, instance, **kwargs):
                instance._audit_user = user
                instance._audit_ip = ip_address
                instance._audit_ua = user_agent
        
        handler = make_handler(model)
        original_handlers[model] = handler
    
    try:
        yield
    finally:
        # Remove temporary handlers
        for model, handler in original_handlers.items():
            signals.pre_save.disconnect(handler, sender=model)
```

### Using Audit Log

```python
# views.py
from django.contrib.auth.decorators import login_required
from .models import Article, AuditLog
from .context import audit_context

@login_required
def update_article(request, pk):
    """Update article with audit logging"""
    article = Article.objects.get(pk=pk)
    
    # Set audit context
    article._audit_user = request.user
    article._audit_ip = request.META.get('REMOTE_ADDR')
    article._audit_ua = request.META.get('HTTP_USER_AGENT', '')
    
    # Update article
    article.title = request.POST.get('title')
    article.content = request.POST.get('content')
    article.save()  # Triggers audit log
    
    # Or use context manager for multiple operations
    with audit_context(
        user=request.user,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    ):
        article.publish()  # Will be audited
```

### Querying Audit Logs

```python
# Get recent actions
recent_changes = AuditLog.objects.filter(
    timestamp__gte=timezone.now() - timedelta(days=7)
)

# Get actions for specific object
article_logs = AuditLog.objects.filter(
    content_type=ContentType.objects.get_for_model(Article),
    object_id=article.id
).order_by('-timestamp')

# Get user's actions
user_actions = AuditLog.objects.filter(user=user)

# Get specific action type
publishes = AuditLog.objects.filter(action='publish')

# Get changes with specific field
title_changes = AuditLog.objects.filter(
    changes__has_key='title'
)

# Count by action
from django.db.models import Count
action_counts = AuditLog.objects.values('action').annotate(
    count=Count('id')
)
```

### Audit Log Admin

```python
# admin.py
from django.contrib import admin
from django.utils.html import format_json
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action', 'user', 'object_repr', 'content_type']
    list_filter = ['action', 'content_type', 'timestamp']
    search_fields = ['object_repr', 'user__email']
    readonly_fields = ['timestamp', 'changes_display']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('timestamp', 'action', 'user')
        }),
        ('Object', {
            'fields': ('content_type', 'object_id', 'object_repr')
        }),
        ('Changes', {
            'fields': ('changes_display',),
            'classes': ('wide',)
        }),
        ('Request Info', {
            'fields': ('ip_address', 'user_agent')
        }),
    )
    
    def changes_display(self, obj):
        """Pretty print JSON changes"""
        return format_json(obj.changes)
    changes_display.short_description = 'Changes'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
```

---

## Usage Patterns

### Pattern 1: Blog System

```python
# models.py
class Category(TimestampedModel):
    """Blog category"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Post(SoftDeleteModel, PublishableModel, SEOModel, ChangeTrackingModel):
    """Blog post with all features"""
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    excerpt = models.TextField(max_length=500, blank=True)
    
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='posts'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='posts'
    )
    tags = models.ManyToManyField('Tag', blank=True)
    
    featured_image = models.ImageField(
        upload_to='blog/%Y/%m/%d/',
        null=True,
        blank=True
    )
    views_count = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        """Auto-generate excerpt if not provided"""
        if not self.excerpt and self.content:
            self.excerpt = self.content[:497] + '...' if len(self.content) > 500 else self.content
        super().save(*args, **kwargs)
    
    def increment_views(self):
        """Increment view counter"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('post-detail', kwargs={'slug': self.slug})

class Tag(TimestampedModel):
    """Blog tags"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name
```

**Usage:**

```python
# Create blog post
post = Post.objects.create(
    title="My First Post",
    content="Long content here...",
    author=user,
    category=category
)
post.tags.add(tag1, tag2)

# Publish
post.publish()

# Update (tracked by ChangeTrackingModel)
post.title = "Updated Title"
post.save()

# View change log
print(post.change_log)

# Soft delete
post.delete()

# Restore if needed
post.restore()

# Query published posts
published = Post.objects.filter(status='published')

# Get recent posts
recent = Post.objects.recent(days=7)
```

### Pattern 2: E-commerce

```python
# models.py
class Product(SoftDeleteModel, SEOModel, PublishableModel):
    """E-commerce product"""
    
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost of goods")
    
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    
    category = models.ForeignKey(
        'Category',
        on_delete=models.PROTECT,
        related_name='products'
    )
    
    description = models.TextField()
    specifications = models.JSONField(default=dict, blank=True)
    
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dimensions = models.CharField(max_length=100, blank=True)
    
    # Metrics
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveIntegerField(default=0)
    
    @property
    def current_price(self):
        """Get current price (sale price if available)"""
        return self.sale_price if self.sale_price else self.price
    
    @property
    def is_on_sale(self):
        """Check if product is on sale"""
        return self.sale_price is not None
    
    @property
    def is_low_stock(self):
        """Check if stock is low"""
        return 0 < self.stock_quantity <= self.low_stock_threshold
    
    @property
    def is_out_of_stock(self):
        """Check if out of stock"""
        return self.stock_quantity == 0
    
    def reduce_stock(self, quantity):
        """Reduce stock quantity"""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.sold_count += quantity
            self.save(update_fields=['stock_quantity', 'sold_count'])
            return True
        return False
    
    def update_rating(self, new_rating):
        """Update product rating"""
        total = self.rating * self.review_count + new_rating
        self.review_count += 1
        self.rating = total / self.review_count
        self.save(update_fields=['rating', 'review_count'])

class Order(TimestampedModel):
    """Customer order"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='orders')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    shipping = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    shipping_address = models.JSONField()
    billing_address = models.JSONField()
    
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=20, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    
    notes = models.TextField(blank=True)
    
    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-placed_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status', '-placed_at']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    def calculate_total(self):
        """Calculate order total"""
        self.total = self.subtotal + self.tax + self.shipping - self.discount
        return self.total
    
    def update_status(self, new_status):
        """Update order status"""
        self.status = new_status
        
        if new_status == 'shipped':
            self.shipped_at = timezone.now()
        elif new_status == 'delivered':
            self.delivered_at = timezone.now()
        
        self.save()
    
    @property
    def is_completed(self):
        """Check if order is completed"""
        return self.status in ['delivered', 'cancelled', 'refunded']

class OrderItem(TimestampedModel):
    """Order line item"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of order
    
    @property
    def subtotal(self):
        """Calculate item subtotal"""
        return self.price * self.quantity
```

**Usage:**

```python
# Create product
product = Product.objects.create(
    name="Wireless Headphones",
    sku="WH-001",
    price=99.99,
    stock_quantity=50,
    category=electronics
)

# Check stock
if product.is_low_stock:
    alert_admin("Low stock alert")

# Process sale
if product.reduce_stock(1):
    # Create order
    order = Order.objects.create(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        user=user,
        subtotal=product.price,
        tax=product.price * 0.1,
        shipping=5.00,
        total=product.price * 1.1 + 5.00
    )
    
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price=product.price
    )
    
    order.update_status('processing')
```

### Pattern 3: API Integration

```python
# serializers.py
from rest_framework import serializers
from .models import Post, Category

class PostSerializer(serializers.ModelSerializer):
    """Post serializer with nested fields"""
    
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_published = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'excerpt',
            'author', 'author_name', 'category', 'category_name',
            'status', 'is_published', 'published_at',
            'views_count', 'created_at', 'updated_at',
            'seo_title', 'seo_description', 'seo_keywords'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'views_count']
    
    def validate(self, data):
        """Custom validation"""
        if data.get('status') == 'published' and not data.get('published_at'):
            data['published_at'] = timezone.now()
        return data

# views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Post
from .serializers import PostSerializer
from .filters import PostFilter

class PostViewSet(viewsets.ModelViewSet):
    """Post API viewset with all features"""
    
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PostFilter
    search_fields = ['title', 'content', 'excerpt']
    ordering_fields = ['created_at', 'updated_at', 'published_at', 'views_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Optimize queryset"""
        queryset = super().get_queryset()
        
        # Select related fields to avoid N+1
        queryset = queryset.select_related('author', 'category')
        
        # Prefetch tags
        queryset = queryset.prefetch_related('tags')
        
        return queryset
    
    def perform_create(self, serializer):
        """Set author on creation"""
        serializer.save(author=self.request.user)
    
    def perform_update(self, serializer):
        """Track changes with audit info"""
        instance = self.get_object()
        instance._audit_user = self.request.user
        instance._audit_ip = self.request.META.get('REMOTE_ADDR')
        instance._audit_ua = self.request.META.get('HTTP_USER_AGENT', '')
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish post"""
        post = self.get_object()
        post.publish()
        
        # Create audit log
        AuditLog.objects.create(
            action="publish",
            content_type=ContentType.objects.get_for_model(post),
            object_id=post.pk,
            object_repr=str(post),
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'status': 'published'})
    
    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """Increment view counter"""
        post = self.get_object()
        post.increment_views()
        return Response({'views_count': post.views_count})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get post statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'published': queryset.filter(status='published').count(),
            'draft': queryset.filter(status='draft').count(),
            'archived': queryset.filter(status='archived').count(),
            'total_views': queryset.aggregate(models.Sum('views_count'))['views_count__sum'],
            'most_viewed': PostSerializer(queryset.order_by('-views_count').first()).data,
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent posts"""
        days = int(request.query_params.get('days', 7))
        posts = self.get_queryset().recent(days=days)
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
```

**API Endpoints:**

```
GET    /api/posts/                 # List posts (filterable)
POST   /api/posts/                 # Create post
GET    /api/posts/{id}/            # Retrieve post
PUT    /api/posts/{id}/            # Update post
PATCH  /api/posts/{id}/            # Partial update
DELETE /api/posts/{id}/            # Soft delete post

POST   /api/posts/{id}/publish/    # Publish post
POST   /api/posts/{id}/increment_views/  # Increment views
GET    /api/posts/stats/            # Get statistics
GET    /api/posts/recent/?days=7    # Recent posts
```

---

## Performance Optimization

### 1. Database Indexes

```python
class OptimizedModel(models.Model):
    """Model with optimized indexes"""
    
    # Index single fields
    status = models.CharField(max_length=20, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    
    class Meta:
        indexes = [
            # Composite index for common queries
            models.Index(fields=['status', '-created_at']),
            
            # Partial index (PostgreSQL)
            models.Index(
                fields=['user'],
                condition=Q(status='active'),
                name='active_user_idx'
            ),
            
            # Expression index (PostgreSQL)
            models.Index(
                F('lower(name)'),
                name='lower_name_idx'
            ),
        ]
```

### 2. Query Optimization

```python
# views.py
class OptimizedViewSet(viewsets.ModelViewSet):
    
    def get_queryset(self):
        """Optimize queryset"""
        queryset = super().get_queryset()
        
        # Use select_related for foreign keys
        queryset = queryset.select_related(
            'author',
            'category'
        )
        
        # Use prefetch_related for many-to-many
        queryset = queryset.prefetch_related(
            'tags',
            Prefetch(
                'comments',
                queryset=Comment.objects.filter(approved=True),
                to_attr='approved_comments'
            )
        )
        
        # Only get needed fields
        if not self.request.user.is_staff:
            queryset = queryset.only(
                'id', 'title', 'excerpt', 'slug',
                'published_at', 'author__username'
            )
        
        return queryset
    
    def list(self, request):
        """Optimized list view"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Count efficiently
        count = queryset.count()
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'count': count,
                'results': serializer.data
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': count,
            'results': serializer.data
        })
```

### 3. Caching

```python
from django.core.cache import cache

class CachedModelMixin:
    """Mixin for model caching"""
    
    def save(self, *args, **kwargs):
        """Clear cache on save"""
        super().save(*args, **kwargs)
        cache.delete(self._cache_key())
    
    def delete(self, *args, **kwargs):
        """Clear cache on delete"""
        cache.delete(self._cache_key())
        return super().delete(*args, **kwargs)
    
    def _cache_key(self):
        """Generate cache key"""
        return f"{self._meta.model_name}:{self.pk}"
    
    @classmethod
    def get_cached(cls, pk):
        """Get cached instance"""
        key = f"{cls._meta.model_name}:{pk}"
        instance = cache.get(key)
        
        if not instance:
            try:
                instance = cls.objects.get(pk=pk)
                cache.set(key, instance, timeout=3600)
            except cls.DoesNotExist:
                return None
        
        return instance

class Post(CachedModelMixin, TimestampedModel):
    """Post with caching"""
    title = models.CharField(max_length=200)
    content = models.TextField()

# Usage
post = Post.get_cached('550e8400-e29b-41d4-a716-446655440000')  # Gets from cache if available
```

### 4. Bulk Operations

```python
# Efficient bulk operations
def bulk_publish_posts(post_ids):
    """Publish multiple posts efficiently"""
    Post.objects.filter(id__in=post_ids).update(
        status='published',
        published_at=timezone.now()
    )

def bulk_delete_posts(post_ids):
    """Soft delete multiple posts"""
    Post.objects.filter(id__in=post_ids).delete()  # Uses custom delete()

def bulk_restore_posts(post_ids):
    """Restore multiple posts"""
    Post.objects.filter(id__in=post_ids, deleted_at__isnull=False).update(
        deleted_at=None
    )
```

### 5. QuerySet Caching

```python
class CachedQuerySet(QuerySet):
    """QuerySet with caching"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._result_cache = None
    
    def _fetch_all(self):
        """Fetch with caching"""
        if self._result_cache is None:
            cache_key = self._cache_key()
            self._result_cache = cache.get(cache_key)
            
            if self._result_cache is None:
                super()._fetch_all()
                cache.set(cache_key, self._result_cache, timeout=300)
    
    def _cache_key(self):
        """Generate cache key for query"""
        return f"queryset:{hash(str(self.query))}"
```

### 6. Monitoring Queries

```python
import time
from django.db import connection, reset_queries

def profile_queries(func):
    """Decorator to profile database queries"""
    def wrapper(*args, **kwargs):
        reset_queries()
        start = time.time()
        
        result = func(*args, **kwargs)
        
        end = time.time()
        queries = len(connection.queries)
        
        print(f"Function: {func.__name__}")
        print(f"Queries: {queries}")
        print(f"Time: {end - start:.3f}s")
        
        for i, query in enumerate(connection.queries[:5]):  # First 5
            print(f"{i+1}. {query['sql'][:100]}...")
        
        return result
    
    return wrapper

# Usage
@profile_queries
def get_dashboard_data():
    posts = Post.objects.select_related('author').prefetch_related('tags')[:10]
    return PostSerializer(posts, many=True).data
```

---

## Testing Strategies

### 1. Model Tests

```python
# tests/test_models.py
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from apps.blog.models import Post, Category
from apps.users.models import CustomUser

class PostModelTest(TestCase):
    """Test Post model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = CustomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            username="testuser"
        )
        self.category = Category.objects.create(
            name="Technology",
            slug="technology"
        )
        self.post = Post.objects.create(
            title="Test Post",
            content="Test content",
            author=self.user,
            category=self.category
        )
    
    def test_post_creation(self):
        """Test post creation"""
        self.assertEqual(self.post.title, "Test Post")
        self.assertEqual(self.post.author, self.user)
        self.assertEqual(self.post.status, "draft")
        self.assertIsNotNone(self.post.id)
        self.assertIsNotNone(self.post.created_at)
        self.assertIsNotNone(self.post.updated_at)
    
    def test_post_str_method(self):
        """Test string representation"""
        self.assertEqual(str(self.post), "Test Post")
    
    def test_post_publish(self):
        """Test publishing post"""
        self.post.publish()
        
        self.assertEqual(self.post.status, "published")
        self.assertIsNotNone(self.post.published_at)
        self.assertTrue(self.post.is_published)
    
    def test_post_unpublish(self):
        """Test unpublishing post"""
        self.post.publish()
        self.post.unpublish()
        
        self.assertEqual(self.post.status, "draft")
    
    def test_post_archive(self):
        """Test archiving post"""
        self.post.archive()
        
        self.assertEqual(self.post.status, "archived")
    
    def test_post_soft_delete(self):
        """Test soft delete"""
        post_id = self.post.id
        self.post.delete()
        
        # Should not be in default queryset
        self.assertFalse(Post.objects.filter(id=post_id).exists())
        
        # Should be in all_with_deleted
        self.assertTrue(Post.objects.all_with_deleted().filter(id=post_id).exists())
        self.assertTrue(self.post.is_deleted)
    
    def test_post_restore(self):
        """Test restoring deleted post"""
        self.post.delete()
        self.post.restore()
        
        self.assertFalse(self.post.is_deleted)
        self.assertTrue(Post.objects.filter(id=self.post.id).exists())
    
    def test_post_increment_views(self):
        """Test view counter"""
        self.assertEqual(self.post.views_count, 0)
        
        self.post.increment_views()
        self.post.refresh_from_db()
        
        self.assertEqual(self.post.views_count, 1)
    
    def test_excerpt_auto_generation(self):
        """Test excerpt generation"""
        long_content = "A" * 1000
        post = Post.objects.create(
            title="Long Post",
            content=long_content,
            author=self.user
        )
        
        self.assertEqual(len(post.excerpt), 500)
        self.assertTrue(post.excerpt.endswith('...'))
    
    def test_change_tracking(self):
        """Test change tracking"""
        initial_log = self.post.change_log.copy()
        
        self.post.title = "Updated Title"
        self.post.save()
        
        self.assertNotEqual(self.post.change_log, initial_log)
        
        # Check log structure
        latest_timestamp = max(self.post.change_log.keys())
        changes = self.post.change_log[latest_timestamp]
        self.assertIn('title', changes)
        self.assertEqual(changes['title']['old'], "Test Post")
        self.assertEqual(changes['title']['new'], "Updated Title")

class PostManagerTest(TestCase):
    """Test Post manager methods"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        
        # Create posts with different dates
        now = timezone.now()
        
        self.post1 = Post.objects.create(
            title="Recent Post",
            content="Content",
            author=self.user,
            created_at=now - timedelta(days=2)
        )
        
        self.post2 = Post.objects.create(
            title="Old Post",
            content="Content",
            author=self.user,
            created_at=now - timedelta(days=15)
        )
        
        self.post3 = Post.objects.create(
            title="Deleted Post",
            content="Content",
            author=self.user
        )
        self.post3.delete()
    
    def test_recent_method(self):
        """Test recent() manager method"""
        recent_posts = Post.objects.recent(days=7)
        self.assertIn(self.post1, recent_posts)
        self.assertNotIn(self.post2, recent_posts)
    
    def test_older_than_method(self):
        """Test older_than() manager method"""
        old_posts = Post.objects.older_than(days=7)
        self.assertIn(self.post2, old_posts)
        self.assertNotIn(self.post1, old_posts)
    
    def test_all_with_deleted(self):
        """Test all_with_deleted() manager method"""
        all_posts = Post.objects.all_with_deleted()
        self.assertEqual(all_posts.count(), 3)
    
    def test_deleted_method(self):
        """Test deleted() manager method"""
        deleted_posts = Post.objects.deleted()
        self.assertEqual(deleted_posts.count(), 1)
        self.assertIn(self.post3, deleted_posts)
```

### 2. Manager Tests

```python
# tests/test_managers.py
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.core.models import SoftDeleteModel, TimestampedModel
from apps.blog.models import Post

class SoftDeleteManagerTest(TestCase):
    """Test SoftDeleteManager functionality"""
    
    def setUp(self):
        self.post1 = Post.objects.create(title="Post 1", content="Content")
        self.post2 = Post.objects.create(title="Post 2", content="Content")
        self.post3 = Post.objects.create(title="Post 3", content="Content")
        
        self.post2.delete()
        self.post3.delete()
    
    def test_default_queryset_excludes_deleted(self):
        """Test default queryset excludes deleted records"""
        posts = Post.objects.all()
        self.assertEqual(posts.count(), 1)
        self.assertIn(self.post1, posts)
        self.assertNotIn(self.post2, posts)
    
    def test_all_with_deleted_includes_all(self):
        """Test all_with_deleted includes deleted records"""
        posts = Post.objects.all_with_deleted()
        self.assertEqual(posts.count(), 3)
    
    def test_deleted_returns_only_deleted(self):
        """Test deleted returns only deleted records"""
        posts = Post.objects.deleted()
        self.assertEqual(posts.count(), 2)
        self.assertIn(self.post2, posts)
        self.assertIn(self.post3, posts)
    
    def test_restore_all_restores_deleted(self):
        """Test restore_all restores all deleted records"""
        Post.objects.restore_all()
        
        posts = Post.objects.all()
        self.assertEqual(posts.count(), 3)
    
    def test_bulk_delete(self):
        """Test bulk soft delete"""
        Post.objects.filter(title__startswith="Post").delete()
        
        self.assertEqual(Post.objects.all().count(), 0)
        self.assertEqual(Post.objects.deleted().count(), 3)
    
    def test_bulk_restore(self):
        """Test bulk restore"""
        Post.objects.deleted().restore()
        
        self.assertEqual(Post.objects.all().count(), 3)
        self.assertEqual(Post.objects.deleted().count(), 0)

class TimestampedManagerTest(TestCase):
    """Test TimestampedManager functionality"""
    
    def setUp(self):
        now = timezone.now()
        
        self.post1 = Post.objects.create(
            title="Post 1",
            content="Content",
            created_at=now - timedelta(days=1)
        )
        
        self.post2 = Post.objects.create(
            title="Post 2",
            content="Content",
            created_at=now - timedelta(days=10)
        )
        
        self.post3 = Post.objects.create(
            title="Post 3",
            content="Content",
            created_at=now - timedelta(days=30)
        )
    
    def test_recent_days_filter(self):
        """Test recent days filter"""
        recent = Post.objects.recent(days=7)
        self.assertEqual(recent.count(), 1)
        self.assertIn(self.post1, recent)
    
    def test_older_than_filter(self):
        """Test older than filter"""
        old = Post.objects.older_than(days=15)
        self.assertEqual(old.count(), 1)
        self.assertIn(self.post3, old)
    
    def test_updated_since_filter(self):
        """Test updated since filter"""
        cutoff = timezone.now() - timedelta(hours=1)
        self.post2.save()  # Update timestamp
        
        updated = Post.objects.updated_since(cutoff)
        self.assertIn(self.post2, updated)
        self.assertNotIn(self.post1, updated)
```

### 3. Integration Tests

```python
# tests/test_integration.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from apps.blog.models import Post, Category
from apps.users.models import CustomUser

class PostAPITest(APITestCase):
    """Test Post API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user = CustomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            username="testuser"
        )
        
        self.category = Category.objects.create(
            name="Technology",
            slug="technology"
        )
        
        self.post = Post.objects.create(
            title="Test Post",
            content="Test content",
            author=self.user,
            category=self.category
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_list_posts(self):
        """Test listing posts"""
        url = reverse('post-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_post(self):
        """Test creating post"""
        url = reverse('post-list')
        data = {
            'title': 'New Post',
            'content': 'New content',
            'category': self.category.id
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 2)
        self.assertEqual(Post.objects.last().author, self.user)
    
    def test_publish_post(self):
        """Test publishing post via API"""
        url = reverse('post-publish', args=[self.post.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_published)
    
    def test_filter_posts(self):
        """Test filtering posts"""
        # Create another post
        Post.objects.create(
            title="Another Post",
            content="Content",
            author=self.user,
            status="published"
        )
        
        url = reverse('post-list')
        response = self.client.get(url, {'status': 'published'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], "Another Post")
    
    def test_search_posts(self):
        """Test searching posts"""
        url = reverse('post-list')
        response = self.client.get(url, {'search': 'Test'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], "Test Post")
    
    def test_recent_posts_endpoint(self):
        """Test recent posts endpoint"""
        url = reverse('post-recent')
        response = self.client.get(url, {'days': 7})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_stats_endpoint(self):
        """Test stats endpoint"""
        url = reverse('post-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['published'], 0)
        self.assertEqual(response.data['draft'], 1)
```

### 4. Audit Log Tests

```python
# tests/test_audit.py
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from apps.core.models import AuditLog
from apps.blog.models import Post
from apps.users.models import CustomUser
import uuid

class AuditLogTest(TestCase):
    """Test audit logging"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        
        # Set audit context
        self.post = Post(
            title="Test Post",
            content="Content",
            author=self.user
        )
        self.post._audit_user = self.user
        self.post._audit_ip = "127.0.0.1"
        self.post._audit_ua = "Test Agent"
        self.post.save()
    
    def test_create_audit_log(self):
        """Test audit log on create"""
        logs = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Post),
            object_id=self.post.id
        )
        
        self.assertEqual(logs.count(), 1)
        
        log = logs.first()
        self.assertEqual(log.action, "create")
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.ip_address, "127.0.0.1")
        self.assertEqual(log.user_agent, "Test Agent")
        self.assertIn('title', log.changes)
    
    def test_update_audit_log(self):
        """Test audit log on update"""
        self.post._audit_user = self.user
        self.post.title = "Updated Title"
        self.post.save()
        
        logs = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Post),
            object_id=self.post.id,
            action="update"
        )
        
        self.assertEqual(logs.count(), 1)
        
        log = logs.first()
        self.assertIn('title', log.changes)
        self.assertEqual(log.changes['title']['old'], "Test Post")
        self.assertEqual(log.changes['title']['new'], "Updated Title")
    
    def test_delete_audit_log(self):
        """Test audit log on delete"""
        self.post._audit_user = self.user
        self.post.delete()
        
        logs = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Post),
            object_id=self.post.id,
            action="delete"
        )
        
        self.assertEqual(logs.count(), 1)
        
    def test_uuid_formatting_in_audit_log(self):
        """Test that UUIDs are stored as strings with hyphens"""
        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Post),
            object_id=self.post.id
        ).first()
        
        # Check that object_id is a string with hyphens
        self.assertIsInstance(log.object_id, str)
        self.assertEqual(len(log.object_id), 36)  # UUID with hyphens
        self.assertIn('-', log.object_id)
```

---

## Best Practices

### 1. Model Design

✅ **DO:**

```python
class Article(SoftDeleteModel, PublishableModel, SEOModel, ChangeTrackingModel):
    """Single responsibility model with proper inheritance"""
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return self.title
```

❌ **DON'T:**

```python
class Article(models.Model):  # Missing base classes
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)  # Reinventing UUIDModel
    created_at = models.DateTimeField(auto_now_add=True)  # Redundant with TimestampedModel
    updated_at = models.DateTimeField(auto_now=True)  # Redundant
    deleted_at = models.DateTimeField(null=True)  # Reinventing soft delete
    
    # Too many fields, mixed responsibilities
    title = models.CharField(max_length=200)
    content = models.TextField()
    seo_title = models.CharField(max_length=60)  # Should use SEOModel
    seo_description = models.CharField(max_length=160)  # Should use SEOModel
    slug = models.SlugField()  # Should use SEOModel
    status = models.CharField(max_length=20)  # Should use PublishableModel
```

### 2. Manager Usage

✅ **DO:**

```python
# Use manager methods for common queries
active_posts = Post.objects.active()
recent_posts = Post.objects.recent(days=7)
published_posts = Post.objects.filter(status='published')

# Chain methods
results = Post.objects.active()\
    .filter(category=tech)\
    .recent(days=30)\
    .select_related('author')
```

❌ **DON'T:**

```python
# Don't manually filter deleted
posts = Post.objects.filter(deleted_at__isnull=True)

# Don't recreate date logic
cutoff = timezone.now() - timedelta(days=7)
recent = Post.objects.filter(created_at__gte=cutoff)
```

### 3. Soft Delete Handling

✅ **DO:**

```python
# Use soft delete by default
post.delete()  # Soft delete

# Hard delete only when necessary
post.hard_delete()

# Restore when needed
post.restore()

# Bulk operations
Post.objects.filter(status='draft').delete()
Post.objects.deleted().restore()
```

❌ **DON'T:**

```python
# Don't bypass soft delete unnecessarily
Post.objects.filter(id=post.id).delete()  # Bulk delete ignores soft delete

# Don't forget to check deleted status
if not post.is_deleted:
    process_post(post)
```

### 4. Change Tracking

✅ **DO:**

```python
# Let it work automatically
post.title = "New Title"
post.save()  # Changes are tracked

# Access change log when needed
changes = post.change_log

# Use for audit purposes
if 'price' in latest_changes:
    alert_finance_team()
```

❌ **DON'T:**

```python
# Don't manually track changes
post._old_title = post.title
post.title = "New Title"
if post._old_title != post.title:
    log_change(post)  # Redundant with ChangeTrackingModel
```

### 5. Audit Logging

✅ **DO:**

```python
# Set audit context
post._audit_user = request.user
post._audit_ip = request.META.get('REMOTE_ADDR')
post.save()

# Or use context manager
with audit_context(user=request.user):
    post.publish()
    
# Query logs for compliance
user_actions = AuditLog.objects.filter(user=user)
```

❌ **DON'T:**

```python
# Don't log manually
log_entry = f"User {user} changed post {post.id}"  # Use AuditLog instead

# Don't forget IP and user agent
post.save()  # No audit context means no tracking
```

### 6. UUID Handling

✅ **DO:**

```python
# In models, let Django handle UUID conversion
class MyModel(UUIDModel):
    name = models.CharField(max_length=100)

# When querying, use strings
obj = MyModel.objects.get(id="550e8400-e29b-41d4-a716-446655440000")

# In signals, ensure UUIDs are strings
@receiver(post_save)
def log_save(sender, instance, **kwargs):
    object_id = str(instance.pk) if isinstance(instance.pk, uuid.UUID) else instance.pk
    # Use object_id...
```

❌ **DON'T:**

```python
# Don't assume UUID objects everywhere
obj = MyModel.objects.get(id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))  # Works but verbose

# Don't forget to convert UUIDs to strings for logging
object_id = instance.pk  # Might be UUID object, causing issues in JSON serialization
```

### 7. Performance

✅ **DO:**

```python
# Use select_related for foreign keys
posts = Post.objects.select_related('author', 'category')

# Use prefetch_related for many-to-many
posts = Post.objects.prefetch_related('tags')

# Use only() for specific fields
posts = Post.objects.only('id', 'title', 'slug')

# Add indexes for filtered fields
class Meta:
    indexes = [
        models.Index(fields=['status', '-created_at']),
    ]
```

❌ **DON'T:**

```python
# Don't cause N+1 queries
for post in Post.objects.all():
    print(post.author.username)  # Extra query per post

# Don't fetch unnecessary fields
posts = Post.objects.all()  # Fetches all fields

# Don't filter on non-indexed fields
Post.objects.filter(status='published')  # Should have index
```

### 8. Testing

✅ **DO:**

```python
class PostTest(TestCase):
    def setUp(self):
        self.post = Post.objects.create(title="Test")
    
    def test_publish(self):
        self.post.publish()
        self.assertTrue(self.post.is_published)
        self.assertIsNotNone(self.post.published_at)
    
    def test_uuid_format(self):
        """Test that UUID is stored as string"""
        self.assertIsInstance(self.post.id, str)
        self.assertEqual(len(self.post.id), 36)
        self.assertIn('-', self.post.id)
```

❌ **DON'T:**

```python
def test_post():
    post = Post.objects.create(title="Test")
    post.publish()
    assert post.is_published  # No assertions, no test isolation
```

### 9. Error Handling

✅ **DO:**

```python
try:
    post.publish()
except Exception as e:
    logger.error(f"Failed to publish post {post.id}: {e}")
    raise
```

❌ **DON'T:**

```python
post.publish()  # No error handling
```

### 10. Documentation

✅ **DO:**

```python
class Post(SoftDeleteModel, PublishableModel, SEOModel, ChangeTrackingModel):
    """
    Blog post model with publishing workflow.
    
    Features:
    - UUID primary key
    - Soft delete with restore
    - Draft/published/archived states
    - Automatic slug generation
    - SEO fields (title, description, keywords)
    - Change tracking
    - Timestamps (created, updated)
    """
    
    title = models.CharField(
        max_length=200,
        help_text="Post title (required)"
    )
```

❌ **DON'T:**

```python
class Post(models.Model):
    title = models.CharField(max_length=200)  # No help text, no class docstring
```

---

## Summary

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **UUIDModel** | Base model | UUID primary key |
| **TimestampedModel** | Time tracking | created_at, updated_at |
| **SoftDeleteModel** | Safe deletion | deleted_at, restore() |
| **ChangeTrackingModel** | Field changes | JSON change log |
| **PublishableModel** | Content workflow | draft/published/archived |
| **SEOModel** | SEO fields | slug, seo_title, etc. |
| **CustomUser** | Enhanced user | Email login, verification |
| **AuditLog** | Action history | Generic audit trail |
| **SoftDeleteManager** | Query filtering | active(), deleted() |
| **CustomUserManager** | User queries | verified(), recently_joined() |
| **TimestampedManager** | Time queries | recent(), older_than() |

---

## Next Steps

1. **Choose base classes** for your models
2. **Set up AUTH_USER_MODEL** before first migration
3. **Add indexes** for filtered fields
4. **Implement audit logging** for critical models
5. **Write tests** for model behavior
6. **Create serializers** for API
7. **Add filters** for list views
8. **Monitor performance** and optimize
9. **Document your models** thoroughly

---

**Key Takeaways:**

- Use **UUIDModel** for distributed-friendly IDs
- Use **SoftDeleteModel** for safe deletion
- Use **PublishableModel** for content workflows
- Use **ChangeTrackingModel** for audit requirements
- Use **SEOModel** for SEO-optimized content
- Use **CustomUser** for enhanced user features
- Use **AuditLog** for compliance
- **Always convert UUIDs to strings** in signals and logs
- **Add indexes** for filtered fields
- **Write comprehensive tests**
- **Document your models** thoroughly
- **Use manager methods** instead of manual filtering