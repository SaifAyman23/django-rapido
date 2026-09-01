"""
REUSE: Generic notification + device models — FCM + in-app inbox.

From ras-elbar-go/backend/notifications/models.py — made project-agnostic.
NotificationType is generic; add your domain events (ORDER_*, COMMENT_*, etc.)
RelatedObjectType is generic; use your domain (order, post, ticket).

Device model is the standard FCM registry — token unique, device_uuid stable
per install (uuid.v4 in secure storage), upsert on login.
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import TimestampedModel, UUIDModel

User = get_user_model()


class NotificationType(models.TextChoices):
    """REUSE: Generic event types — extend per project."""

    WELCOME = "welcome", _("Welcome")
    GENERIC = "generic", _("Generic")  # fallback
    # Examples — uncomment for your domain:
    # ORDER_SUBMITTED = "order_submitted", _("Order Submitted")
    # ORDER_COMPLETED = "order_completed", _("Order Completed")
    # COMMENT_CREATED = "comment_created", _("New Comment")
    # PAYMENT_RECEIVED = "payment_received", _("Payment Received")


class RelatedObjectType(models.TextChoices):
    """REUSE: Generic related object — extend per project."""

    ORDER = "order", _("Order")
    USER = "user", _("User")
    GENERIC = "generic", _("Generic")


class Notification(TimestampedModel, UUIDModel):
    """In-app notification inbox — one per user per event.

    REUSE: Query with Notification.objects.filter(user=request.user, is_read=False)
    Indexes on (user, is_read) and (user, type) for dashboard queries.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()
    related_object_id = models.UUIDField(null=True, blank=True)
    related_object_type = models.CharField(
        max_length=50, choices=RelatedObjectType.choices, null=True, blank=True
    )
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
            models.Index(fields=["user", "type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class DevicePlatform(models.TextChoices):
    ANDROID = "android", "Android"
    IOS = "ios", "iOS"
    WEB = "web", "Web"


class Device(TimestampedModel, UUIDModel):
    """FCM device registry — one row per (user, device_uuid).

    REUSE: Register via POST /notifications/devices/ {token, device_uuid, platform}
    Upsert via update_or_create(user, device_uuid). Unique token.
    Deactivate on logout: Device.objects.filter(user=user).update(is_active=False)
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    token = models.TextField(unique=True)
    device_uuid = models.CharField(max_length=255)
    platform = models.CharField(max_length=20, choices=DevicePlatform.choices)
    device_name = models.CharField(max_length=255, blank=True)
    device_model = models.CharField(max_length=255, blank=True)
    os_version = models.CharField(max_length=50, blank=True)
    app_version = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=10, blank=True)
    timezone = models.CharField(max_length=100, blank=True)
    notifications_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=True, help_text="Whether this token should receive notifications."
    )
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_token_refresh_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen_at", "-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["platform"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["last_seen_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "device_uuid"], name="unique_user_device"),
        ]

    def __str__(self):
        return f"{self.user} - {self.platform}"
