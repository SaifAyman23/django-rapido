"""
REUSE: Generic contact models — public message + singleton info.

From ras-elbar-go/backend/contacts/models.py — project-agnostic.
ContactMessage: public POST no auth (AllowAny)
ContactInfo: singleton with hours + socials + geo
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import TimestampedModel, UUIDModel


class ContactMessage(TimestampedModel, UUIDModel):
    """Public contact form submission from unauthenticated visitors."""

    name = models.CharField(_("name"), max_length=255)
    email = models.EmailField(_("email"))
    subject = models.CharField(_("subject"), max_length=255)
    message = models.TextField(_("message"))

    class Meta:
        verbose_name = _("contact message")
        verbose_name_plural = _("contact messages")
        ordering = ["-created_at"]

    def __str__(self):
        """Return a short label for admin lists."""
        return f"{self.name} - {self.subject}"


class ContactInfo(TimestampedModel, UUIDModel):
    """REUSE: Singleton — business hours feed is_ordering_open() check."""

    address = models.TextField(_("address"), blank=True, default="")
    phone = models.CharField(_("phone"), max_length=50, blank=True, default="")
    email = models.EmailField(_("email"), blank=True, default="")
    working_hours = models.TextField(_("working hours"), blank=True, default="")
    # REUSE: start/end hours gated via BUSINESS_TIME_ZONE
    start_hours = models.TimeField(_("start hours"), null=True, blank=True)
    end_hours = models.TimeField(_("end hours"), null=True, blank=True)
    facebook_url = models.URLField(_("Facebook URL"), blank=True, default="")
    instagram_url = models.URLField(_("Instagram URL"), blank=True, default="")
    twitter_url = models.URLField(_("Twitter/X URL"), blank=True, default="")
    linkedin_url = models.URLField(_("LinkedIn URL"), blank=True, default="")
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("longitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )

    class Meta:
        verbose_name = _("contact info")
        verbose_name_plural = _("contact info")

    def __str__(self):
        return "Contact Info"

    def save(self, *args, **kwargs):
        """Enforce singleton — only one ContactInfo row allowed."""
        if not self.pk and ContactInfo.objects.exists():
            raise ValidationError(_("Only one ContactInfo instance is allowed."))
        super().save(*args, **kwargs)
