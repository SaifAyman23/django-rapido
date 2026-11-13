"""REUSE: Notification + device routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomReminderViewSet, DeviceViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r"devices", DeviceViewSet, basename="device")
router.register(r"push-devices", DeviceViewSet, basename="push-device")
router.register(r"custom-reminders", CustomReminderViewSet, basename="custom-reminder")
router.register(r"", NotificationViewSet, basename="notification")

urlpatterns = [path("", include(router.urls))]
