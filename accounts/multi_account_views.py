"""Auth API — thin ViewSet over the accounts services (QOOT-001 / QOOT-002).

No business logic here: views validate input, call one service, and shape the
response. Errors are raised as ``ApplicationException`` subclasses so the global
handler returns the single Qoot envelope (QOOT-014 §2.1.1).
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from common.exceptions import (
    AccountAlreadyAddedError,
    AccountNotFoundError,
    AccountOwnershipConflictError,
    InvalidCodeError,
    ThrottledError,
)
from common.permissions import IsEmailVerified
from common.throttles import AccountLinkThrottle, AuthRateThrottle, OTPThrottle

from .models import EmailOTP
from .serializers import (
    AccountSummarySerializer,
    AddAccountLoginSerializer,
    AddAccountRequestSerializer,
    AddAccountResendSerializer,
    AddAccountVerifySerializer,
    AppleSocialLoginSerializer,
    AuthResponseSerializer,
    AvatarUploadSerializer,
    EmailChangeConfirmSerializer,
    EmailChangeRequestSerializer,
    FacebookSocialLoginSerializer,
    GoogleSocialLoginSerializer,
    LoginSerializer,
    LogoutSerializer,
    MeSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    VerificationPendingSerializer,
    VerifyEmailSerializer,
)
from .services import register as register_service
from .services.accounts import delete_account as delete_account_service
from .services.accounts import (
    delete_user_identity,
    get_account_for_user,
    list_for_user,
    request_add_account,
    resend_add_account,
    resolve_login_identity,
    verify_add_account,
)
from .services.avatar import clear_account_avatar, set_account_avatar
from .services.email_change import confirm_email_change, request_email_change
from .services.login import check_credentials, login_user
from .services.login import verify_email as verify_email_service
from .services.otp import queue_otp_email, seconds_until_resend
from .services.password_change import change_password
from .services.password_reset import confirm_password_reset, request_password_reset
from .services.social import login_with_apple, login_with_facebook, login_with_google
from .services.tokens import build_token_pair, register_outstanding_refresh_token

logger = logging.getLogger(__name__)
User = get_user_model()

PUBLIC = {"authentication_classes": [], "permission_classes": [AllowAny]}
VERIFIED = [IsAuthenticated, IsEmailVerified]


def _auth_response(result, request) -> dict:
    """Turn a service result into the ``{user, account, access, refresh}`` body."""
    user, account = result["user"], result["account"]
    user.active_account = account
    payload = {
        "user": user,
        "account": account,
        "access": result["access"],
        "refresh": result["refresh"],
    }
    return AuthResponseSerializer(
        payload,
        context={"request": request, "account": account},
    ).data


def _user_for_email(email: str):
    user, _account = resolve_login_identity(email)
    return user


@extend_schema(tags=["Authentication"])
class AuthViewSet(viewsets.ViewSet):
    """Account-scoped authentication endpoints."""

    permission_classes = [IsAuthenticated]

    # ── Registration / verification ───────────────────────────────

    @extend_schema(
        summary=_("Register with email and password"),
        request=RegisterSerializer,
        responses={201: VerificationPendingSerializer, 200: VerificationPendingSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="register",
        throttle_classes=[AuthRateThrottle, OTPThrottle],
        **PUBLIC,
    )
    @transaction.atomic
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, account, otp, created = register_service.register_user(**serializer.validated_data)
        transaction.on_commit(lambda: register_service.send_verification_code(otp))

        payload = {
            "user": user,
            "account": account,
            "verification_required": True,
            "message": _("We sent a verification code to your email."),
        }
        body = VerificationPendingSerializer(
            payload,
            context={"request": request, "account": account},
        ).data
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(
        summary=_("Verify email with the 6-digit code"),
        request=VerifyEmailSerializer,
        responses={200: AuthResponseSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="verify-email",
        throttle_classes=[AuthRateThrottle],
        **PUBLIC,
    )
    def verify_email(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = _user_for_email(data["email"])
        if user is None:
            raise InvalidCodeError()

        result = verify_email_service(
            user,
            data["code"],
            data.get("account_id"),
            email=data["email"],
        )
        return Response(_auth_response(result, request), status=status.HTTP_200_OK)

    @extend_schema(
        summary=_("Resend the email verification code"),
        request=ResendVerificationSerializer,
        responses={204: OpenApiResponse(description=_("Code sent"))},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="verify-email/resend",
        throttle_classes=[OTPThrottle],
        **PUBLIC,
    )
    @transaction.atomic
    def resend_verification(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp = register_service.resend_verification_email(serializer.validated_data["email"])
        # Anti-enumeration: verified or unknown emails get the same 204.
        if otp is not None:
            transaction.on_commit(lambda: queue_otp_email(otp))
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Session ───────────────────────────────────────────────────

    @extend_schema(
        summary=_("Log in and select an account"),
        request=LoginSerializer,
        responses={200: AuthResponseSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="login",
        throttle_classes=[AuthRateThrottle],
        **PUBLIC,
    )
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = login_user(**serializer.validated_data)
        return Response(_auth_response(result, request), status=status.HTTP_200_OK)

    # ── Social sign-in (Google / Apple) ───────────────────────────

    @extend_schema(
        summary=_("Sign in with Google"),
        request=GoogleSocialLoginSerializer,
        responses={200: AuthResponseSerializer, 201: AuthResponseSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="social/google",
        throttle_classes=[AuthRateThrottle],
        **PUBLIC,
    )
    def social_google(self, request):
        serializer = GoogleSocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = login_with_google(**serializer.validated_data)
        created = result.pop("created", False)
        return Response(
            _auth_response(result, request),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        summary=_("Sign in with Apple"),
        request=AppleSocialLoginSerializer,
        responses={200: AuthResponseSerializer, 201: AuthResponseSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="social/apple",
        throttle_classes=[AuthRateThrottle],
        **PUBLIC,
    )
    def social_apple(self, request):
        serializer = AppleSocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("full_name", None)  # Apple name is display-only; onboarding owns it
        result = login_with_apple(**data)
        created = result.pop("created", False)
        return Response(
            _auth_response(result, request),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        summary=_("Sign in with Facebook"),
        request=FacebookSocialLoginSerializer,
        responses={200: AuthResponseSerializer, 201: AuthResponseSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="social/facebook",
        throttle_classes=[AuthRateThrottle],
        **PUBLIC,
    )
    def social_facebook(self, request):
        serializer = FacebookSocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = login_with_facebook(**serializer.validated_data)
        created = result.pop("created", False)
        return Response(
            _auth_response(result, request),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        summary=_("Change password while signed in"),
        request=PasswordChangeSerializer,
        responses={200: OpenApiResponse(description=_("Password changed"))},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="password/change",
        permission_classes=VERIFIED,
        throttle_classes=[AuthRateThrottle],
    )
    @transaction.atomic
    def password_change(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        change_password(
            request.user,
            current_password=data["current_password"],
            new_password=data["new_password"],
            keep_refresh=data.get("refresh", ""),
        )
        return Response({"message": _("Password changed.")}, status=status.HTTP_200_OK)

    @extend_schema(
        summary=_("Request an email change (code sent to the new address)"),
        request=EmailChangeRequestSerializer,
        responses={200: OpenApiResponse(description=_("Verification code sent"))},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="email/change-request",
        permission_classes=VERIFIED,
        throttle_classes=[AuthRateThrottle, OTPThrottle],
    )
    @transaction.atomic
    def email_change_request(self, request):
        serializer = EmailChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_email = serializer.validated_data["new_email"]
        request_email_change(request.user, new_email, account=request.active_account)
        return Response(
            {
                "email": new_email,
                "verification_required": True,
                "message": _("We sent a verification code to the new email."),
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary=_("Confirm an email change with the 6-digit code"),
        request=EmailChangeConfirmSerializer,
        responses={200: OpenApiResponse(description=_("Email changed"))},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="email/change-confirm",
        permission_classes=VERIFIED,
        throttle_classes=[AuthRateThrottle],
    )
    @transaction.atomic
    def email_change_confirm(self, request):
        serializer = EmailChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        new_email = confirm_email_change(
            request.user,
            data["code"],
            account=request.active_account,
            new_email=data["new_email"],
            keep_refresh=data.get("refresh", ""),
        )
        account = request.active_account
        if account is not None:
            account.refresh_from_db()
        payload = (
            serialize_profile(account)
            if account is not None and account.profile is not None
            else None
        )
        if payload is None:
            payload = {"email": new_email}
        return Response(payload, status=status.HTTP_200_OK)

    @extend_schema(
        summary=_("Log out (blacklist the refresh token)"),
        request=LogoutSerializer,
        responses={204: OpenApiResponse(description=_("Logged out"))},
    )
    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        refresh = request.data.get("refresh") or request.COOKIES.get("refresh_token")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except Exception:  # already blacklisted / malformed — logout stays idempotent
                logger.debug("Logout with unusable refresh token", exc_info=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary=_("Current active-account state"),
        responses={200: MeSerializer},
    )
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        account = getattr(request, "active_account", None)
        payload = {"user": request.user, "account": account}
        return Response(
            MeSerializer(payload, context={"request": request, "account": account}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary=_("Upload or remove the active account's profile image"),
        request=AvatarUploadSerializer,
        responses={
            200: AccountSummarySerializer,
            204: OpenApiResponse(description=_("Image removed")),
        },
    )
    @action(
        detail=False,
        methods=["post", "delete"],
        url_path="avatar",
        parser_classes=[MultiPartParser, FormParser],
    )
    def avatar(self, request):
        account = getattr(request, "active_account", None)
        if account is None:
            raise AccountNotFoundError()

        if request.method == "DELETE":
            clear_account_avatar(account)
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        set_account_avatar(account, serializer.validated_data["avatar"])
        return Response(
            AccountSummarySerializer(
                account,
                context={"request": request, "account": account},
            ).data,
            status=status.HTTP_200_OK,
        )

    # ── Multi-account ─────────────────────────────────────────────

    @extend_schema(
        summary=_("List the caller's accounts"),
        responses={200: AccountSummarySerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="accounts", permission_classes=VERIFIED)
    def accounts(self, request):
        rows = list_for_user(request.user)
        serializer = AccountSummarySerializer(
            rows,
            many=True,
            context={"request": request, "account": request.active_account},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary=_("Add/select an existing account of the same person"),
        request=AddAccountLoginSerializer,
        responses={200: AuthResponseSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="accounts/add/login",
        permission_classes=VERIFIED,
        throttle_classes=[AccountLinkThrottle],
    )
    def add_login(self, request):
        serializer = AddAccountLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        candidate, resolved = check_credentials(email=data["email"], password=data["password"])
        if candidate.pk != request.user.pk:
            # Credentials cannot merge two person identities (QOOT-001 §1.5).
            raise AccountOwnershipConflictError()

        target_id = data.get("account_id") or (resolved.pk if resolved is not None else None)
        account = get_account_for_user(candidate, target_id, required=True)
        if request.active_account and account.pk == request.active_account.pk:
            raise AccountAlreadyAddedError()

        tokens = build_token_pair(candidate, account)
        return Response(
            _auth_response({"user": candidate, "account": account, **tokens}, request),
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary=_("Request a code to add a new account email"),
        request=AddAccountRequestSerializer,
        responses={202: OpenApiResponse(description=_("Verification code sent"))},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="accounts/add/request",
        permission_classes=VERIFIED,
        throttle_classes=[AccountLinkThrottle, OTPThrottle],
    )
    @transaction.atomic
    def add_request(self, request):
        serializer = AddAccountRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        otp = request_add_account(
            request.user,
            email=data["email"],
            role=data["role"],
        )
        transaction.on_commit(lambda: queue_otp_email(otp))

        return Response(
            {
                "email": data["email"],
                "role": data["role"],
                "verification_required": True,
                "message": _("We sent a verification code to the new email."),
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        summary=_("Verify the new account email and create the account"),
        request=AddAccountVerifySerializer,
        responses={201: AuthResponseSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="accounts/add/verify",
        permission_classes=VERIFIED,
        throttle_classes=[AccountLinkThrottle],
    )
    def add_verify(self, request):
        # No long-lived atomic block here: verify_otp must persist failed attempts.
        serializer = AddAccountVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        account = verify_add_account(
            request.user,
            email=data["email"],
            code=data["code"],
        )
        tokens = build_token_pair(request.user, account)
        return Response(
            _auth_response({"user": request.user, "account": account, **tokens}, request),
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary=_("Resend the add-account verification code"),
        request=AddAccountResendSerializer,
        responses={204: OpenApiResponse(description=_("Code sent"))},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="accounts/add/resend",
        permission_classes=VERIFIED,
        throttle_classes=[AccountLinkThrottle, OTPThrottle],
    )
    @transaction.atomic
    def add_resend(self, request):
        serializer = AddAccountResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        remaining = seconds_until_resend(request.user, EmailOTP.Purpose.ADD_ACCOUNT, email=email)
        if remaining:
            raise ThrottledError(context={"retry_after": remaining})

        otp = resend_add_account(request.user, email=email)
        if otp is not None:
            transaction.on_commit(lambda: queue_otp_email(otp))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary=_("Delete the person identity and every account"),
        responses={204: OpenApiResponse(description=_("Deleted"))},
    )
    @action(detail=False, methods=["delete"], url_path="account")
    def delete_account(self, request):
        delete_user_identity(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Password reset (public) ───────────────────────────────────

    @extend_schema(
        summary=_("Request a password reset code"),
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description=_("Neutral confirmation"))},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="password-reset/request",
        throttle_classes=[AuthRateThrottle, OTPThrottle],
        **PUBLIC,
    )
    def password_reset_request(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data["email"])
        return Response(
            {"message": _("If this email exists, we sent a reset code.")},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary=_("Confirm a password reset with the 6-digit code"),
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(description=_("Password reset"))},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="password-reset/confirm",
        throttle_classes=[AuthRateThrottle],
        **PUBLIC,
    )
    def password_reset_confirm(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        confirm_password_reset(**serializer.validated_data)
        return Response({"message": _("Password reset successfully.")}, status=status.HTTP_200_OK)


class RemoveAccountView(APIView):
    """``DELETE /auth/accounts/{account_id}/`` — hard-delete one Account.

    Deleting the last Account also deletes the person identity, because no
    Account would remain. A primary Account removal mirrors ``User.email`` to the
    oldest remaining Account that has an email.
    """

    permission_classes = VERIFIED

    @extend_schema(
        summary=_("Delete an account and its data"),
        responses={204: OpenApiResponse(description=_("Deleted"))},
        tags=["Authentication"],
    )
    def delete(self, request, account_id):
        delete_account_service(request.user, account_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary=_("Rotate the refresh token"),
    tags=["Authentication"],
    responses={200: OpenApiResponse(description=_("New access and refresh tokens"))},
)
class RefreshTokenView(TokenRefreshView):
    """Standard simplejwt rotation (ROTATE_REFRESH_TOKENS + blacklist)."""

    def post(self, request, *args, **kwargs):
        # simplejwt's TokenRefreshView.validate() calls User.objects.get(user_id=...)
        # and raises an uncaught DoesNotExist when the token references a deleted
        # user. That surfaces as a 500 with an ugly traceback; convert it to a 401 so
        # the client clears the session instead of crashing.
        try:
            response = super().post(request, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — surface as 401, never 500
            logger.warning("Token refresh rejected: %s", exc)
            return Response(
                {"detail": _("Invalid or expired refresh token.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        # simplejwt rotates the token but does not record the new one; without
        # this, per-account revocation would miss a recently refreshed session.
        if response.status_code == status.HTTP_200_OK and response.data.get("refresh"):
            register_outstanding_refresh_token(response.data["refresh"])
        return response
