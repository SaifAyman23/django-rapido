"""Account viewsets"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from accounts.serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserDetailSerializer,
)
from common.views import BaseViewSet

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
            return Response(
                {"message": "User registered"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)