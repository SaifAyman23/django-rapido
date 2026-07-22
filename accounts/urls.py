from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenVerifyView,
    TokenBlacklistView,
)
from .views import (
    UserViewSet,
    CustomTokenObtainPairView,
    CookieTokenRefreshView,
)

app_name = 'accounts'

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
]
