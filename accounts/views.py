from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserDetailSerializer,
)
from common.views import BaseViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils.translation import gettext as _
from common.helpers import set_refresh_token_cookie, clear_token_cookies
User = get_user_model()


@extend_schema(summary=_("Obtain JWT token pair"), tags=["Authentication"])
class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT token view"""
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        refresh_token = serializer.validated_data.get('refresh')
        if refresh_token:
            response = set_refresh_token_cookie(response, refresh_token)
        return response


@extend_schema(summary=_("Refresh JWT token"), tags=["Authentication"])
class CookieTokenRefreshView(TokenObtainPairView):
    """Token refresh view that reads refresh token from cookie."""

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token') or request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': _('Refresh token is required.')},
                status=status.HTTP_401_UNAUTHORIZED
            )
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        new_refresh_token = serializer.validated_data.get('refresh', refresh_token)
        response = set_refresh_token_cookie(response, new_refresh_token)
        return response


@extend_schema(summary=_("User viewset"), tags=["Authentication"])
class UserViewSet(BaseViewSet):
    """User viewset"""
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["username", "email"]

    @extend_schema(
        summary=_("Get current user profile"),
        responses={200: UserDetailSerializer},
        tags=["Authentication"]
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
            400: OpenApiResponse(description=_("Validation error"))
        },
        tags=["Authentication"]
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"message": _("Account created successfully.")},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"error": {"code": "validation_error", "message": _("Invalid input"), "details": serializer.errors}},
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        summary=_("Logout user"),
        request=inline_serializer(
            name='LogoutRequest',
            fields={'refresh': serializers.CharField(required=False)}
        ),
        responses={
            205: OpenApiResponse(description=_("Logout successful.")),
            400: OpenApiResponse(description=_("Bad Request"))
        },
        tags=["Authentication"]
    )
    @action(detail=False, methods=["post"])
    def logout(self, request):
        try:
            refresh_token = request.data.get('refresh') or request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            response = Response({'detail': _('Logout successful.')}, status=status.HTTP_205_RESET_CONTENT)
            return clear_token_cookies(response)
        except (KeyError, TokenError):
            return clear_token_cookies(
                Response({'detail': _('Logout successful.')}, status=status.HTTP_205_RESET_CONTENT)
            )
