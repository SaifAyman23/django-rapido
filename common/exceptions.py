import logging
from typing import Any, Dict, List, Optional, Type

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ApplicationException(APIException):
    """Base application exception with automatic logging and structured error responses."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An error occurred"
    default_code = "error"

    def __init__(
        self,
        detail: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(detail=detail, code=code)
        self.context = context or {}

        if self.status_code >= 500:
            logger.error(
                f"{self.__class__.__name__}: {self.detail}",
                extra=self.context,
                exc_info=True,
            )
        elif self.status_code >= 400:
            logger.warning(
                f"{self.__class__.__name__}: {self.detail}",
                extra=self.context,
            )

    def get_response(self) -> Dict[str, Any]:
        """Return the standardized error response body."""
        return {
            "error": {
                "code": self.default_code,
                "message": str(self.detail),
                "status": self.status_code,
            },
            "context": self.context if self.context else None,
        }


# ---------------------------------------------------------------------------
# Validation — 400
# ---------------------------------------------------------------------------


class ValidationError(ApplicationException):
    """Validation error — request data did not pass validation."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error"
    default_code = "validation_error"


class FieldValidationError(ApplicationException):
    """Field-level validation error indicating which field failed."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Field validation failed"
    default_code = "field_validation_error"

    def __init__(
        self,
        field: str,
        detail: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        full_detail = f"{field}: {detail}"
        super().__init__(detail=full_detail, context=context or {})
        self.field = field


class RequiredFieldMissingError(ValidationError):
    """A required field was not provided in the request data."""

    default_detail = "Required field is missing"
    default_code = "required_field_missing"


# ---------------------------------------------------------------------------
# Authentication — 401
# ---------------------------------------------------------------------------


class AuthenticationError(ApplicationException):
    """Authentication failed — user is not authenticated."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed"
    default_code = "authentication_error"


class InvalidCredentialsError(AuthenticationError):
    """Provided username/password combination is invalid."""

    default_detail = "Invalid credentials"
    default_code = "invalid_credentials"


class TokenExpiredError(AuthenticationError):
    """The authentication token has expired and needs to be refreshed."""

    default_detail = "Token has expired"
    default_code = "token_expired"


class InvalidTokenError(AuthenticationError):
    """The provided token is malformed or unrecognised."""

    default_detail = "Invalid token"
    default_code = "invalid_token"


class EmailNotVerifiedError(AuthenticationError):
    """The user's email address has not been verified yet."""

    default_detail = "Email not verified"
    default_code = "email_not_verified"


# ---------------------------------------------------------------------------
# Permission — 403 / 429
# ---------------------------------------------------------------------------


class PermissionError(ApplicationException):
    """Permission denied — user lacks access to the requested resource."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Permission denied"
    default_code = "permission_denied"


class InsufficientPermissionsError(PermissionError):
    """User does not hold the required permission for this action."""

    default_detail = "Insufficient permissions"
    default_code = "insufficient_permissions"


class AdminOnlyError(PermissionError):
    """The requested action requires admin/staff privileges."""

    default_detail = "Admin access required"
    default_code = "admin_only"


class OwnerOnlyError(PermissionError):
    """Only the resource owner may perform this action."""

    default_detail = "Only owner can perform this action"
    default_code = "owner_only"


class RateLimitExceededError(PermissionError):
    """The client has exceeded the allowed rate limit."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded"
    default_code = "rate_limit_exceeded"


# ---------------------------------------------------------------------------
# Resources — 404 / 409
# ---------------------------------------------------------------------------


class ResourceNotFoundError(ApplicationException):
    """The requested resource could not be found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found"
    default_code = "not_found"

    def __init__(self, resource: str, identifier: str = "") -> None:
        detail = f"{resource} not found"
        if identifier:
            detail += f": {identifier}"
        super().__init__(detail=detail)
        self.resource = resource
        self.identifier = identifier


class DuplicateError(ApplicationException):
    """A resource with the same unique fields already exists."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource already exists"
    default_code = "duplicate_error"


class DuplicateEmailError(DuplicateError):
    """A user with the given email address already exists."""

    default_detail = "Email already exists"
    default_code = "duplicate_email"


# ---------------------------------------------------------------------------
# Business Logic — 422
# ---------------------------------------------------------------------------


class BusinessLogicError(ApplicationException):
    """The request violates a business rule or constraint."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Business logic error"
    default_code = "business_logic_error"


class InvalidStateTransitionError(BusinessLogicError):
    """An attempt was made to transition an entity to an invalid state."""

    default_detail = "Invalid state transition"
    default_code = "invalid_state_transition"

    def __init__(
        self,
        current_state: str,
        attempted_state: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        detail = f"Cannot transition from {current_state} to {attempted_state}"
        context = context or {}
        context.update(
            {
                "current_state": current_state,
                "attempted_state": attempted_state,
            }
        )
        super().__init__(detail=detail, context=context)


class OperationNotAllowedError(BusinessLogicError):
    """The requested operation is not permitted in the current state."""

    default_detail = "Operation not allowed"
    default_code = "operation_not_allowed"


# ---------------------------------------------------------------------------
# External Services — 502
# ---------------------------------------------------------------------------


class ExternalServiceError(ApplicationException):
    """An upstream / third-party service returned an error."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "External service error"
    default_code = "external_service_error"


class PaymentProcessingError(ExternalServiceError):
    """Payment gateway or processor rejected or failed to handle the request."""

    default_detail = "Payment processing failed"
    default_code = "payment_processing_error"


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    """DRF global exception handler that normalises all error responses."""
    response = exception_handler(exc, context)

    if isinstance(exc, ApplicationException):
        return Response(exc.get_response(), status=exc.status_code)

    if response is not None:
        response.data = {
            "error": {
                "code": getattr(exc, "default_code", "error"),
                "message": str(exc),
                "status": response.status_code,
            }
        }

    return response


# ---------------------------------------------------------------------------
# Validation Helpers
# ---------------------------------------------------------------------------


def validate_or_raise(
    condition: bool,
    error_class: Type[ApplicationException],
    message: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Raise *error_class* if *condition* is ``False``."""
    if not condition:
        if message:
            raise error_class(detail=message, context=context)
        raise error_class(context=context)


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: List[str],
) -> None:
    """Ensure all keys in *required_fields* exist in *data*."""
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise RequiredFieldMissingError(
            detail=f"Missing fields: {', '.join(missing_fields)}",
            context={"missing_fields": missing_fields},
        )
