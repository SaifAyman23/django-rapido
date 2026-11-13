"""Password policy helpers shared by register, reset, and change."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()


def password_validator_errors(password: str, *, email: str = "", user=None) -> list:
    """Return Django validator messages for ``password`` (empty when valid)."""
    candidate = user or User(email=email or "", username=(email or "").split("@")[0])
    try:
        validate_password(password, candidate)
    except DjangoValidationError as exc:
        return list(exc.messages)
    return []
