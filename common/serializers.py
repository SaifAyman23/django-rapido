"""
Ultimate reusable Django REST Framework serializers
Provides production-grade serializers with:
- Automatic validation
- Error handling
- Field-level customization
- Nested relationships
- Audit trail integration
"""

from typing import Any, Dict, Optional, List, Tuple
from decimal import Decimal

from rest_framework import serializers
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator, EmailValidator
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


# ===========================
# Base Serializers
# ===========================

class DynamicFieldsSerializer(serializers.ModelSerializer):
    """
    Serializer that allows dynamic field selection via query params
    Usage: ?fields=id,name,email
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get fields from query params if it's a request context
        request = self.context.get("request")
        if request:
            fields_param = request.query_params.get("fields")
            if fields_param:
                allowed_fields = set(fields_param.split(","))
                existing_fields = set(self.fields.keys())
                fields_to_remove = existing_fields - allowed_fields

                for field_name in fields_to_remove:
                    self.fields.pop(field_name)


class AuditableSerializer(serializers.ModelSerializer):
    """Base serializer with audit trail support"""

    created_at = serializers.DateTimeField(
        read_only=True,
        format="%Y-%m-%dT%H:%M:%SZ",
    )
    updated_at = serializers.DateTimeField(
        read_only=True,
        format="%Y-%m-%dT%H:%M:%SZ",
    )

    class Meta:
        abstract = True

    @transaction.atomic
    def create(self, validated_data: Dict) -> Any:
        """Create instance and log audit trail"""
        instance = super().create(validated_data)
        logger.info(
            f"Created {instance.__class__.__name__} (ID: {instance.pk})",
            extra={"user_id": self.context.get("request").user.id if self.context.get("request") else None},
        )
        return instance

    @transaction.atomic
    def update(self, instance: Any, validated_data: Dict) -> Any:
        """Update instance and log audit trail"""
        # Get changed fields
        changes = {}
        for field_name, new_value in validated_data.items():
            old_value = getattr(instance, field_name, None)
            if old_value != new_value:
                changes[field_name] = {
                    "old": str(old_value),
                    "new": str(new_value),
                }

        instance = super().update(instance, validated_data)

        if changes:
            logger.info(
                f"Updated {instance.__class__.__name__} (ID: {instance.pk}): {changes}",
                extra={"user_id": self.context.get("request").user.id if self.context.get("request") else None},
            )

        return instance


class TimestampedSerializer(DynamicFieldsSerializer, AuditableSerializer):
    """Combine dynamic fields and audit logging"""

    class Meta:
        abstract = True


class ListRetrieveSerializer(DynamicFieldsSerializer):
    """
    Different serializers for list vs retrieve views
    Override list_serializer_class in child classes
    """

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Simplify for list views
        if self.context.get("view") and self.context["view"].action == "list":
            # Remove expensive fields for list views
            expensive_fields = getattr(self.Meta, "list_exclude_fields", [])
            for field in expensive_fields:
                if field in self.fields:
                    self.fields.pop(field)


# ===========================
# Field Serializers
# ===========================

class ColorField(serializers.CharField):
    """Serializer for hex color values"""

    def to_representation(self, value: str) -> str:
        """Ensure color starts with #"""
        if value and not value.startswith("#"):
            return f"#{value}"
        return value

    def to_internal_value(self, data: str) -> str:
        """Remove # if present"""
        if isinstance(data, str):
            data = data.lstrip("#").upper()
        return super().to_internal_value(data)


class SlugField(serializers.SlugField):
    """Enhanced slug field with auto-generation option"""

    def __init__(self, *args, auto_generate_from: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_generate_from = auto_generate_from

    def to_internal_value(self, data: Any) -> str:
        """Validate and normalize slug"""
        if not data and self.auto_generate_from:
            # Auto-generate from field if not provided
            source_field = self.parent._kwargs.get(self.auto_generate_from)
            if source_field:
                from django.utils.text import slugify
                data = slugify(source_field)

        return super().to_internal_value(data)


class JSONSerializerField(serializers.JSONField):
    """Enhanced JSON field with validation"""

    def to_representation(self, value: Dict) -> Dict:
        """Ensure clean JSON output"""
        if value is None:
            return {}
        return super().to_representation(value)

    def validate_empty_values(self, data: Any) -> Tuple[bool, Any]:
        """Allow empty dicts"""
        if data == {}:
            return False, {}
        return super().validate_empty_values(data)


class EnumField(serializers.ChoiceField):
    """Serializer for Django choice fields"""

    def __init__(self, enum_choices: Tuple, **kwargs):
        self.enum_map = {choice[0]: choice[1] for choice in enum_choices}
        super().__init__(choices=enum_choices, **kwargs)


class PriceField(serializers.DecimalField):
    """Serializer for price fields with currency handling"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 10)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("coerce_to_string", False)
        super().__init__(*args, **kwargs)

    def to_representation(self, value: Decimal) -> float:
        """Return as float"""
        if value is None:
            return 0.0
        return float(value)


# ===========================
# User Serializers
# ===========================

class UserCreateSerializer(TimestampedSerializer):
    """User creation with password validation"""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text=_("Password (minimum 8 characters)"),
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text=_("Confirm password"),
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        ]

    def validate(self, data: Dict) -> Dict:
        """Validate password match"""
        password = data.pop("password")
        password_confirm = data.pop("password_confirm")

        if password != password_confirm:
            raise ValidationError({
                "password": _("Passwords do not match"),
            })

        data["password"] = password
        return data

    @transaction.atomic
    def create(self, validated_data: Dict) -> User:
        """Create user with password"""
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        logger.info(f"User created: {user.email}")
        return user


class UserDetailSerializer(TimestampedSerializer):
    """Complete user information"""

    full_name = serializers.SerializerMethodField()
    email_verified = serializers.BooleanField(source="is_verified", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "avatar",
            "bio",
            "email_verified",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_full_name(self, obj: User) -> str:
        """Get user's full name"""
        return obj.get_full_name() or obj.username


class UserListSerializer(DynamicFieldsSerializer):
    """Lightweight user serializer for list views"""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "avatar",
            "is_verified",
        ]


