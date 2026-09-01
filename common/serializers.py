"""Reusable serializers and validation helpers.

Provides a base auditable serializer and file/image validators for API input.
"""

from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

User = get_user_model()


class AuditableSerializer(serializers.ModelSerializer):
    """Base serializer exposing read-only timestamps and request context helpers."""

    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%dT%H:%M:%SZ")
    updated_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%dT%H:%M:%SZ")

    class Meta:
        abstract = True

    def _get_user_from_context(self):
        """Return the authenticated user from serializer context."""
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def _get_request_metadata(self):
        """Return IP and user-agent metadata from the request."""
        request = self.context.get("request")
        if not request:
            return {}
        return {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }


def validate_file_size(value, max_size_mb: int = 5):
    """Validate that an uploaded file does not exceed the size limit."""
    max_size_bytes = max_size_mb * 1024 * 1024
    if value.size > max_size_bytes:
        raise ValidationError(_(f"File size must be less than {max_size_mb}MB"))
    return value


def validate_file_extension(value, allowed_extensions: List[str]):
    """Validate that a file's extension is in the allowed list."""
    import os

    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            _(f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")
        )
    return value


def validate_image_type(value):
    """Validate that an uploaded file is an allowed image MIME type."""
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if hasattr(value, "content_type") and value.content_type not in allowed_types:
        raise ValidationError(_("Invalid image type. Allowed types: JPEG, PNG, GIF, WebP"))
    return value
