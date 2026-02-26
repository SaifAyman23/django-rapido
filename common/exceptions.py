"""
Ultimate custom exception classes for Django REST Framework
Provides production-grade error handling with:
- Standardized error responses
- Error logging
- HTTP status codes
- Error tracking
"""

from typing import Dict, Any, Optional, List
from rest_framework import status
from rest_framework.exceptions import APIException
import logging

logger = logging.getLogger(__name__)


# ===========================
# Base Custom Exception
# ===========================

class ApplicationException(APIException):
    """Base application exception with logging"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An error occurred"
    default_code = "error"

    def __init__(
        self,
        detail: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(detail=detail, code=code)
        self.context = context or {}

        # Log the exception
        logger.error(
            f"{self.__class__.__name__}: {self.detail}",
            extra=self.context,
            exc_info=True,
        )

    def get_response(self) -> Dict[str, Any]:
        """Get standardized response format"""
        return {
            "error": {
                "code": self.detail_code,
                "message": str(self.detail),
                "status": self.status_code,
            },
            "context": self.context if self.context else None,
        }


# ===========================
# Validation Exceptions
# ===========================

class ValidationError(ApplicationException):
    """Validation error - 400"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error"
    default_code = "validation_error"


class FieldValidationError(ApplicationException):
    """Field-level validation error"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Field validation failed"
    default_code = "field_validation_error"

    def __init__(
        self,
        field: str,
        detail: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        full_detail = f"{field}: {detail}"
        super().__init__(detail=full_detail, context=context or {})
        self.field = field


class RequiredFieldMissingError(ValidationError):
    """Required field is missing"""

    default_detail = "Required field is missing"
    default_code = "required_field_missing"


class InvalidDataTypeError(ValidationError):
    """Invalid data type provided"""

    default_detail = "Invalid data type"
    default_code = "invalid_data_type"


# ===========================
# Authentication Exceptions
# ===========================

class AuthenticationError(ApplicationException):
    """Authentication error - 401"""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed"
    default_code = "authentication_error"


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password"""

    default_detail = "Invalid credentials"
    default_code = "invalid_credentials"


class TokenExpiredError(AuthenticationError):
    """Authentication token has expired"""

    default_detail = "Token has expired"
    default_code = "token_expired"


class InvalidTokenError(AuthenticationError):
    """Invalid authentication token"""

    default_detail = "Invalid token"
    default_code = "invalid_token"


class EmailNotVerifiedError(AuthenticationError):
    """Email not verified"""

    default_detail = "Email not verified"
    default_code = "email_not_verified"


# ===========================
# Permission Exceptions
# ===========================

class PermissionError(ApplicationException):
    """Permission denied - 403"""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Permission denied"
    default_code = "permission_denied"


class InsufficientPermissionsError(PermissionError):
    """User lacks required permissions"""

    default_detail = "Insufficient permissions"
    default_code = "insufficient_permissions"


class AdminOnlyError(PermissionError):
    """Admin access required"""

    default_detail = "Admin access required"
    default_code = "admin_only"


class OwnerOnlyError(PermissionError):
    """Only owner can perform this action"""

    default_detail = "Only owner can perform this action"
    default_code = "owner_only"


class RateLimitExceededError(PermissionError):
    """Rate limit exceeded"""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded"
    default_code = "rate_limit_exceeded"


# ===========================
# Resource Exceptions
# ===========================

class ResourceNotFoundError(ApplicationException):
    """Resource not found - 404"""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found"
    default_code = "not_found"

    def __init__(self, resource: str, identifier: str = ""):
        detail = f"{resource} not found"
        if identifier:
            detail += f": {identifier}"
        super().__init__(detail=detail)
        self.resource = resource
        self.identifier = identifier


class ObjectNotFoundError(ResourceNotFoundError):
    """Object does not exist"""

    default_detail = "Object does not exist"
    default_code = "object_not_found"


class UserNotFoundError(ResourceNotFoundError):
    """User does not exist"""

    default_detail = "User not found"
    default_code = "user_not_found"


