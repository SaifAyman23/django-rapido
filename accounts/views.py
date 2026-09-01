"""Accounts views — JWT auth, registration, OTP verification, and password reset."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from common.helpers import clear_token_cookies, set_refresh_token_cookie
from common.throttles import AuthRateThrottle
from common.views import BaseViewSet

from .helpers import create_and_send_otp, generate_otp, generate_password_reset_token
from .models import OTPRecord, PasswordResetToken
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserDetailSerializer,
    UserEmailSerializer,
    UserRegistrationSerializer,
    UserResetPasswordSerializer,
    UserVerifyAccountSerializer,
)

User = get_user_model()


@extend_schema(summary=_("Obtain JWT token pair"), tags=["Authentication"])
class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT token view"""

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        refresh_token = serializer.validated_data.get("refresh")
        if refresh_token:
            response = set_refresh_token_cookie(response, refresh_token)
        return response


@extend_schema(summary=_("Refresh JWT token"), tags=["Authentication"])
class CookieTokenRefreshView(TokenObtainPairView):
    """Token refresh view that reads refresh token from cookie."""

    def post(self, request, *args, **kwargs):
        # REUSE: body or cookie — supports both header and HttpOnly cookie clients
        refresh_token = request.data.get("refresh") or request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response(
                {"error": _("Refresh token is required.")}, status=status.HTTP_401_UNAUTHORIZED
            )
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        new_refresh_token = serializer.validated_data.get("refresh", refresh_token)
        response = set_refresh_token_cookie(response, new_refresh_token)
        return response


@extend_schema(summary=_("User viewset"), tags=["Authentication"])
class UserViewSet(BaseViewSet):
    """User viewset — REUSE: generic auth, wire OTP endpoints as needed."""

    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["username", "email"]

    @extend_schema(
        summary=_("Get current user profile"),
        responses={200: UserDetailSerializer},
        tags=["Authentication"],
    )
    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Register new user"),
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(description=_("Account created.")),
            400: OpenApiResponse(description=_("Validation error")),
        },
        tags=["Authentication"],
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        throttle_classes=[AuthRateThrottle],
    )
    @transaction.atomic
    def register(self, request):
        """REUSE: Creates user + sends OTP via on_commit. Swap to Celery .delay() if needed."""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # REUSE: Use transaction.on_commit so email only sends if DB commit succeeds
            transaction.on_commit(lambda: create_and_send_otp(user))
            return Response(
                {"message": _("Check your email for verification code.")},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "error": {
                    "code": "validation_error",
                    "message": _("Invalid input"),
                    "details": serializer.errors,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ─────────────────────────────────────────────────────────────────
    # OTP verification flow — REUSE: project-agnostic, no role checks
    # Uncomment these actions + wire urls if you need email verification.
    # From ras-elbar-go/backend/accounts/views.py (generic subset).
    # ─────────────────────────────────────────────────────────────────

    @extend_schema(
        summary=_("Verify account with OTP"),
        request=UserVerifyAccountSerializer,
        responses={200: OpenApiResponse(description=_("Verified"))},
        tags=["Authentication"],
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        throttle_classes=[AuthRateThrottle],
        url_path="verify",
    )
    @transaction.atomic
    def verify_account(self, request):
        """Verify OTP → marks user verified. REUSE for any email-verify flow."""
        serializer = UserVerifyAccountSerializer(data=request.data)
        if serializer.is_valid():
            otp_record = serializer.validated_data["otp_record"]
            user = otp_record.user

            if otp_record.type == OTPRecord.OTPType.EMAIL_VERIFICATION:
                # REUSE: Generic verification — adapt fields to your User model
                if hasattr(user, "is_verified"):
                    user.is_verified = True
                if hasattr(user, "status"):
                    user.status = User.Status.ACTIVE
                user.is_active = True
                if hasattr(user, "verified_at"):
                    user.verified_at = timezone.now()
                user.save()

                refresh = RefreshToken.for_user(user)
                otp_record.is_used = True
                otp_record.save(update_fields=["is_used"])
                return Response(
                    {
                        "message": _("Account verified successfully."),
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    status=status.HTTP_200_OK,
                )

            if otp_record.type == OTPRecord.OTPType.PASSWORD_RESET:
                token = PasswordResetToken.objects.create(
                    user=user,
                    token=generate_password_reset_token(),
                    expires_at=timezone.now() + timedelta(minutes=15),
                )
                otp_record.is_used = True
                otp_record.save(update_fields=["is_used"])
                return Response(
                    {"message": _("Password reset code verified."), "token": token.token},
                    status=status.HTTP_200_OK,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary=_("Resend verification code"), request=UserEmailSerializer, tags=["Authentication"]
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        throttle_classes=[AuthRateThrottle],
        url_path="send-verification-code",
    )
    @transaction.atomic
    def send_verification_code(self, request):
        """Resend OTP. REUSE: anti-enumeration — always 200 even if email not found."""
        serializer = UserEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"message": _("Check your email for verification code.")}, status=status.HTTP_200_OK
            )

        if serializer.validated_data["type"] == "email_verification" and getattr(
            user, "is_verified", False
        ):
            return Response(
                {"error": _("User is already verified.")}, status=status.HTTP_400_BAD_REQUEST
            )

        otp_record = OTPRecord.objects.create(
            user=user,
            otp=generate_otp(),
            type=serializer.validated_data["type"],
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        # REUSE: Swap to .delay() for async
        from .tasks import send_verification_email

        transaction.on_commit(
            lambda: send_verification_email.delay(user.id, user.email, otp_record.otp)
        )
        return Response(
            {"message": _("Check your email for verification code.")}, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary=_("Reset password"), request=UserResetPasswordSerializer, tags=["Authentication"]
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[AllowAny],
        throttle_classes=[AuthRateThrottle],
        url_path="reset-password",
    )
    @transaction.atomic
    def reset_password(self, request):
        """Reset password via token. REUSE: attempt limit 5, expiry check."""
        serializer = UserResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            token = (
                PasswordResetToken.objects.select_for_update()
                .filter(token=serializer.validated_data["token"], is_used=False)
                .first()
            )
            if not token:
                return Response(
                    {"error": _("Invalid or expired token.")}, status=status.HTTP_400_BAD_REQUEST
                )
            if token.attempts >= 5:
                return Response(
                    {"error": _("Too many attempts. Request a new reset link.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token.attempts += 1
            token.save(update_fields=["attempts"])
            user = token.user
            user.set_password(serializer.validated_data["password"])
            user.save()
            token.is_used = True
            token.save(update_fields=["is_used"])
            return Response(
                {"message": _("Password reset successfully.")}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary=_("Logout user"),
        request=inline_serializer(
            name="LogoutRequest", fields={"refresh": serializers.CharField(required=False)}
        ),
        responses={205: OpenApiResponse(description=_("Logout successful."))},
        tags=["Authentication"],
    )
    @action(detail=False, methods=["post"])
    def logout(self, request):
        try:
            refresh_token = request.data.get("refresh") or request.COOKIES.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            response = Response(
                {"detail": _("Logout successful.")}, status=status.HTTP_205_RESET_CONTENT
            )
            return clear_token_cookies(response)
        except (KeyError, TokenError):
            return clear_token_cookies(
                Response({"detail": _("Logout successful.")}, status=status.HTTP_205_RESET_CONTENT)
            )
