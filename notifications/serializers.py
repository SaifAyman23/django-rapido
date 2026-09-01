"""Notification and device serializers.

Provide in-app inbox and FCM device registration schemas.
"""

from rest_framework import serializers

from .models import Device, Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for in-app notification inbox entries."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "body",
            "related_object_id",
            "related_object_type",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for FCM device registrations."""

    class Meta:
        model = Device
        fields = [
            "id",
            "token",
            "device_uuid",
            "platform",
            "device_name",
            "is_active",
            "notifications_enabled",
            "last_seen_at",
        ]
        read_only_fields = ["id", "created_at"]


class DeviceRegisterSerializer(serializers.Serializer):
    """Serializer for registering a device via POST /notifications/devices/."""

    token = serializers.CharField()
    device_uuid = serializers.CharField()
    platform = serializers.ChoiceField(choices=["android", "ios", "web"])
    device_name = serializers.CharField(required=False, allow_blank=True, default="")
