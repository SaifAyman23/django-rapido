"""Accounts URL routes.

Wires JWT login, token refresh, verification, and user viewset endpoints.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView, TokenVerifyView

from .views import CookieTokenRefreshView, CustomTokenObtainPairView, UserViewSet

app_name = "accounts"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    # REUSE: Uncomment to enable OTP verification flow (requires OTPRecord + helpers)
    # path("verify/", UserVerifyView.as_view(), name="verify"),
    # path("send-verification-code/", SendVerificationCodeView.as_view(), name="send_code"),
    # path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    # REUSE: Uncomment for social login (requires allauth + SocialAccountAdapter)
    # path("auth/social/<str:provider>/", SocialLoginJWTView.as_view(), name="social_login"),
]
