"""Policy routes — mounted at ``/api/v1/policies/``."""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import PolicyViewSet

app_name = "policies"

router = SimpleRouter()
router.register(r"", PolicyViewSet, basename="policy")

urlpatterns = [path("", include(router.urls))]
