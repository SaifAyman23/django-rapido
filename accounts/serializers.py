"""Accounts serializers — strict request validation and read models.

Every request serializer extends ``StrictSerializer`` so an unknown key returns
``400 UNKNOWN_FIELD`` instead of being silently dropped.
Response shapes are ``{user, account, access, refresh}``.
"""

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from common.serializers import StrictSerializer

from .models import Account
from .services.passwords import password_validator_errors

User = get_user_model()

CODE_PATTERN = r"^\d{6}$"


class LowercaseEmailField(serializers.EmailField):
    """Email field that trims and lowercases input."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = data.strip().lower()
        return super().to_internal_value(data)


class RoleField(serializers.ChoiceField):
    """Accept ``CLIENT``/``client`` and normalise to the stored lowercase value."""

    def __init__(self, **kwargs):
        kwargs.setdefault("choices", Account.Role.choices)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = data.strip().lower()
        return super().to_internal_value(data)


class CodeField(serializers.RegexField):
    """Exactly six digits."""

    def __init__(self, **kwargs):
        kwargs.setdefault("regex", CODE_PATTERN)
        kwargs.setdefault("error_messages", {"invalid": _("Enter the 6-digit code")})
        super().__init__(**kwargs)


# ─────────────────────────────────────────────────────────────────
# Request serializers
# ─────────────────────────────────────────────────────────────────


class RegisterSerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    role = RoleField()

    def validate(self, attrs):
        errors = password_validator_errors(attrs["password"], email=attrs["email"])
        if errors:
            raise serializers.ValidationError({"password": errors})
        return attrs


class LoginSerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    account_id = serializers.UUIDField(required=False)


class VerifyEmailSerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)
    code = CodeField()
    account_id = serializers.UUIDField(required=False)


class ResendVerificationSerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)


class PasswordResetRequestSerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)


class PasswordResetConfirmSerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)
    code = CodeField()
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate(self, attrs):
        errors = password_validator_errors(attrs["new_password"], email=attrs["email"])
        if errors:
            raise serializers.ValidationError({"new_password": errors})
        return attrs


class PasswordChangeSerializer(StrictSerializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    refresh = serializers.CharField(required=False, write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context.get("user")
        errors = password_validator_errors(attrs["new_password"], user=user)
        if errors:
            raise serializers.ValidationError({"new_password": errors})
        return attrs


class EmailChangeRequestSerializer(StrictSerializer):
    new_email = LowercaseEmailField(max_length=254)


class EmailChangeConfirmSerializer(StrictSerializer):
    new_email = LowercaseEmailField(max_length=254)
    code = CodeField()
    refresh = serializers.CharField(required=False, write_only=True, trim_whitespace=False)


class AddAccountLoginSerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    account_id = serializers.UUIDField(required=False)


class AddAccountRequestSerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)
    role = RoleField()


class AddAccountVerifySerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)
    code = CodeField()


class AddAccountResendSerializer(StrictSerializer):
    email = LowercaseEmailField(max_length=254)


class GoogleSocialLoginSerializer(StrictSerializer):
    """Google SDK ID token, or an authorization code + PKCE verifier."""

    id_token = serializers.CharField(required=False, allow_blank=False)
    code = serializers.CharField(required=False, allow_blank=False)
    redirect_uri = serializers.URLField(required=False, allow_blank=False)
    code_verifier = serializers.CharField(required=False, allow_blank=False)
    role = RoleField(required=False)

    def validate(self, attrs):
        if not attrs.get("id_token") and not attrs.get("code"):
            raise serializers.ValidationError(
                {"id_token": _("Send a Google ID token or an authorization code.")}
            )
        if attrs.get("code") and not attrs.get("redirect_uri"):
            raise serializers.ValidationError(
                {"redirect_uri": _("redirect_uri is required with an authorization code.")}
            )
        return attrs


class AppleSocialLoginSerializer(StrictSerializer):
    """Apple identity token from the native sign-in sheet."""

    identity_token = serializers.CharField(allow_blank=False)
    role = RoleField(required=False)
    nonce = serializers.CharField(required=False, allow_blank=False)
    full_name = serializers.JSONField(required=False)


class FacebookSocialLoginSerializer(StrictSerializer):
    """Facebook user access token from the native SDK."""

    access_token = serializers.CharField(allow_blank=False)
    role = RoleField(required=False)


class LogoutSerializer(StrictSerializer):
    refresh = serializers.CharField(required=False, allow_blank=True)


# ─────────────────────────────────────────────────────────────────
# Read serializers
# ─────────────────────────────────────────────────────────────────


def _current_account(serializer, instance_user=None):
    """Account bound to this response (explicit context wins over request)."""
    if "account" in serializer.context:
        return serializer.context["account"]
    user = instance_user or serializer.context.get("user")
    if user is not None:
        return getattr(user, "active_account", None)
    request = serializer.context.get("request")
    return getattr(request, "active_account", None) if request else None


class UserSummarySerializer(serializers.ModelSerializer):
    """``{id, email, role, is_email_verified, onboarding_completed}``."""

    email = serializers.SerializerMethodField()
    is_email_verified = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    onboarding_completed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "is_email_verified", "onboarding_completed"]
        read_only_fields = fields

    def get_email(self, obj):
        account = _current_account(self, obj)
        return account.display_email if account else obj.email

    def get_is_email_verified(self, obj):
        account = _current_account(self, obj)
        if account is not None:
            return account.is_email_verified
        return bool(obj.is_verified)

    def get_role(self, obj):
        account = _current_account(self, obj)
        return account.role if account else None

    def get_onboarding_completed(self, obj):
        account = _current_account(self, obj)
        return bool(account and account.has_profile)


class AccountSummarySerializer(serializers.ModelSerializer):
    """Account row used by login/me and the account switcher."""

    full_name = serializers.CharField(read_only=True)
    has_profile = serializers.BooleanField(read_only=True)
    email = serializers.CharField(source="display_email", read_only=True)
    is_current = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    needs_setup = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id",
            "role",
            "full_name",
            "email",
            "is_active",
            "has_profile",
            "is_current",
            "unread_count",
            "needs_setup",
            "avatar_url",
        ]
        read_only_fields = fields

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url

    def get_is_current(self, obj):
        account = _current_account(self)
        return bool(account and account.pk == obj.pk)

    def get_unread_count(self, obj):
        # Notifications.Device is keyed by User, not Account, so a per-account
        # unread count is not possible yet; the notifications app owns the real counter.
        return 0

    def get_needs_setup(self, obj):
        return not obj.is_email_verified or not obj.has_profile


class AuthResponseSerializer(serializers.Serializer):
    """``{user, account, access, refresh}``."""

    user = UserSummarySerializer(read_only=True)
    account = AccountSummarySerializer(read_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class VerificationPendingSerializer(serializers.Serializer):
    """Register response — no tokens until the email is verified."""

    user = UserSummarySerializer(read_only=True)
    account = AccountSummarySerializer(read_only=True)
    verification_required = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)


class MeSerializer(serializers.Serializer):
    """Current active-account state used by the app router."""

    user = UserSummarySerializer(read_only=True)
    account = AccountSummarySerializer(read_only=True)
    is_email_verified = serializers.SerializerMethodField()
    onboarding_completed = serializers.SerializerMethodField()

    def get_is_email_verified(self, obj):
        account = obj.get("account") or _current_account(self)
        if account is not None:
            return account.is_email_verified
        user = obj.get("user")
        return bool(user and user.is_verified)

    def get_onboarding_completed(self, obj):
        account = obj.get("account") or _current_account(self)
        return bool(account and account.has_profile)


MAX_AVATAR_BYTES = 5 * 1024 * 1024


class AvatarUploadSerializer(StrictSerializer):
    """``POST /auth/avatar/`` — one multipart profile image."""

    avatar = serializers.ImageField()

    def validate_avatar(self, image):
        if image.size > MAX_AVATAR_BYTES:
            raise serializers.ValidationError(_("Keep the image under 5 MB."))
        return image


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer ??? REUSE: generic login, no role hardcoding."""

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
        # REUSE: add custom claims if needed ??? e.g. token["role"] = getattr(user, "role", "")
        return token


class UserRegistrationSerializer(serializers.Serializer):
    """Generic registration ??? REUSE: creates user + handles social-only reuse."""

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
            # Social-only account reuse ??? set password on existing
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


# ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
# OTP / Password-reset serializers ??? REUSE: Generic verification
# Django Rapido ??? project-agnostic serializers.
# ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????


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
