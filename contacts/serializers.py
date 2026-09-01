"""Contact serializers for public message creation and business info."""

from rest_framework import serializers

from .models import ContactInfo, ContactMessage
from .services import is_ordering_open


class ContactMessageSerializer(serializers.ModelSerializer):
    """Serializer for public contact form submissions."""

    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "subject", "message", "created_at"]
        read_only_fields = ["id", "created_at"]


class ContactInfoSerializer(serializers.ModelSerializer):
    """Serializer for singleton business info with ordering availability flags."""

    ordering_open = serializers.SerializerMethodField()
    site_inactive = serializers.SerializerMethodField()

    class Meta:
        model = ContactInfo
        fields = [
            "id",
            "address",
            "phone",
            "email",
            "working_hours",
            "start_hours",
            "end_hours",
            "facebook_url",
            "instagram_url",
            "twitter_url",
            "linkedin_url",
            "latitude",
            "longitude",
            "ordering_open",
            "site_inactive",
        ]

    def get_ordering_open(self, obj):
        """Return whether ordering is currently open based on business hours."""
        is_open, _ = is_ordering_open()
        return is_open

    def get_site_inactive(self, obj):
        """Return whether the site should be treated as inactive (closed)."""
        is_open, _ = is_ordering_open()
        return not is_open
