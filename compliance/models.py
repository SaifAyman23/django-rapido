"""
REUSE: Generic compliance CMS — FAQ + Legal docs.

From ras-elbar-go/backend/compliance/models.py — project-agnostic.
Add DocumentType values per project (e.g. COOKIE_POLICY, REFUND_POLICY).
Requires: modeltranslation for translatable fields + markdownx for admin.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import TimestampedModel, UUIDModel


class DocumentType(models.TextChoices):
    PRIVACY_POLICY = "PRIVACY_POLICY", _("Privacy Policy")
    TERMS_OF_SERVICE = "TERMS_OF_SERVICE", _("Terms of Service")
    # REUSE: add your legal docs:
    # COOKIE_POLICY = "COOKIE_POLICY", _("Cookie Policy")
    # REFUND_POLICY = "REFUND_POLICY", _("Refund Policy")


class FAQ(TimestampedModel, UUIDModel):
    """REUSE: Translatable Q&A — show on support page."""

    question = models.CharField(max_length=500)  # REUSE: translatable via translation.py
    answer = models.TextField(max_length=10000)  # REUSE: translatable, Markdown optional
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = _("FAQ")
        verbose_name_plural = _("FAQs")
        ordering = ["sort_order"]

    def __str__(self):
        return self.question


class ComplianceDocument(TimestampedModel, UUIDModel):
    """REUSE: Singleton per type — title+content translatable, Markdown."""

    type = models.CharField(max_length=30, choices=DocumentType.choices, unique=True)
    title = models.CharField(max_length=200)  # REUSE: translatable
    content = models.TextField(max_length=50000)  # REUSE: translatable, Markdown
    is_published = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Compliance Document")
        verbose_name_plural = _("Compliance Documents")

    def __str__(self):
        return self.title
