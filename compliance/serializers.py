"""Compliance API serializers.

Exposes FAQ and legal document data for public read and admin write.
"""

from rest_framework import serializers

from .models import ComplianceDocument, FAQ, PolicyAcceptance, PolicyDocument


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


class PolicyListSerializer(serializers.ModelSerializer):
    """Row shown in Profile → Policies."""

    class Meta:
        model = PolicyDocument
        fields = ["slug", "title", "version"]


class PolicyListWithStatusSerializer(PolicyListSerializer):
    """List row extended with the authenticated user's consent status.

    ``accepted`` is true only when the user has accepted the *current* published
    version, mirroring server-side enforcement. A single query annotates every
    row, so the list stays O(number of policies).
    """

    accepted = serializers.SerializerMethodField()
    accepted_at = serializers.SerializerMethodField()

    class Meta(PolicyListSerializer.Meta):
        fields = PolicyListSerializer.Meta.fields + ["accepted", "accepted_at", "updated_at"]

    def get_accepted(self, obj):
        acceptances = self.context.get("acceptances") or {}
        entry = acceptances.get(obj.slug)
        return bool(entry and entry["version"] == obj.version)

    def get_accepted_at(self, obj):
        acceptances = self.context.get("acceptances") or {}
        entry = acceptances.get(obj.slug)
        if entry and entry["version"] == obj.version:
            return entry["created_at"]
        return None


class PolicyDetailSerializer(PolicyListSerializer):
    """Full Markdown text for one published policy."""

    class Meta(PolicyListSerializer.Meta):
        fields = ["slug", "title", "content", "version"]


class PolicyAcceptanceSerializer(serializers.ModelSerializer):
    """Consent receipt; ``accepted_at`` maps the row's creation timestamp."""

    accepted_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = PolicyAcceptance
        fields = ["policy_slug", "version", "accepted_at"]