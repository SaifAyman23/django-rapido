"""Notification inbox and device registry views.

Provide user-scoped notification listing and FCM device management.
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.views import BaseViewSet

from .models import Device, Notification
from .serializers import DeviceSerializer, NotificationSerializer


class NotificationViewSet(BaseViewSet):
    """User-scoped notification inbox with read-state helpers."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return notifications for the current user ordered newest first."""
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        """List notifications and inject the cached unread count."""
        # Reuse cached counter to avoid extra count query.
        from .tasks import get_unread_count

        response = super().list(request, *args, **kwargs)
        response.data["unread_count"] = get_unread_count(str(request.user.id))
        return response

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a notification and mark it as read."""
        obj = self.get_object()
        obj.is_read = True
        obj.save(update_fields=["is_read"])
        from .tasks import _invalidate_unread_count_cache

        _invalidate_unread_count_cache(str(request.user.id))
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None):
        """Mark a single notification as read."""
        obj = self.get_object()
        obj.is_read = True
        obj.save(update_fields=["is_read"])
        from .tasks import _invalidate_unread_count_cache

        _invalidate_unread_count_cache(str(request.user.id))
        return Response({"is_read": True})

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        """Mark all of the current user's unread notifications as read."""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        from .tasks import _invalidate_unread_count_cache

        _invalidate_unread_count_cache(str(request.user.id))
        return Response({"marked": True})


class DeviceViewSet(BaseViewSet):
    """Device registry — upserts on (user, device_uuid) for FCM push."""

    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return devices owned by the current user."""
        return Device.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Register or update a device token for the current user."""
        token = request.data.get("token")
        device_uuid = request.data.get("device_uuid")
        if not token or not device_uuid:
            return Response(
                {"error": "token and device_uuid required"}, status=status.HTTP_400_BAD_REQUEST
            )

        device, created = Device.objects.update_or_create(
            user=request.user,
            device_uuid=device_uuid,
            defaults={
                "token": token,
                "platform": request.data.get("platform", "web"),
                "device_name": request.data.get("device_name", ""),
                "is_active": True,
                "last_seen_at": timezone.now(),
                "last_token_refresh_at": timezone.now(),
            },
        )
        return Response(
            DeviceSerializer(device).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="unregister")
    def unregister(self, request):
        """Deactivate a device so it no longer receives push notifications."""
        device_uuid = request.data.get("device_uuid")
        if not device_uuid:
            return Response({"error": "device_uuid required"}, status=status.HTTP_400_BAD_REQUEST)
        Device.objects.filter(user=request.user, device_uuid=device_uuid).update(is_active=False)
        return Response({"deactivated": True})
