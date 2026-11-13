"""Push device routes (QOOT-010) - mounted at /api/v1/push-devices/."""

from django.urls import path

from .views import DeviceViewSet

app_name = "push-devices"
urlpatterns = [
    path("", DeviceViewSet.as_view({"get": "list", "post": "create"}), name="push-devices"),
    path("<uuid:pk>/", DeviceViewSet.as_view({"delete": "destroy"}), name="push-device-detail"),
    path(
        "unregister/", DeviceViewSet.as_view({"post": "unregister"}), name="push-devices-unregister"
    ),
]
