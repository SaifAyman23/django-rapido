"""Notification and device serializers.

Provide in-app inbox and FCM device registration schemas.
"""

from rest_framework import serializers

from .models import CustomReminder, Device, Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for in-app notification inbox entries."""

    link_status = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "body",
            "data",
            "related_object_id",
            "related_object_type",
            "is_read",
            "read_at",
            "scheduled_at",
            "delivery_status",
            "link_status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_link_status(self, obj) -> str | None:
        if obj.type != "COACH_REQUEST":
            return None
        link_id = (obj.data or {}).get("link_id")
        if not link_id:
            return None
        return self.context.get("link_status_by_id", {}).get(str(link_id))


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


class CustomReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomReminder
        fields = ["id", "name", "name_ar", "time", "days_of_week", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_days_of_week(self, value):
        if len(set(value)) != len(value) or any(
            not isinstance(day, int) or day < 0 or day > 6 for day in value
        ):
            raise serializers.ValidationError(
                "days_of_week must contain unique values from 0 to 6."
            )
        return value