class UserUpdateSerializer(TimestampedSerializer):
    """User profile update (non-password fields)"""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "avatar",
            "bio",
        ]

    def validate_avatar(self, value) -> Any:
        """Validate image size"""
        if value and value.size > 5 * 1024 * 1024:  # 5MB
            raise ValidationError(_("Image size must be less than 5MB"))
        return value


class UserPasswordChangeSerializer(serializers.Serializer):
    """Password change serializer"""

    old_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    def validate(self, data: Dict) -> Dict:
        """Validate old password and new passwords match"""
        request = self.context.get("request")
        user = request.user if request else None

        if not user:
            raise ValidationError(_("User not found"))

        # Validate old password
        if not user.check_password(data["old_password"]):
            raise ValidationError({
                "old_password": _("Incorrect password"),
            })

        # Validate new passwords match
        if data["new_password"] != data["new_password_confirm"]:
            raise ValidationError({
                "new_password": _("Passwords do not match"),
            })

        return data

    @transaction.atomic
    def save(self) -> User:
        """Update user password"""
        request = self.context.get("request")
        user = request.user
        user.set_password(self.validated_data["new_password"])
        user.save()
        logger.info(f"Password changed for user: {user.email}")
        return user


# ===========================
# Validation Serializers
# ===========================

class BulkCreateSerializer(serializers.ListSerializer):
    """Serializer for bulk create operations"""

    @transaction.atomic
    def create(self, validated_data: List[Dict]) -> List[Any]:
        """Create multiple instances"""
        instances = [self.child.Meta.model(**item) for item in validated_data]
        instances = self.child.Meta.model.objects.bulk_create(instances)
        logger.info(f"Bulk created {len(instances)} instances")
        return instances


class BulkUpdateSerializer(serializers.ListSerializer):
    """Serializer for bulk update operations"""

    @transaction.atomic
    def update(self, instances: List[Any], validated_data: List[Dict]) -> List[Any]:
        """Update multiple instances"""
        # Map instances by ID
        instance_map = {instance.id: instance for instance in instances}

        updated = []
        for item in validated_data:
            instance = instance_map.get(item.get("id"))
            if instance:
                for field, value in item.items():
                    if field != "id":
                        setattr(instance, field, value)
                updated.append(instance)

        self.child.Meta.model.objects.bulk_update(updated, fields=list(validated_data[0].keys()))
        logger.info(f"Bulk updated {len(updated)} instances")
        return updated


class NestedCreateSerializer(serializers.ModelSerializer):
    """Handle nested object creation"""

    class Meta:
        abstract = True

    @transaction.atomic
    def create(self, validated_data: Dict) -> Any:
        """Create instance with nested relations"""
        nested_data = {}

        # Extract nested fields
        for field_name, field in self.fields.items():
            if isinstance(field, serializers.ModelSerializer) and field_name in validated_data:
                nested_data[field_name] = validated_data.pop(field_name)

        # Create main instance
        instance = super().create(validated_data)

        # Create nested instances
        for field_name, nested_values in nested_data.items():
            getattr(instance, field_name).set(nested_values)

        return instance


# ===========================
# Utility Serializers
# ===========================

class PaginationSerializer(serializers.Serializer):
    """Serializer for pagination metadata"""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    current_page = serializers.IntegerField()


class ErrorSerializer(serializers.Serializer):
    """Standard error response format"""

    code = serializers.CharField()
    message = serializers.CharField()
    details = JSONSerializerField(required=False)


class SuccessResponseSerializer(serializers.Serializer):
    """Standard success response format"""

    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = JSONSerializerField(required=False)


# ===========================
# Mixin Serializers
# ===========================

class SlugRelatedFieldMixin:
    """Mixin for slug-based relationships"""

    slug_field = "slug"

    def get_fields(self):
        fields = super().get_fields()
        for field_name, field in fields.items():
            if isinstance(field, serializers.PrimaryKeyRelatedField):
                field = serializers.SlugRelatedField(
                    slug_field=self.slug_field,
                    queryset=field.queryset,
                )
                fields[field_name] = field
        return fields


class PermissionMixin:
    """Mixin for permission-based field visibility"""

    permission_fields = {}  # {"field_name": "permission.name"}

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")

        if request and self.permission_fields:
            user = request.user
            for field_name, permission in self.permission_fields.items():
                if field_name in fields and not user.has_perm(permission):
                    fields.pop(field_name)

        return fields


class TimezoneAwareDateTimeField(serializers.DateTimeField):
    """Handle timezone-aware datetime serialization"""

    def to_representation(self, value) -> str:
        """Convert to ISO format with timezone"""
        if value is None:
            return None
        return value.isoformat()