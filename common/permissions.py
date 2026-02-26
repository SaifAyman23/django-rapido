"""
Ultimate reusable Django REST Framework permissions
Provides production-grade permission classes with:
- Object-level permissions
- Role-based access control (RBAC)
- Permission caching
- Custom rule evaluation
"""

from typing import Optional, List, Callable, Any
from functools import lru_cache

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from django.contrib.auth.models import Permission, Group
from django.db.models import Model
import logging

logger = logging.getLogger(__name__)


# ===========================
# Base Permission Classes
# ===========================

class BasePermission(permissions.BasePermission):
    """Enhanced base permission with logging"""

    def __str__(self) -> str:
        return self.__class__.__name__

    def check_access(
        self,
        request: Request,
        view: APIView,
        obj: Optional[Model] = None,
    ) -> bool:
        """Override in subclasses"""
        return True

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check view-level permission"""
        result = self.check_access(request, view)
        if not result:
            logger.warning(
                f"Permission denied: {self} for {request.user} on {request.path}",
                extra={"user_id": request.user.id if request.user else None},
            )
        return result

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Model,
    ) -> bool:
        """Check object-level permission"""
        result = self.check_access(request, view, obj)
        if not result:
            logger.warning(
                f"Object permission denied: {self} for {request.user} on {obj}",
                extra={"user_id": request.user.id if request.user else None},
            )
        return result


# ===========================
# Authentication Permissions
# ===========================

class IsAuthenticated(BasePermission):
    """User must be authenticated"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        return bool(request.user and request.user.is_authenticated)


class IsAnonymous(BasePermission):
    """User must NOT be authenticated"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        return not request.user or not request.user.is_authenticated


class IsAuthenticatedOrReadOnly(BasePermission):
    """Authenticated users can do anything, others can only read"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


# ===========================
# Role-Based Permissions
# ===========================

class IsAdmin(BasePermission):
    """User must be admin/staff"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        return bool(request.user and request.user.is_staff)


class IsSuperUser(BasePermission):
    """User must be superuser"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        return bool(request.user and request.user.is_superuser)


class IsInGroup(BasePermission):
    """User must be in specified group(s)"""

    required_groups: List[str] = []

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if not self.required_groups:
            return True

        user_groups = request.user.groups.values_list("name", flat=True)
        return any(group in user_groups for group in self.required_groups)


class HasPermission(BasePermission):
    """User must have specific permission(s)"""

    required_permissions: List[str] = []

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        if not self.required_permissions:
            return True

        return all(
            request.user.has_perm(perm)
            for perm in self.required_permissions
        )


# ===========================
# Ownership Permissions
# ===========================

class IsOwner(BasePermission):
    """User must be the object owner"""

    owner_field: str = "user"

    def check_access(self, request: Request, view: APIView, obj: Optional[Model] = None) -> bool:
        if obj is None:
            return True

        try:
            owner = getattr(obj, self.owner_field)
            return owner == request.user
        except AttributeError:
            logger.error(f"Owner field '{self.owner_field}' not found on {obj.__class__.__name__}")
            return False


class IsOwnerOrReadOnly(BasePermission):
    """Owner can edit, others can only read"""

    owner_field: str = "user"

    def check_access(self, request: Request, view: APIView, obj: Optional[Model] = None) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if obj is None:
            return True

        try:
            owner = getattr(obj, self.owner_field)
            return owner == request.user
        except AttributeError:
            logger.error(f"Owner field '{self.owner_field}' not found on {obj.__class__.__name__}")
            return False


class IsOwnerOrAdmin(BasePermission):
    """Owner or admin can edit"""

    owner_field: str = "user"

    def check_access(self, request: Request, view: APIView, obj: Optional[Model] = None) -> bool:
        if request.user and request.user.is_staff:
            return True

        if obj is None:
            return True

        try:
            owner = getattr(obj, self.owner_field)
            return owner == request.user
        except AttributeError:
            logger.error(f"Owner field '{self.owner_field}' not found on {obj.__class__.__name__}")
            return False


# ===========================
# HTTP Method Permissions
# ===========================

class IsReadOnly(BasePermission):
    """Only allow safe methods"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        return request.method in permissions.SAFE_METHODS


class AllowGet(BasePermission):
    """Only allow GET requests"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        return request.method == "GET"


class AllowPost(BasePermission):
    """Only allow POST requests"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        return request.method == "POST"


class AllowGetPost(BasePermission):
    """Only allow GET and POST requests"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        return request.method in ["GET", "POST"]


# ===========================
# Complex Permissions
# ===========================

class MultiplePermissionsRequired(BasePermission):
    """Require multiple permissions with AND logic"""

    permissions: List[BasePermission] = []

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        if not self.permissions:
            return True

        for perm in self.permissions:
            if not perm.check_access(request, view, obj):
                return False

        return True


