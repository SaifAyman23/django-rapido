"""
Django REST Framework Permissions.

Comprehensive set of permission classes for DRF projects.
"""

import logging
from typing import Any, Callable, List, Optional, Tuple, Type

from django.core.cache import cache
from django.contrib.auth.models import Group, Permission
from django.db.models import Model
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import View

logger = logging.getLogger(__name__)


# =============================================================================
# 1. Authentication Permissions
# =============================================================================

class IsAuthenticated(BasePermission):
    """User must be authenticated."""

    def has_permission(self, request: Request, view: View) -> bool:
        return bool(request.user and request.user.is_authenticated)


class IsAnonymous(BasePermission):
    """User must NOT be authenticated."""

    def has_permission(self, request: Request, view: View) -> bool:
        return not request.user or not request.user.is_authenticated


class IsAuthenticatedOrReadOnly(BasePermission):
    """Authenticated users can do anything, others can only read."""

    def has_permission(self, request: Request, view: View) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


# =============================================================================
# 2. Role-Based Permissions
# =============================================================================

class IsAdmin(BasePermission):
    """User must be admin/staff (is_staff)."""

    def has_permission(self, request: Request, view: View) -> bool:
        return bool(request.user and request.user.is_staff)


class IsSuperUser(BasePermission):
    """User must be a superuser."""

    def has_permission(self, request: Request, view: View) -> bool:
        return bool(request.user and request.user.is_superuser)


class IsInGroup(BasePermission):
    """User must be in specified group(s)."""

    required_groups: List[str] = []

    def has_permission(self, request: Request, view: View) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if not self.required_groups:
            return True
        user_groups = request.user.groups.values_list("name", flat=True)
        return any(group in user_groups for group in self.required_groups)


class HasPermission(BasePermission):
    """User must have specific Django permission(s)."""

    required_permissions: List[str] = []

    def has_permission(self, request: Request, view: View) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if not self.required_permissions:
            return True
        return all(
            request.user.has_perm(perm)
            for perm in self.required_permissions
        )


# =============================================================================
# 3. Ownership Permissions
# =============================================================================

class IsOwner(BasePermission):
    """User must be the object owner (object-level)."""

    owner_field: str = "user"

    def has_object_permission(self, request: Request, view: View, obj: Model) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            owner = getattr(obj, self.owner_field)
        except AttributeError:
            logger.error("Owner field '%s' not found on %s", self.owner_field, obj)
            return False
        if owner is None:
            return False
        return owner == request.user


class IsOwnerOrReadOnly(BasePermission):
    """Owner can edit, others can only read (object-level)."""

    owner_field: str = "user"

    def has_object_permission(self, request: Request, view: View, obj: Model) -> bool:
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            owner = getattr(obj, self.owner_field)
        except AttributeError:
            return False
        return owner == request.user


class IsOwnerOrAdmin(BasePermission):
    """Owner or admin (staff) can edit (object-level)."""

    owner_field: str = "user"

    def has_object_permission(self, request: Request, view: View, obj: Model) -> bool:
        if request.user and request.user.is_staff:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            owner = getattr(obj, self.owner_field)
        except AttributeError:
            return False
        return owner == request.user


# =============================================================================
# 4. HTTP Method Permissions
# =============================================================================

class IsReadOnly(BasePermission):
    """Only allow safe methods (GET, HEAD, OPTIONS)."""

    def has_permission(self, request: Request, view: View) -> bool:
        return request.method in SAFE_METHODS


class AllowGet(BasePermission):
    """Only allow GET requests."""

    def has_permission(self, request: Request, view: View) -> bool:
        return request.method == "GET"


class AllowPost(BasePermission):
    """Only allow POST requests."""

    def has_permission(self, request: Request, view: View) -> bool:
        return request.method == "POST"


# =============================================================================
# 5. Complex Permissions
# =============================================================================

class MultiplePermissionsRequired(BasePermission):
    """Require all specified permissions (AND logic)."""

    permissions: List[Type[BasePermission]] = []

    def has_permission(self, request: Request, view: View) -> bool:
        if not self.permissions:
            return True
        return all(
            perm().has_permission(request, view) for perm in self.permissions
        )

    def has_object_permission(self, request: Request, view: View, obj: Model) -> bool:
        if not self.permissions:
            return True
        return all(
            perm().has_object_permission(request, view, obj) for perm in self.permissions
        )


