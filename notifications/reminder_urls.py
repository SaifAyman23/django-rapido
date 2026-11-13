"""Custom reminder routes (QOOT-010) - mounted at /api/v1/custom-reminders/."""

from django.urls import path

from .views import CustomReminderViewSet

app_name = "custom-reminders"
urlpatterns = [
    path(
        "",
        CustomReminderViewSet.as_view({"get": "list", "post": "create"}),
        name="custom-reminders",
    ),
    path(
        "<uuid:pk>/",
        CustomReminderViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="custom-reminder-detail",
    ),
]
