"""
Ultimate reusable Django filters for DRF
Provides production-grade filtering with:
- Advanced query filtering
- Range filtering
- Date filtering
- Search optimization
"""

from typing import Any, List, Optional, Tuple
from datetime import timedelta

from django_filters import rest_framework as filters
from django.db.models import Model, QuerySet, Q
from django.utils import timezone
from rest_framework import serializers
import logging

logger = logging.getLogger(__name__)


# ===========================
# Custom Filter Classes
# ===========================

class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """Filter for comma-separated values"""
    pass


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    """Filter for multiple UUIDs"""
    pass


class DateRangeFilter(filters.FilterSet):
    """Filter by date range"""

    start_date = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        help_text="Filter records after this date",
    )
    end_date = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        help_text="Filter records before this date",
    )

    class Meta:
        model = None
        fields = []


class StatusFilter(filters.FilterSet):
    """Filter by status"""

    status = filters.CharFilter(
        field_name="status",
        method="filter_status",
        help_text="Filter by status",
    )

    def filter_status(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Filter by single or multiple statuses"""
        statuses = value.split(",") if value else []

        if statuses:
            return queryset.filter(status__in=statuses)

        return queryset

    class Meta:
        model = None
        fields = []


class VerifiedFilter(filters.FilterSet):
    """Filter by verification status"""

    verified = filters.BooleanFilter(
        field_name="is_verified",
        help_text="Filter verified/unverified",
    )

    class Meta:
        model = None
        fields = []


class ActiveFilter(filters.FilterSet):
    """Filter by active status"""

    active = filters.BooleanFilter(
        field_name="is_active",
        help_text="Filter active/inactive",
    )

    class Meta:
        model = None
        fields = []


class SearchableFilterSet(filters.FilterSet):
    """Base filterset with search capabilities"""

    search = filters.CharFilter(
        method="search_filter",
        help_text="Search across multiple fields",
    )

    search_fields: List[str] = []

    def search_filter(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Search across multiple fields"""
        if not value or not self.search_fields:
            return queryset

        # Build Q object for OR search
        q_objects = Q()

        for field in self.search_fields:
            lookup = f"{field}__icontains"
            q_objects |= Q(**{lookup: value})

        return queryset.filter(q_objects)

    class Meta:
        model = None
        fields = []


class RangeFilter(filters.FilterSet):
    """Filter by numeric range"""

    min_value = filters.NumberFilter(
        field_name="value",
        lookup_expr="gte",
        help_text="Minimum value",
    )
    max_value = filters.NumberFilter(
        field_name="value",
        lookup_expr="lte",
        help_text="Maximum value",
    )

    class Meta:
        model = None
        fields = []


class RecentFilter(filters.FilterSet):
    """Filter recent records"""

    recent_days = filters.NumberFilter(
        method="filter_recent",
        help_text="Filter records from last N days",
    )

    def filter_recent(self, queryset: QuerySet, name: str, value: int) -> QuerySet:
        """Filter records from last N days"""
        if not value:
            return queryset

        cutoff_date = timezone.now() - timedelta(days=int(value))
        return queryset.filter(created_at__gte=cutoff_date)

    class Meta:
        model = None
        fields = []


class PublishedFilter(filters.FilterSet):
    """Filter published vs draft"""

    published = filters.BooleanFilter(
        field_name="status",
        method="filter_published",
        help_text="Filter published/draft",
    )

    def filter_published(self, queryset: QuerySet, name: str, value: bool) -> QuerySet:
        """Filter by published status"""
        if value is None:
            return queryset

        status = "published" if value else "draft"
        return queryset.filter(status=status)

    class Meta:
        model = None
        fields = []


class AuthorFilter(filters.FilterSet):
    """Filter by author/creator"""

    author = filters.CharFilter(
        field_name="user__username",
        lookup_expr="iexact",
        help_text="Filter by author username",
    )

    author_id = filters.UUIDFilter(
        field_name="user__id",
        help_text="Filter by author ID",
    )

    class Meta:
        model = None
        fields = []


class TagFilter(filters.FilterSet):
    """Filter by tags"""

    tags = filters.CharFilter(
        field_name="tags__name",
        method="filter_tags",
        help_text="Filter by tags (comma-separated)",
    )

    def filter_tags(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Filter by multiple tags"""
        tags = value.split(",") if value else []

        if tags:
            return queryset.filter(tags__name__in=tags).distinct()

        return queryset

    class Meta:
        model = None
        fields = []


class PriceRangeFilter(filters.FilterSet):
    """Filter by price range"""

    min_price = filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
        help_text="Minimum price",
    )
    max_price = filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
        help_text="Maximum price",
    )

    class Meta:
        model = None
        fields = []


class RatingFilter(filters.FilterSet):
    """Filter by rating"""

    min_rating = filters.NumberFilter(
        field_name="rating",
        lookup_expr="gte",
        help_text="Minimum rating",
    )
    rating_count_min = filters.NumberFilter(
        field_name="rating_count",
        lookup_expr="gte",
        help_text="Minimum number of ratings",
    )

    class Meta:
        model = None
        fields = []


class DeletedFilter(filters.FilterSet):
    """Filter soft-deleted records"""

    include_deleted = filters.BooleanFilter(
        field_name="deleted_at",
        method="filter_deleted",
        help_text="Include deleted records",
    )

    def filter_deleted(self, queryset: QuerySet, name: str, value: bool) -> QuerySet:
        """Include or exclude deleted records"""
        if value:
            # Include deleted
            if hasattr(queryset, "all_with_deleted"):
                return queryset.all_with_deleted()
        else:
            # Only active
            if hasattr(queryset, "active"):
                return queryset.active()

        return queryset

    class Meta:
        model = None
        fields = []


# ===========================
# Composite Filters
# ===========================

class StandardUserFilter(SearchableFilterSet):
    """Standard user filtering"""

    search_fields = ["username", "email", "first_name", "last_name"]

    active = filters.BooleanFilter(
        field_name="is_active",
        help_text="Filter by active status",
    )
    verified = filters.BooleanFilter(
        field_name="is_verified",
        help_text="Filter by verification status",
    )
    staff = filters.BooleanFilter(
        field_name="is_staff",
        help_text="Filter by staff status",
    )

    class Meta:
        model = None
        fields = ["search", "active", "verified", "staff"]


class StandardContentFilter(SearchableFilterSet):
    """Standard content filtering"""

    search_fields = ["title", "description", "slug"]

    status = filters.CharFilter(
        field_name="status",
        help_text="Filter by status",
    )
    author = filters.CharFilter(
        field_name="user__username",
        help_text="Filter by author",
    )
    published_start = filters.DateTimeFilter(
        field_name="published_at",
        lookup_expr="gte",
    )
    published_end = filters.DateTimeFilter(
        field_name="published_at",
        lookup_expr="lte",
    )

    class Meta:
        model = None
        fields = ["search", "status", "author"]


# ===========================
# Filter Utilities
# ===========================

def apply_filters(
    queryset: QuerySet,
    filters_dict: dict[str, Any],
) -> QuerySet:
    """Apply multiple filters to queryset"""
    for field_name, value in filters_dict.items():
        if value is None:
            continue

        # Handle range filters
        if field_name.endswith("__gte"):
            queryset = queryset.filter(**{field_name: value})
        elif field_name.endswith("__lte"):
            queryset = queryset.filter(**{field_name: value})
        else:
            queryset = queryset.filter(**{field_name: value})

    return queryset


def get_filter_summary(queryset: QuerySet, filters_applied: dict) -> dict:
    """Get summary of applied filters"""
    return {
        "total_records": queryset.count(),
        "filters_applied": filters_applied,
        "query": str(queryset.query) if queryset else "",
    }