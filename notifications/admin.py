"""REUSE: Admin for notifications inbox."""

from django.contrib import admin

from common.unfold_admin_bases import BaseAdmin

from .models import Device, Notification


@admin.register(Notification)
class NotificationAdmin(BaseAdmin):
    list_display = ["user", "type", "title", "is_read", "created_at"]
    list_filter = ["type", "is_read"]
    search_fields = ["user__email", "title", "body"]


@admin.register(Device)
class DeviceAdmin(BaseAdmin):
    list_display = [
        "user",
        "platform",
        "device_uuid",
        "is_active",
        "notifications_enabled",
        "last_seen_at",
    ]
    list_filter = ["platform", "is_active"]
    search_fields = ["user__email", "token", "device_uuid"]
