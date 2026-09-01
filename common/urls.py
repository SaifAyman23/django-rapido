"""Common app URL routes.

Currently no extra endpoints; router is reserved for future common APIs.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

app_name = "common"

router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
]
