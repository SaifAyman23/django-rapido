"""Notification inbox and device registry views.

Provide user-scoped notification listing and FCM device management.
"""

from typing import Any

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.views import BaseViewSet

from .models import Device, Notification
from .serializers import CustomReminderSerializer, DeviceSerializer, NotificationSerializer


class NotificationViewSet(BaseViewSet):
    """User-scoped notification inbox with read-state helpers."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_serializer_context(self):
        # Projects that model a linked object can inject its status here under
        # ``link_status_by_id``; the base template ships no such relation.
        return super().get_serializer_context()

    def get_queryset(self) -> Any:
        """Return notifications for the current user ordered newest first."""
        queryset = Notification.objects.filter(user=self.request.user).order_by("-created_at")
        return queryset[:100] if self.action == "list" else queryset

    def list(self, request, *args, **kwargs) -> Any:
        """List notifications and inject the cached unread count."""
        from .tasks import get_unread_count

        response = super().list(request, *args, **kwargs)
        if isinstance(response.data, dict):
            response.data["unread_count"] = get_unread_count(str(request.user.id))
        else:
            response.data = {
                "results": response.data,
                "unread_count": get_unread_count(str(request.user.id)),
            }
        return response

    def retrieve(self, request, *args, **kwargs) -> Any:
        """Retrieve a notification and mark it as read."""
        obj = self.get_object()
        obj.is_read = True
        obj.read_at = timezone.now()
        obj.save(update_fields=["is_read", "read_at", "updated_at"])
        from .tasks import _invalidate_unread_count_cache

        _invalidate_unread_count_cache(str(request.user.id))
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None) -> Any:
        """Mark a single notification as read."""
        obj = self.get_object()
        obj.is_read = True
        obj.read_at = timezone.now()
        obj.save(update_fields=["is_read", "read_at", "updated_at"])
        from .tasks import _invalidate_unread_count_cache

        _invalidate_unread_count_cache(str(request.user.id))
        return Response({"is_read": True})

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request) -> Any:
        """Mark all of the current user's unread notifications as read."""
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        from .tasks import _invalidate_unread_count_cache

        _invalidate_unread_count_cache(str(request.user.id))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request) -> Any:
        """Return the unread notification count for the current user."""
        from .tasks import get_unread_count

        return Response({"unread_count": get_unread_count(str(request.user.id))})


class DeviceViewSet(BaseViewSet):
    """Device registry — upserts on (user, device_uuid) for FCM push."""

    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> Any:
        """Return devices owned by the current user."""
        queryset = Device.objects.filter(user=self.request.user)
        return queryset[:50] if self.action == "list" else queryset

    def create(self, request, *args, **kwargs) -> Any:
        """Register or update a device token for the current user/account."""
        token = request.data.get("token")
        device_uuid = request.data.get("device_uuid")
        if not token or not device_uuid:
            return Response(
                {"error": "token and device_uuid required"}, status=status.HTTP_400_BAD_REQUEST
            )

        account = getattr(request, "active_account", None)
        # Upsert on (account, token) when an account is known, else (user, device_uuid).
        if account is not None:
            device, created = Device.objects.update_or_create(
                account=account,
                token=token,
                defaults={
                    "user": request.user,
                    "device_uuid": device_uuid,
                    "platform": request.data.get("platform", "web"),
                    "device_name": request.data.get("device_name", ""),
                    "is_active": True,
                    "last_seen_at": timezone.now(),
                    "last_token_refresh_at": timezone.now(),
                },
            )
        else:
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

        # Token handoff: drop the same token from other users' devices.
        Device.objects.filter(token=token).exclude(pk=device.pk).exclude(user=request.user).delete()

        return Response(
            DeviceSerializer(device).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="unregister")
    def unregister(self, request) -> Any:
        """Deactivate a device so it no longer receives push notifications."""
        device_uuid = request.data.get("device_uuid")
        if not device_uuid:
            return Response({"error": "device_uuid required"}, status=status.HTTP_400_BAD_REQUEST)
        Device.objects.filter(user=request.user, device_uuid=device_uuid).update(is_active=False)
        return Response({"deactivated": True})


from rest_framework import serializers as drf_serializers

from common.permissions import IsClient, IsEmailVerified

from .models import CustomReminder


class CustomReminderViewSet(BaseViewSet):
    """CRUD for user-defined reminders."""

    serializer_class = CustomReminderSerializer
    permission_classes = [IsAuthenticated, IsEmailVerified, IsClient]
    pagination_class = None

    def get_queryset(self) -> Any:
        queryset = CustomReminder.objects.filter(user=self.request.user).order_by("time", "name")
        return queryset[:50] if self.action == "list" else queryset

    def perform_create(self, serializer):
        # Extend here with plan/limit checks; the base ships no billing app.
        account = getattr(self.request, "active_account", None)
        serializer.save(user=self.request.user, account=account)

    def perform_update(self, serializer):
        serializer.save()
