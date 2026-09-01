"""Compliance API serializers.

Exposes FAQ and legal document data for public read and admin write.
"""

from rest_framework import serializers

from .models import FAQ, ComplianceDocument


class FAQSerializer(serializers.ModelSerializer):
    """Serializer for FAQ entries."""

    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "sort_order", "is_published", "created_at"]
        read_only_fields = ["id", "created_at"]


class ComplianceDocumentSerializer(serializers.ModelSerializer):
    """Serializer for compliance/legal documents."""

    class Meta:
        model = ComplianceDocument
        fields = ["id", "type", "title", "content", "is_published", "created_at"]
        read_only_fields = ["id", "created_at"]
