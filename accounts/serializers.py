"""Accounts serializers for auth, registration, and OTP flows."""

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPRecord, PasswordResetToken

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer — REUSE: generic login, no role hardcoding."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField(required=False, allow_blank=True)
        self.fields["password"] = serializers.CharField(
            required=False, allow_blank=True, write_only=True
        )

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
        # REUSE: add custom claims if needed — e.g. token["role"] = getattr(user, "role", "")
        return token


class UserRegistrationSerializer(serializers.Serializer):
    """Generic registration — REUSE: creates user + handles social-only reuse."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._existing_user = None

    def validate(self, attrs):
        if User.objects.filter(email=attrs.get("email")).exists():
            existing = User.objects.filter(email=attrs.get("email")).first()
            if existing and existing.has_usable_password():
                raise serializers.ValidationError(
                    {"email": _("A user with this email already exists. Please log in instead.")}
                )
            self._existing_user = existing
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password": _("Passwords don't match")})
        return attrs

    def create(self, validated_data):
        if self._existing_user:
            # Social-only account reuse — set password on existing
            existing = self._existing_user
            existing.set_password(validated_data["password"])
            existing.is_active = True
            if hasattr(existing, "is_verified"):
                existing.is_verified = True
            if hasattr(existing, "status"):
                existing.status = User.Status.ACTIVE
            existing.save()
            return existing

        email = validated_data.get("email", "")
        base_username = email.split("@")[0][:140]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        validated_data["username"] = username
        user = User.objects.create_user(**validated_data)
        # REUSE: if your project requires verification, set UNVERIFIED here
        # if hasattr(user, "status"):
        #     user.status = User.Status.UNVERIFIED
        #     user.save(update_fields=["status"])
        return user


# ─────────────────────────────────────────────────────────────────
# OTP / Password-reset serializers — REUSE: Generic verification
# From ras-elbar-go/backend/accounts/serializers.py (project-agnostic)
# ─────────────────────────────────────────────────────────────────


class UserVerifyAccountSerializer(serializers.Serializer):
    """Verify OTP code. REUSE: POST {code, purpose?} to /verify/"""

    code = serializers.CharField(write_only=True, min_length=6, max_length=6)
    purpose = serializers.CharField(required=False, default="email_verification")

    def validate(self, attrs):
        from .helpers import validate_otp

        code = attrs.get("code", "").strip()
        purpose = attrs.get("purpose", "email_verification")
        otp_record = validate_otp(code, purpose=purpose)
        attrs["otp_record"] = otp_record
        return attrs


class UserResetPasswordSerializer(serializers.Serializer):
    """Reset password via token. REUSE: POST {token, password, password_confirm}"""

    token = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        token = PasswordResetToken.objects.filter(token=attrs["token"], is_used=False).first()
        if not token:
            raise serializers.ValidationError({"token": _("Invalid token")})
        if token.expires_at < timezone.now():
            raise serializers.ValidationError({"token": _("Token has expired")})
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password": _("Passwords don't match")})
        attrs["reset_token"] = token
        return attrs


class UserEmailSerializer(serializers.Serializer):
    """Request OTP email. REUSE: POST {email, type} to /send-verification-code/"""

    email = serializers.EmailField(required=True)
    type = serializers.CharField(default="email_verification", write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").strip()
        otp_type = attrs.get("type", "").strip()
        if not email:
            raise serializers.ValidationError({"email": _("Email is required")})
        if otp_type not in OTPRecord.OTPType.values:
            raise serializers.ValidationError({"type": _("Invalid type")})
        return attrs


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for user profile read/update."""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_verified",
            "status",
            "first_name",
            "last_name",
            "phone_number",
            "avatar",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
