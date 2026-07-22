from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField(required=False, allow_blank=True)
        self.fields['password'] = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        from .helpers import validate_credentials

        email = attrs.get(self.username_field, "").strip()
        password = attrs.get("password", "")
        user = validate_credentials(email, password)

        self.user = user
        refresh = self.get_token(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        return token


class UserRegistrationSerializer(serializers.Serializer):
    """User registration"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if User.objects.filter(email=attrs.get("email")).exists():
            raise serializers.ValidationError({"email": _("A user with this email already exists.")})
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password": _("Passwords don't match")})
        return attrs

    def create(self, validated_data):
        email = validated_data.get('email', '')
        base_username = email.split('@')[0][:140]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        validated_data['username'] = username
        user = User.objects.create_user(**validated_data)
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "is_verified", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
