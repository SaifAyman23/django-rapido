# Django REST Framework Custom Exceptions Guide

**A comprehensive guide to implementing production-grade exception handling**

---

## Table of Contents

1. [Overview](#overview)
2. [Base Exception Class](#base-exception-class)
3. [Validation Exceptions](#validation-exceptions)
4. [Authentication Exceptions](#authentication-exceptions)
5. [Permission Exceptions](#permission-exceptions)
6. [Resource Exceptions](#resource-exceptions)
7. [Business Logic Exceptions](#business-logic-exceptions)
8. [External Service Exceptions](#external-service-exceptions)
9. [Database Exceptions](#database-exceptions)
10. [Exception Handling](#exception-handling)
11. [Best Practices](#best-practices)

---

## Overview

Custom exceptions provide standardized error handling across your Django REST Framework application. They ensure consistent error responses, proper logging, and better debugging.

### Why Custom Exceptions?

- **Consistency** — Uniform error format across API
- **Logging** — Automatic error logging
- **Clarity** — Clear error messages for clients
- **Debugging** — Better error tracking
- **HTTP Codes** — Proper status codes

### Quick Start

```python
from rest_framework.exceptions import APIException
from rest_framework import status

class CustomException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred"
    default_code = "error"

# Usage
raise CustomException(detail="Something went wrong")
```

---

## Base Exception Class

### ApplicationException

```python
from typing import Dict, Any, Optional
from rest_framework.exceptions import APIException
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


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
                "code": self.default_code,
                "message": str(self.detail),
                "status": self.status_code,
            },
            "context": self.context if self.context else None,
        }
```

**Features:**
- Automatic logging
- Structured error responses
- Context data support
- Standardized format

**Usage:**

```python
raise ApplicationException(
    detail="Database connection failed",
    context={"database": "main", "attempt": 3}
)
```

**Response:**

```json
{
  "error": {
    "code": "error",
    "message": "Database connection failed",
    "status": 500
  },
  "context": {
    "database": "main",
    "attempt": 3
  }
}
```

---

## Validation Exceptions

### ValidationError

```python
class ValidationError(ApplicationException):
    """Validation error - 400"""
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error"
    default_code = "validation_error"
```

**Usage:**

```python
if not email:
    raise ValidationError(detail="Email is required")

if len(password) < 8:
    raise ValidationError(
        detail="Password too short",
        context={"min_length": 8, "provided": len(password)}
    )
```

### FieldValidationError

```python
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
```

**Usage:**

```python
raise FieldValidationError(
    field="email",
    detail="Invalid email format",
    context={"provided": "invalid@@@email"}
)
```

### RequiredFieldMissingError

```python
class RequiredFieldMissingError(ValidationError):
    """Required field is missing"""
    
    default_detail = "Required field is missing"
    default_code = "required_field_missing"
```

**Usage:**

```python
if 'email' not in data:
    raise RequiredFieldMissingError(detail="Email field is required")
```

---

## Authentication Exceptions

### AuthenticationError

```python
class AuthenticationError(ApplicationException):
    """Authentication error - 401"""
    
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed"
    default_code = "authentication_error"
```

### InvalidCredentialsError

```python
class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password"""
    
    default_detail = "Invalid credentials"
    default_code = "invalid_credentials"
```

**Usage:**

```python
user = authenticate(username=username, password=password)
if not user:
    raise InvalidCredentialsError()
```

### TokenExpiredError

```python
class TokenExpiredError(AuthenticationError):
    """Authentication token has expired"""
    
    default_detail = "Token has expired"
    default_code = "token_expired"
```

**Usage:**

```python
if token.is_expired():
    raise TokenExpiredError(
        context={"expired_at": token.expired_at}
    )
```

### InvalidTokenError

```python
class InvalidTokenError(AuthenticationError):
    """Invalid authentication token"""
    
    default_detail = "Invalid token"
    default_code = "invalid_token"
```

### EmailNotVerifiedError

```python
class EmailNotVerifiedError(AuthenticationError):
    """Email not verified"""
    
    default_detail = "Email not verified"
    default_code = "email_not_verified"
```

**Usage:**

```python
if not user.email_verified:
    raise EmailNotVerifiedError(
        context={"email": user.email}
    )
```

---

## Permission Exceptions

### PermissionError

```python
class PermissionError(ApplicationException):
    """Permission denied - 403"""
    
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Permission denied"
    default_code = "permission_denied"
```

### InsufficientPermissionsError

```python
class InsufficientPermissionsError(PermissionError):
    """User lacks required permissions"""
    
    default_detail = "Insufficient permissions"
    default_code = "insufficient_permissions"
```

**Usage:**

```python
if not user.has_perm('articles.publish'):
    raise InsufficientPermissionsError(
        detail="Cannot publish articles",
        context={"required_permission": "articles.publish"}
    )
```

### AdminOnlyError

```python
class AdminOnlyError(PermissionError):
    """Admin access required"""
    
    default_detail = "Admin access required"
    default_code = "admin_only"
```

**Usage:**

```python
if not user.is_staff:
    raise AdminOnlyError()
```

### OwnerOnlyError

```python
class OwnerOnlyError(PermissionError):
    """Only owner can perform this action"""
    
    default_detail = "Only owner can perform this action"
    default_code = "owner_only"
```

**Usage:**

```python
if article.author != request.user:
    raise OwnerOnlyError(
        context={"owner_id": article.author.id}
    )
```

### RateLimitExceededError

```python
class RateLimitExceededError(PermissionError):
    """Rate limit exceeded"""
    
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded"
    default_code = "rate_limit_exceeded"
```

**Usage:**

```python
if requests_count > limit:
    raise RateLimitExceededError(
        context={"limit": limit, "window": "1 hour"}
    )
```

---

## Resource Exceptions

### ResourceNotFoundError

```python
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
```

**Usage:**

```python
article = Article.objects.filter(id=article_id).first()
if not article:
    raise ResourceNotFoundError(
        resource="Article",
        identifier=str(article_id)
    )
```

### DuplicateError

```python
class DuplicateError(ApplicationException):
    """Duplicate resource - 409"""
    
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource already exists"
    default_code = "duplicate_error"
```

### DuplicateEmailError

```python
class DuplicateEmailError(DuplicateError):
    """Email already exists"""
    
    default_detail = "Email already exists"
    default_code = "duplicate_email"
```

**Usage:**

```python
if User.objects.filter(email=email).exists():
    raise DuplicateEmailError(
        context={"email": email}
    )
```

---

## Business Logic Exceptions

### BusinessLogicError

```python
class BusinessLogicError(ApplicationException):
    """Business logic violation - 422"""
    
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Business logic error"
    default_code = "business_logic_error"
```

### InvalidStateTransitionError

```python
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
```

**Usage:**

```python
if article.status == 'archived' and new_status == 'published':
    raise InvalidStateTransitionError(
        current_state='archived',
        attempted_state='published'
    )
```

### OperationNotAllowedError

```python
class OperationNotAllowedError(BusinessLogicError):
    """Operation is not allowed in current state"""
    
    default_detail = "Operation not allowed"
    default_code = "operation_not_allowed"
```

---

## External Service Exceptions

### ExternalServiceError

```python
class ExternalServiceError(ApplicationException):
    """External service error - 502"""
    
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "External service error"
    default_code = "external_service_error"
```

### PaymentProcessingError

```python
class PaymentProcessingError(ExternalServiceError):
    """Payment processing failed"""
    
    default_detail = "Payment processing failed"
    default_code = "payment_processing_error"
```

**Usage:**

```python
try:
    charge_customer(payment)
except StripeError as e:
    raise PaymentProcessingError(
        detail=str(e),
        context={"payment_id": payment.id}
    )
```

---

## Exception Handling

### Global Exception Handler

```python
from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    """Custom exception handler"""
    
    # Call DRF's default handler first
    response = exception_handler(exc, context)
    
    # Handle custom exceptions
    if isinstance(exc, ApplicationException):
        return Response(
            exc.get_response(),
            status=exc.status_code
        )
    
    # Handle other exceptions
    if response is not None:
        response.data = {
            "error": {
                "code": getattr(exc, 'default_code', 'error'),
                "message": str(exc),
                "status": response.status_code,
            }
        }
    
    return response

# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'myapp.exceptions.custom_exception_handler',
}
```

### Validation Helper

```python
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

# Usage
validate_or_raise(
    user.is_verified,
    EmailNotVerifiedError,
    "Please verify your email first"
)
```

### Field Validation Helper

```python
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

# Usage
validate_required_fields(
    request.data,
    ['email', 'password', 'username']
)
```

---

## Best Practices

### 1. Use Specific Exceptions

✅ **Good:**

```python
if not user:
    raise UserNotFoundError(identifier=user_id)

if payment_failed:
    raise PaymentProcessingError(detail="Card declined")
```

❌ **Bad:**

```python
if not user:
    raise Exception("User not found")

if payment_failed:
    raise Exception("Payment failed")
```

### 2. Include Context

✅ **Good:**

```python
raise InvalidStateTransitionError(
    current_state=article.status,
    attempted_state='published',
    context={"article_id": article.id}
)
```

❌ **Bad:**

```python
raise InvalidStateTransitionError(
    current_state=article.status,
    attempted_state='published'
)
```

### 3. Log Appropriately

```python
class ApplicationException(APIException):
    def __init__(self, detail=None, code=None, context=None):
        super().__init__(detail, code)
        self.context = context or {}
        
        # Log with appropriate level
        if self.status_code >= 500:
            logger.error(f"{self.__class__.__name__}: {detail}", extra=context)
        elif self.status_code >= 400:
            logger.warning(f"{self.__class__.__name__}: {detail}", extra=context)
```

### 4. Provide Clear Messages

✅ **Good:**

```python
raise ValidationError(
    detail="Password must be at least 8 characters long",
    context={"min_length": 8, "provided": 5}
)
```

❌ **Bad:**

```python
raise ValidationError(detail="Invalid password")
```

### 5. Test Exception Handling

```python
class ExceptionTest(TestCase):
    def test_validation_error(self):
        """Test validation error response"""
        with self.assertRaises(ValidationError) as context:
            validate_password("")
        
        self.assertEqual(
            context.exception.status_code,
            400
        )
    
    def test_not_found_error(self):
        """Test 404 error"""
        response = self.client.get('/api/articles/999/')
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json())
```

---

## Summary

| Exception | Status | Use Case |
|-----------|--------|----------|
| **ValidationError** | 400 | Invalid input data |
| **AuthenticationError** | 401 | Auth failed |
| **PermissionError** | 403 | Access denied |
| **ResourceNotFoundError** | 404 | Resource doesn't exist |
| **DuplicateError** | 409 | Resource already exists |
| **BusinessLogicError** | 422 | Business rule violation |
| **ExternalServiceError** | 502 | Third-party service error |
| **ApplicationException** | 500 | Generic server error |

---

**Key Takeaways:**

- Use specific exception classes
- Include context information
- Log exceptions appropriately
- Provide clear error messages
- Use proper HTTP status codes
- Test exception handling
- Create custom handler for consistency