"""Account serializers"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from common.serializers import AuditableSerializer
from django.utils.translation import gettext as _
from .models import OTPRecord
User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField(required=False, allow_blank=True)
        self.fields['password'] = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get(self.username_field, "").strip()
        password = attrs.get("password", "")

        if not email or not password:
            raise serializers.ValidationError({"detail": _("Please fill in all fields")})

        user = User.objects.filter(email=email).first()
        
        if not user or not user.check_password(password):
            raise serializers.ValidationError({"detail": _("Incorrect email or password")})

        if user.status == User.Status.UNVERIFIED:
            raise serializers.ValidationError({"detail": _("Please verify your email first")})
            
        if user.status == User.Status.SUSPENDED:
            raise serializers.ValidationError({"detail": _("Your account has been suspended. Contact support.")})

        self.user = user
        refresh = self.get_token(user)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        return token

class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password": _("Passwords don't match")})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class UserActivationSerializer(serializers.ModelSerializer):
    """User activation"""
    class Meta:
        model = User
        fields = ["code"]

    def validate(self, attrs):
        code = attrs.get("code", "").strip()
        if not code:
            raise serializers.ValidationError({"code": _("Code is required")})
        
        return attrs

class UserDetailSerializer(AuditableSerializer):
    """User details"""
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_verified", "status", "created_at"]
