from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from rest_framework import serializers


def validate_credentials(email, password):
    """Validate email/password and return user."""
    User = get_user_model()

    if not email or not password:
        raise serializers.ValidationError({"detail": _("Please fill in all fields")})

    user = User.objects.filter(email=email).first()

    if not user or not user.check_password(password):
        raise serializers.ValidationError({"detail": _("Incorrect email or password")})

    if user.status == User.Status.UNVERIFIED:
        raise serializers.ValidationError({"detail": _("Please verify your email first")})

    if user.status == User.Status.SUSPENDED:
        raise serializers.ValidationError({"detail": _("Your account has been suspended. Contact support.")})

    return user
