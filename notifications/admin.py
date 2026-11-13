"""REUSE: Admin for notifications inbox."""

from django.contrib import admin

from common.unfold_admin_bases import BaseAdmin

from .models import Device, Notification


@admin.register(Notification)
class NotificationAdmin(BaseAdmin):
    list_display = ["user", "type", "title", "is_read", "created_at"]
    list_filter = ["type", "is_read"]
    search_fields = ["user__email", "title", "body"]
    actions = ["broadcast_system"]

    @admin.action(description="Broadcast system notification to all users")
    def broadcast_system(self, request, queryset) -> None:
        from django.contrib.auth import get_user_model

        from .services import notify

        User = get_user_model()
        title = request.POST.get("title") or "System notification"
        body = request.POST.get("body") or ""
        recipients = User.objects.filter(is_active=True)
        count = 0
        for user in recipients.iterator():
            notify(user, type="SYSTEM", title=title, body=body)
            count += 1
        self.message_user(request, f"Broadcast queued for {count} users.")


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
