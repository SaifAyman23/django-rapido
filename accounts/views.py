"""Account viewsets"""
from .helpers import generate_otp
from .serializers import UserActivationSerializer
from rest_framework import viewsets, status
from rest_framework.decorators import action
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
from .tasks import send_verification_email
from .models import OTPRecord
from datetime import timedelta
from django.utils import timezone
User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT token view"""
    serializer_class = CustomTokenObtainPairSerializer

class UserViewSet(BaseViewSet):
    """User viewset"""
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["username", "email"]

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def register(self, request):
        """Register new user"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            otp_record = OTPRecord.objects.create(
                user=user,
                otp=generate_otp(),
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            send_verification_email.delay(user.id, user.email, otp_record.otp)
            return Response(
                {"message": _("Check your email for activation code.")},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def activate(self, request):
        """Activate user"""
        serializer = UserActivationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"message": _("Account activated successfully.")},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def logout(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': _('Logout successful.')}, status=status.HTTP_205_RESET_CONTENT)
        except KeyError:
            return Response({'error': _('Refresh token required.')}, status=status.HTTP_400_BAD_REQUEST)
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)