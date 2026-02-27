"""
Ultimate reusable Django REST Framework viewsets
Provides production-grade viewsets with:
- Advanced filtering and searching
- Automatic permission handling
- Audit logging
- Soft delete support
- Bulk operations
- Custom actions
"""

from typing import Any, Dict, Optional, List
from functools import wraps

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.exceptions import ValidationError, PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import QuerySet, Prefetch
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator
from .mixins import BaseViewSetMixin
import logging

logger = logging.getLogger(__name__)




# ===========================
# Base ViewSets
# ===========================

class BaseViewSet(BaseViewSetMixin, viewsets.ModelViewSet):
    """
    Ultimate base viewset with:
    - Dynamic filtering
    - Permission handling
    - Audit logging
    - Error handling
    """

    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    pagination_class = None
    serializer_class = None
    queryset = None

    # Configuration
    search_fields: List[str] = []
    ordering_fields: List[str] = []
    filterset_fields: List[str] = []
    permission_required: Optional[str] = None

    def get_queryset(self) -> QuerySet:
        """
        Override to add custom filtering
        Optimize queries with select_related and prefetch_related
        """
        queryset = super().get_queryset()

        # Apply optimizations
        if hasattr(self, "select_related_fields"):
            queryset = queryset.select_related(*self.select_related_fields)

        if hasattr(self, "prefetch_related_fields"):
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)

        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == "list":
            return getattr(self, "list_serializer_class", self.serializer_class)
        elif self.action == "create":
            return getattr(self, "create_serializer_class", self.serializer_class)
        elif self.action == "retrieve":
            return getattr(self, "retrieve_serializer_class", self.serializer_class)
        elif self.action == "update" or self.action == "partial_update":
            return getattr(self, "update_serializer_class", self.serializer_class)

        return self.serializer_class

    def get_permissions(self):
        """Dynamic permission handling based on action"""
        if self.action in ["create"]:
            permission_classes = [IsAuthenticated]
        elif self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = self.permission_classes

        return [permission() for permission in permission_classes]

    @log_action("CREATE")
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create instance with audit logging"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        logger.info(
            f"Created {self.basename}: {serializer.data.get('id')}",
            extra={"user_id": request.user.id},
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """Hook for custom create logic"""
        if hasattr(self, "get_user"):
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    @log_action("UPDATE")
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Update instance with audit logging"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(
            f"Updated {self.basename}: {instance.id}",
            extra={"user_id": request.user.id},
        )

        return Response(serializer.data)

    @log_action("DELETE")
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Delete instance with audit logging"""
        instance = self.get_object()
        instance_id = instance.id

        self.perform_destroy(instance)

        logger.info(
            f"Deleted {self.basename}: {instance_id}",
            extra={"user_id": request.user.id},
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def handle_exception(self, exc):
        """Enhanced error handling"""
        logger.error(
            f"Exception in {self.__class__.__name__}: {str(exc)}",
            exc_info=True,
            extra={"user_id": self.request.user.id if self.request.user else None},
        )
        return super().handle_exception(exc)


class SoftDeleteViewSet(BaseViewSet):
    """ViewSet with soft delete support"""

    @action(detail=False, methods=["get"])
    def deleted(self, request) -> Response:
        """Get soft-deleted records"""
        if not request.user.is_staff:
            raise PermissionDenied("Only staff can view deleted records")

        queryset = self.get_queryset().all_with_deleted().deleted()
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None) -> Response:
        """Restore soft-deleted record"""
        instance = self.get_object()

        if not hasattr(instance, "restore"):
            return Response(
                {"error": "This model does not support restoration"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.restore()
        serializer = self.get_serializer(instance)

        logger.info(f"Restored {self.basename}: {instance.id}", extra={"user_id": request.user.id})

        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_restore(self, request) -> Response:
        """Restore multiple soft-deleted records"""
        if not request.user.is_staff:
            raise PermissionDenied("Only staff can restore records")

        ids = request.data.get("ids", [])
        queryset = self.get_queryset().all_with_deleted().deleted().filter(id__in=ids)
        count = queryset.restore()

        logger.info(f"Bulk restored {count} {self.basename}", extra={"user_id": request.user.id})

        return Response({
            "message": f"Successfully restored {count} records",
            "count": count,
        })


class PublishableViewSet(BaseViewSet):
    """ViewSet for publishable models"""

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None) -> Response:
        """Publish record"""
        instance = self.get_object()

        if not hasattr(instance, "publish"):
            return Response(
                {"error": "This model does not support publishing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.publish()
        serializer = self.get_serializer(instance)

        logger.info(f"Published {self.basename}: {instance.id}", extra={"user_id": request.user.id})

        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None) -> Response:
        """Unpublish record"""
        instance = self.get_object()

        if not hasattr(instance, "unpublish"):
            return Response(
                {"error": "This model does not support unpublishing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.unpublish()
        serializer = self.get_serializer(instance)

        logger.info(f"Unpublished {self.basename}: {instance.id}", extra={"user_id": request.user.id})

        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def published(self, request) -> Response:
        """Get published records only"""
        queryset = self.get_queryset().filter(status="published")
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)


class RatableViewSet(BaseViewSet):
    """ViewSet for rateable models"""

    @action(detail=True, methods=["post"])
    def rate(self, request, pk=None) -> Response:
        """Rate an object"""
        instance = self.get_object()

        rating = request.data.get("rating")
        if not rating:
            raise ValidationError({"rating": "Rating is required"})

        if not hasattr(instance, "update_rating"):
            return Response(
                {"error": "This model does not support ratings"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_rating = instance.update_rating(float(rating))
            logger.info(
                f"Rated {self.basename}: {instance.id} with {rating}",
                extra={"user_id": request.user.id},
            )

            return Response({
                "message": "Rating saved",
                "rating": new_rating,
            })
        except ValueError as e:
            raise ValidationError({"rating": str(e)})


# ===========================
# Bulk Operation ViewSet
# ===========================

class BulkOperationViewSet(BaseViewSet):
    """ViewSet with bulk create/update/delete support"""

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def bulk_create(self, request) -> Response:
        """Create multiple instances"""
        data = request.data

        if not isinstance(data, list):
            raise ValidationError({"detail": "Expected a list of objects"})

        serializer = self.get_serializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)

        logger.info(
            f"Bulk created {len(serializer.data)} {self.basename}",
            extra={"user_id": request.user.id},
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_create(self, serializer):
        """Perform bulk create"""
        serializer.save()

    @action(detail=False, methods=["patch"])
    @transaction.atomic
    def bulk_update(self, request) -> Response:
        """Update multiple instances"""
        data = request.data

        if not isinstance(data, list):
            raise ValidationError({"detail": "Expected a list of objects"})

        if not all("id" in item for item in data):
            raise ValidationError({"detail": "Each object must have an 'id' field"})

        # Get instances
        ids = [item["id"] for item in data]
        instances = {obj.id: obj for obj in self.get_queryset().filter(id__in=ids)}

        serializer = self.get_serializer(
            [instances[item["id"]] for item in data if item["id"] in instances],
            data=data,
            many=True,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_update(serializer)

        logger.info(
            f"Bulk updated {len(serializer.data)} {self.basename}",
            extra={"user_id": request.user.id},
        )

        return Response(serializer.data)

    def perform_bulk_update(self, serializer):
        """Perform bulk update"""
        serializer.save()

    @action(detail=False, methods=["delete"])
    @transaction.atomic
    def bulk_delete(self, request) -> Response:
        """Delete multiple instances"""
        ids = request.data.get("ids", [])

        if not ids:
            raise ValidationError({"ids": "At least one ID is required"})

        queryset = self.get_queryset().filter(id__in=ids)
        count, _ = queryset.delete()

        logger.info(
            f"Bulk deleted {count} {self.basename}",
            extra={"user_id": request.user.id},
        )

        return Response({
            "message": f"Successfully deleted {count} records",
            "count": count,
        })


# ===========================
# User ViewSet
# ===========================

class UserViewSet(BaseViewSet):
    """Complete user management viewset"""

    queryset = None  # Set this in your concrete implementation
    serializer_class = None  # Set this in your concrete implementation
    permission_classes = [IsAuthenticated]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["created_at", "username"]

    def get_permissions(self):
        """Allow registration without authentication"""
        if self.action == "register":
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def me(self, request) -> Response:
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    @transaction.atomic
    def register(self, request) -> Response:
        """Register new user"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        logger.info(f"New user registered: {user.email}")

        return Response(
            {"message": "User registered successfully", "user": self.get_serializer(user).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def change_password(self, request) -> Response:
        """Change user password"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        logger.info(f"Password changed for user: {user.email}")

        return Response({"message": "Password changed successfully"})

    @action(detail=False, methods=["get"])
    def active(self, request) -> Response:
        """Get active users"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def verified(self, request) -> Response:
        """Get verified users"""
        queryset = self.get_queryset().filter(is_verified=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ===========================
# Caching & Performance
# ===========================

class CachedViewSet(BaseViewSet):
    """ViewSet with caching support"""

    cache_timeout: int = 300  # 5 minutes

    @method_decorator(cache_page(cache_timeout))
    def list(self, request, *args, **kwargs):
        """Cache list view"""
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    def clear_cache(self, request) -> Response:
        """Clear cache for this viewset"""
        from django.core.cache import cache
        
        if not request.user.is_staff:
            raise PermissionDenied("Only staff can clear cache")

        cache.clear()
        logger.info("Cache cleared by", extra={"user_id": request.user.id})

        return Response({"message": "Cache cleared successfully"})