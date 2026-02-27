"""
Ultimate reusable abstract models, managers, and mixins
Provides production-grade base classes for rapid development with:
- UUID primary keys
- Soft deletes
- Change tracking
- Time-based queries
- Audit logging
- Performance optimization
"""

import uuid
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

from django.db import models
from django.db.models import QuerySet, Manager, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


# ===========================
# Custom Managers
# ===========================

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


# ===========================
# Abstract Base Models
# ===========================

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


# ===========================
# Custom User Model
# ===========================

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
        related_name='customuser_set',        # ← Add this
        related_query_name='customuser',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='customuser_set',        # ← Add this
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


@receiver(post_save, sender=CustomUser)
def log_user_creation(sender, instance, created, **kwargs):
    """Log user creation events"""
    if created:
        logger.info(f"New user created: {instance.id} ({instance.email})")


# ===========================
# Audit Trail Model
# ===========================

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
    # ContentType fields
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=~Q(app_label='common'),  # Optional: restrict to specific apps
        null=True,
        blank=True
    )
    object_id = models.UUIDField(  # matches your UUID PKs
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