class AnyPermissionRequired(BasePermission):
    """Require any one of multiple permissions (OR logic)"""

    permissions: List[BasePermission] = []

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        if not self.permissions:
            return True

        return any(
            perm.check_access(request, view, obj)
            for perm in self.permissions
        )


class CustomPermissionRule(BasePermission):
    """Apply custom permission rule function"""

    rule_function: Optional[Callable[[Request, APIView, Optional[Model]], bool]] = None

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        if self.rule_function is None:
            return True

        try:
            return self.rule_function(request, view, obj)
        except Exception as e:
            logger.error(f"Error evaluating custom permission rule: {str(e)}", exc_info=True)
            return False


# ===========================
# Rate Limiting Permissions
# ===========================

class RateLimitPermission(BasePermission):
    """Rate limit based on user tier"""

    RATE_LIMITS = {
        "anonymous": 100,      # 100 requests
        "authenticated": 1000,  # 1000 requests
        "staff": 10000,        # 10000 requests
    }

    WINDOW_SIZE = 3600  # 1 hour in seconds

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        from django.core.cache import cache
        from django.utils import timezone
        from datetime import timedelta

        if not hasattr(request, "user"):
            return True

        user = request.user

        # Determine user tier
        if not user.is_authenticated:
            tier = "anonymous"
        elif user.is_staff:
            tier = "staff"
        else:
            tier = "authenticated"

        # Get rate limit
        limit = self.RATE_LIMITS.get(tier, 100)

        # Create cache key
        if user.is_authenticated:
            cache_key = f"rate_limit:{user.id}"
        else:
            ip = self.get_client_ip(request)
            cache_key = f"rate_limit:{ip}"

        # Check and update rate limit
        current_requests = cache.get(cache_key, 0)

        if current_requests >= limit:
            logger.warning(
                f"Rate limit exceeded for {tier} user",
                extra={"user_id": user.id if user.is_authenticated else None},
            )
            return False

        cache.set(cache_key, current_requests + 1, self.WINDOW_SIZE)
        return True

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Get client IP from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


# ===========================
# Verification Permissions
# ===========================

class IsVerified(BasePermission):
    """User must be verified (email, etc.)"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        return getattr(request.user, "is_verified", False)


class IsVerifiedOrReadOnly(BasePermission):
    """Verified users can do anything, others can only read"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        return getattr(request.user, "is_verified", False)


class HasTwoFactorEnabled(BasePermission):
    """User must have 2FA enabled"""

    def check_access(self, request: Request, view: APIView, obj=None) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        return getattr(request.user, "two_factor_enabled", False)


# ===========================
# Status-Based Permissions
# ===========================

class IsObjectActive(BasePermission):
    """Object must be active"""

    status_field: str = "status"

    def check_access(self, request: Request, view: APIView, obj: Optional[Model] = None) -> bool:
        if obj is None:
            return True

        try:
            status = getattr(obj, self.status_field)
            return status == "published" or status == "active"
        except AttributeError:
            logger.error(f"Status field '{self.status_field}' not found on {obj.__class__.__name__}")
            return False


class IsObjectPublished(BasePermission):
    """Object must be published"""

    def check_access(self, request: Request, view: APIView, obj: Optional[Model] = None) -> bool:
        if obj is None:
            return True

        return getattr(obj, "status", None) == "published"


# ===========================
# Permission Factories
# ===========================

def create_group_permission(group_name: str) -> type:
    """Factory to create a permission class for a specific group"""
    class GroupPermission(IsInGroup):
        required_groups = [group_name]

    GroupPermission.__name__ = f"Is{group_name.title()}"
    return GroupPermission


def create_permission_check(perm_string: str) -> type:
    """Factory to create a permission class for a specific permission"""
    class PermissionCheck(HasPermission):
        required_permissions = [perm_string]

    PermissionCheck.__name__ = f"Has{perm_string.replace('.', '_').title()}"
    return PermissionCheck


def combine_permissions(*permission_classes: type) -> type:
    """Combine multiple permission classes with AND logic"""
    class CombinedPermission(MultiplePermissionsRequired):
        permissions = [perm() for perm in permission_classes]

    CombinedPermission.__name__ = "Combined" + "And".join(
        perm.__name__ for perm in permission_classes
    )
    return CombinedPermission


# ===========================
# Caching Permissions
# ===========================

class CachedPermission(BasePermission):
    """Cache permission results for performance"""

    cache_timeout: int = 300  # 5 minutes

    @lru_cache(maxsize=1024)
    def _check_permission(self, user_id: int, object_id: int) -> bool:
        """Override this method in subclasses"""
        return True

    def has_object_permission(self, request: Request, view: APIView, obj: Model) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        user_id = request.user.id
        object_id = obj.id

        return self._check_permission(user_id, object_id)