class DuplicateError(ApplicationException):
    """Duplicate resource - 409"""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource already exists"
    default_code = "duplicate_error"


class DuplicateEmailError(DuplicateError):
    """Email already exists"""

    default_detail = "Email already exists"
    default_code = "duplicate_email"


class DuplicateUsernameError(DuplicateError):
    """Username already exists"""

    default_detail = "Username already exists"
    default_code = "duplicate_username"


# ===========================
# Business Logic Exceptions
# ===========================

class BusinessLogicError(ApplicationException):
    """Business logic violation - 422"""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Business logic error"
    default_code = "business_logic_error"


class InsufficientFundsError(BusinessLogicError):
    """Insufficient funds for transaction"""

    default_detail = "Insufficient funds"
    default_code = "insufficient_funds"


class InvalidStateTransitionError(BusinessLogicError):
    """Invalid state transition"""

    default_detail = "Invalid state transition"
    default_code = "invalid_state_transition"

    def __init__(
        self,
        current_state: str,
        attempted_state: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        detail = f"Cannot transition from {current_state} to {attempted_state}"
        context = context or {}
        context.update({
            "current_state": current_state,
            "attempted_state": attempted_state,
        })
        super().__init__(detail=detail, context=context)


class OperationNotAllowedError(BusinessLogicError):
    """Operation is not allowed in current state"""

    default_detail = "Operation not allowed"
    default_code = "operation_not_allowed"


class ResourceAlreadyDeletedError(BusinessLogicError):
    """Resource has already been deleted"""

    default_detail = "Resource has already been deleted"
    default_code = "already_deleted"


# ===========================
# External Service Exceptions
# ===========================

class ExternalServiceError(ApplicationException):
    """External service error - 502"""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "External service error"
    default_code = "external_service_error"


class PaymentProcessingError(ExternalServiceError):
    """Payment processing failed"""

    default_detail = "Payment processing failed"
    default_code = "payment_processing_error"


class EmailServiceError(ExternalServiceError):
    """Email service error"""

    default_detail = "Email service error"
    default_code = "email_service_error"


class SMSServiceError(ExternalServiceError):
    """SMS service error"""

    default_detail = "SMS service error"
    default_code = "sms_service_error"


# ===========================
# Database Exceptions
# ===========================

class DatabaseError(ApplicationException):
    """Database operation error - 500"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Database error"
    default_code = "database_error"


class TransactionError(DatabaseError):
    """Transaction failed"""

    default_detail = "Transaction failed"
    default_code = "transaction_error"


class ConnectionError(DatabaseError):
    """Database connection error"""

    default_detail = "Database connection error"
    default_code = "connection_error"


# ===========================
# Configuration Exceptions
# ===========================

class ConfigurationError(ApplicationException):
    """Configuration error - 500"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Configuration error"
    default_code = "configuration_error"


class MissingConfigurationError(ConfigurationError):
    """Required configuration is missing"""

    default_detail = "Missing configuration"
    default_code = "missing_configuration"

    def __init__(self, config_key: str, context: Optional[Dict[str, Any]] = None):
        detail = f"Missing configuration: {config_key}"
        super().__init__(detail=detail, context=context or {})
        self.config_key = config_key


# ===========================
# Utility Functions
# ===========================

def handle_exception(exception: Exception) -> Dict[str, Any]:
    """Convert any exception to standardized error response"""
    if isinstance(exception, ApplicationException):
        return exception.get_response()

    # Log unexpected exception
    logger.error(f"Unexpected exception: {str(exception)}", exc_info=True)

    return {
        "error": {
            "code": "internal_error",
            "message": "An unexpected error occurred",
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    }


def validate_or_raise(
    condition: bool,
    error_class: type,
    message: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Raise exception if condition is False"""
    if not condition:
        if message:
            raise error_class(detail=message, context=context)
        else:
            raise error_class(context=context)


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: List[str],
) -> None:
    """Validate that all required fields are present"""
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise RequiredFieldMissingError(
            detail=f"Missing fields: {', '.join(missing_fields)}",
            context={"missing_fields": missing_fields},
        )