class AnyPermissionRequired(BasePermission):
    """Require any one of specified permissions (OR logic)."""

    permissions: List[Type[BasePermission]] = []

    def has_permission(self, request: Request, view: View) -> bool:
        if not self.permissions:
            return True
        return any(
            perm().has_permission(request, view) for perm in self.permissions
        )

    def has_object_permission(self, request: Request, view: View, obj: Model) -> bool:
        if not self.permissions:
            return True
        return any(
            perm().has_object_permission(request, view, obj) for perm in self.permissions
        )


# =============================================================================
# 6. Rate Limiting Permission
# =============================================================================

class RateLimitPermission(BasePermission):
    """Rate limiting based on user tier.

    Tiers:
        - anonymous: 100 requests per hour
        - authenticated: 1000 requests per hour
        - staff: 10000 requests per hour
    """

    RATE_LIMITS: dict = {
        "anonymous": (100, 3600),
        "authenticated": (1000, 3600),
        "staff": (10000, 3600),
    }

    @classmethod
    def rate_limit_key(cls, request: Request) -> str:
        """Return the cache key for the given request."""
        if request.user.is_authenticated:
            return f"rate_limit:user:{request.user.id}"
        return f"rate_limit:ip:{cls.get_client_ip(request)}"

    @staticmethod
    def get_client_ip(request: Request) -> str:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def has_permission(self, request: Request, view: View) -> bool:
        if not request.user.is_authenticated:
            tier = "anonymous"
        elif request.user.is_staff:
            tier = "staff"
        else:
            tier = "authenticated"

        limit, window = self.RATE_LIMITS[tier]
        cache_key = self.rate_limit_key(request)

        current = cache.get(cache_key, 0)
        if current >= limit:
            logger.warning("Rate limit exceeded for tier '%s' (key=%s)", tier, cache_key)
            return False

        cache.set(cache_key, current + 1, window)
        return True


# =============================================================================
# 7. Custom Permission Rule
# =============================================================================

class CustomPermissionRule(BasePermission):
    """Apply a pluggable callable to determine access."""

    rule_function: Optional[Callable[[Request, View, Any], bool]] = None

    def has_permission(self, request: Request, view: View) -> bool:
        if self.rule_function is None:
            return True
        try:
            return bool(self.rule_function(request, view, None))
        except Exception as e:
            logger.error("Error in CustomPermissionRule '%s': %s", self.__class__.__name__, e)
            return False

    def has_object_permission(self, request: Request, view: View, obj: Model) -> bool:
        if self.rule_function is None:
            return True
        try:
            return bool(self.rule_function(request, view, obj))
        except Exception as e:
            logger.error("Error in CustomPermissionRule '%s': %s", self.__class__.__name__, e)
            return False


# =============================================================================
# 8. Permission Factories
# =============================================================================

def create_group_permission(group_name: str) -> type:
    """Factory to create a permission class for a specific group."""

    class GroupPermission(IsInGroup):
        required_groups = [group_name]

    GroupPermission.__name__ = f"Is{group_name.title()}"
    GroupPermission.__qualname__ = GroupPermission.__name__
    return GroupPermission


def create_permission_check(perm_string: str) -> type:
    """Factory to create a permission class for a specific Django permission."""

    class PermissionCheck(HasPermission):
        required_permissions = [perm_string]

    PermissionCheck.__name__ = f"Has{perm_string.replace('.', '_').title()}"
    PermissionCheck.__qualname__ = PermissionCheck.__name__
    return PermissionCheck


def combine_permissions(*permission_classes: Type[BasePermission]) -> type:
    """Combine multiple permissions into a single class with AND logic."""

    class_name = "Combined" + "And".join(p.__name__ for p in permission_classes)

    class CombinedPermission(MultiplePermissionsRequired):
        permissions = list(permission_classes)

    CombinedPermission.__name__ = class_name
    CombinedPermission.__qualname__ = class_name
    return CombinedPermission
