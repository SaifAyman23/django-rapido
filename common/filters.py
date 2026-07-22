"""Common filter classes for DRF viewsets.

Provides reusable FilterSet classes covering:
- Basic custom filter fields (CharInFilter, UUIDInFilter)
- Date range filtering
- Status / boolean filtering
- Multi-field search
- Numeric / price / rating range filtering
- Composite filters (user, content, author, tags, soft-delete)
"""

from datetime import timedelta
from typing import Any, ClassVar, Optional

from django.db.models import CharField, Q, Value
from django.db.models.query import QuerySet
from django.utils import timezone
from django_filters import rest_framework as filters

# ---------------------------------------------------------------------------
# 1. Basic custom filter fields
# ---------------------------------------------------------------------------


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """Filter that accepts a comma-separated list of string values for ``__in`` lookups.

    Usage: ``?status=draft,published,archived``
    """

    pass


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    """Filter that accepts a comma-separated list of UUID values for ``__in`` lookups.

    Usage: ``?ids=abc-123,def-456,ghi-789``
    """

    pass


# ---------------------------------------------------------------------------
# 2. Date range filtering
# ---------------------------------------------------------------------------


class DateRangeFilter(filters.FilterSet):
    """Filter a ``created_at``-style field by an inclusive start/end date range.

    Parameters
    ----------
    start_date : str (ISO-8601 date / datetime)
        Return records **on or after** this timestamp.
    end_date : str (ISO-8601 date / datetime)
        Return records **on or before** this timestamp.
    """

    start_date = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        help_text="Filter records after this date (ISO-8601).",
    )
    end_date = filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        help_text="Filter records before this date (ISO-8601).",
    )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class RecentFilter(filters.FilterSet):
    """Return only records created within the last *N* days.

    Parameters
    ----------
    recent_days : int
        Number of days to look back from now.
    """

    recent_days = filters.NumberFilter(
        method="filter_recent",
        help_text="Filter records from the last N days.",
    )

    def filter_recent(self, queryset: QuerySet, name: str, value: Any) -> QuerySet:
        """Filter queryset to records created in the last ``value`` days."""
        if not value:
            return queryset

        cutoff_date = timezone.now() - timedelta(days=int(value))
        return queryset.filter(created_at__gte=cutoff_date)

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class DateShortcutFilter(filters.FilterSet):
    """Allow clients to use human-friendly date shortcuts.

    Parameters
    ----------
    date_filter : str
        One of ``today``, ``this_week``, ``this_month``, ``this_year``.
    """

    date_filter = filters.CharFilter(
        method="filter_by_date_range",
        help_text="Options: today, this_week, this_month, this_year",
    )

    def filter_by_date_range(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Translate a shortcut name into a ``created_at__gte`` filter."""
        now = timezone.now()

        if value == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif value == "this_week":
            start = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif value == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif value == "this_year":
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return queryset

        return queryset.filter(created_at__gte=start)

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


# ---------------------------------------------------------------------------
# 3. Status / boolean filters
# ---------------------------------------------------------------------------


class StatusFilter(filters.FilterSet):
    """Filter records by one or more comma-separated status values.

    Parameters
    ----------
    status : str
        Single status or comma-separated list (e.g. ``published,draft``).
    """

    status = filters.CharFilter(
        field_name="status",
        method="filter_status",
        help_text="Filter by single or multiple statuses (comma-separated).",
    )

    def filter_status(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Split comma-separated statuses into an ``__in`` lookup."""
        statuses = [s.strip() for s in value.split(",") if s.strip()] if value else []

        if statuses:
            return queryset.filter(status__in=statuses)

        return queryset

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class VerifiedFilter(filters.FilterSet):
    """Filter by ``is_verified`` boolean field."""

    verified = filters.BooleanFilter(
        field_name="is_verified",
        help_text="Filter verified (true) / unverified (false) records.",
    )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class ActiveFilter(filters.FilterSet):
    """Filter by ``is_active`` boolean field."""

    active = filters.BooleanFilter(
        field_name="is_active",
        help_text="Filter active (true) / inactive (false) records.",
    )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class PublishedFilter(filters.FilterSet):
    """Convenience filter that maps a boolean to a ``status`` CharField.

    When ``published=true`` the queryset is filtered to ``status='published'``;
    when ``false`` it returns records whose status is ``'draft'``.
    """

    published = filters.BooleanFilter(
        field_name="status",
        method="filter_published",
        help_text="Filter published (true) / draft (false) records.",
    )

    def filter_published(self, queryset: QuerySet, name: str, value: Optional[bool]) -> QuerySet:
        """Translate boolean to a status string."""
        if value is None:
            return queryset

        status = "published" if value else "draft"
        return queryset.filter(status=status)

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


# ---------------------------------------------------------------------------
# 4. Search filters
# ---------------------------------------------------------------------------


class SearchableFilterSet(filters.FilterSet):
    """Base FilterSet that provides a **multi-field OR search**.

    Subclasses **must** define ``search_fields`` — a list of field names
    (optionally spanning relations, e.g. ``author__username``) that will be
    searched with an ``__icontains`` lookup combined via ``|`` (OR).

    Parameters
    ----------
    search : str
        Free-text search term.
    """

    search = filters.CharFilter(
        method="search_filter",
        help_text="Search across multiple fields.",
    )

    search_fields: ClassVar[list[str]] = []

    def search_filter(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Build an OR query across all fields listed in ``search_fields``."""
        if not value or not self.search_fields:
            return queryset

        q_objects = Q()

        for field in self.search_fields:
            lookup = f"{field}__icontains"
            q_objects |= Q(**{lookup: value})

        return queryset.filter(q_objects)

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class AdvancedSearchFilter(filters.FilterSet):
    """PostgreSQL full-text search with relevance ranking.

    Uses ``SearchVector`` and ``SearchQuery`` to rank results.  The vector
    weight gives **title** matches priority (weight ``A``) over **content**
    matches (weight ``B``).

    Parameters
    ----------
    search : str
        Full-text search query.
    """

    search = filters.CharFilter(
        method="search_filter",
        help_text="PostgreSQL full-text search with relevance ranking.",
    )

    def search_filter(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Apply full-text search and order by descending rank."""
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        if not value:
            return queryset

        vector = SearchVector("title", weight="A") + SearchVector("content", weight="B")
        query = SearchQuery(value)

        return (
            queryset.annotate(rank=SearchRank(vector, query))
            .filter(rank__gte=0.1)
            .order_by("-rank")
        )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


# ---------------------------------------------------------------------------
# 5. Range filters
# ---------------------------------------------------------------------------


class RangeFilter(filters.FilterSet):
    """Generic numeric range filter.

    Parameters
    ----------
    min_value : number
        Inclusive lower bound.
    max_value : number
        Inclusive upper bound.
    """

    min_value = filters.NumberFilter(
        field_name="value",
        lookup_expr="gte",
        help_text="Minimum value.",
    )
    max_value = filters.NumberFilter(
        field_name="value",
        lookup_expr="lte",
        help_text="Maximum value.",
    )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class PriceRangeFilter(filters.FilterSet):
    """Filter a ``price`` decimal field by inclusive bounds.

    Parameters
    ----------
    min_price : number
        Minimum price (inclusive).
    max_price : number
        Maximum price (inclusive).
    """

    min_price = filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
        help_text="Minimum price.",
    )
    max_price = filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
        help_text="Maximum price.",
    )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class RatingFilter(filters.FilterSet):
    """Filter by minimum rating and/or minimum rating count.

    Parameters
    ----------
    min_rating : number (1–5)
        Minimum average rating.
    rating_count_min : int
        Minimum number of ratings the entity must have.
    """

    min_rating = filters.NumberFilter(
        field_name="rating",
        lookup_expr="gte",
        help_text="Minimum rating (1-5).",
    )
    rating_count_min = filters.NumberFilter(
        field_name="rating_count",
        lookup_expr="gte",
        help_text="Minimum number of ratings.",
    )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


# ---------------------------------------------------------------------------
# 6. Composite filters
# ---------------------------------------------------------------------------


class StandardUserFilter(SearchableFilterSet):
    """Standard user admin filter with search, active, verified & staff flags.

    Parameters
    ----------
    search : str
        Searches ``username``, ``email``, ``first_name``, ``last_name``.
    active : bool
    verified : bool
    staff : bool
    """

    search_fields: ClassVar[list[str]] = ["username", "email", "first_name", "last_name"]

    active = filters.BooleanFilter(
        field_name="is_active",
        help_text="Filter by active status.",
    )
    verified = filters.BooleanFilter(
        field_name="is_verified",
        help_text="Filter by verification status.",
    )
    staff = filters.BooleanFilter(
        field_name="is_staff",
        help_text="Filter by staff status.",
    )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = ["search", "active", "verified", "staff"]


class StandardContentFilter(SearchableFilterSet):
    """Standard content / article admin filter.

    Parameters
    ----------
    search : str
        Searches ``title``, ``description``, ``slug``.
    status : str
    author : str
        Matches against ``user__username``.
    published_start : str (ISO-8601)
    published_end : str (ISO-8601)
    """

    search_fields: ClassVar[list[str]] = ["title", "description", "slug"]

    status = filters.CharFilter(
        field_name="status",
        help_text="Filter by status.",
    )
    author = filters.CharFilter(
        field_name="user__username",
        help_text="Filter by author username.",
    )
    published_start = filters.DateTimeFilter(
        field_name="published_at",
        lookup_expr="gte",
        help_text="Published after this date.",
    )
    published_end = filters.DateTimeFilter(
        field_name="published_at",
        lookup_expr="lte",
        help_text="Published before this date.",
    )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = ["search", "status", "author"]


class AuthorFilter(filters.FilterSet):
    """Filter content by author username or UUID.

    Parameters
    ----------
    author : str
        Case-insensitive exact match on ``user__username``.
    author_id : str (UUID)
        Exact match on ``user__id``.
    """

    author = filters.CharFilter(
        field_name="user__username",
        lookup_expr="iexact",
        help_text="Filter by author username (case-insensitive).",
    )
    author_id = filters.UUIDFilter(
        field_name="user__id",
        help_text="Filter by author UUID.",
    )

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class TagFilter(filters.FilterSet):
    """Filter records by one or more comma-separated tag names.

    Results are ``.distinct()`` to avoid duplicates from the M2M join.

    Parameters
    ----------
    tags : str
        Comma-separated tag names (e.g. ``python,django,web``).
    """

    tags = filters.CharFilter(
        field_name="tags__name",
        method="filter_tags",
        help_text="Filter by tags (comma-separated).",
    )

    def filter_tags(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Split comma-separated tags into an ``__in`` lookup with ``distinct()``."""
        tag_list = [t.strip() for t in value.split(",") if t.strip()] if value else []

        if tag_list:
            return queryset.filter(tags__name__in=tag_list).distinct()

        return queryset

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []


class DeletedFilter(filters.FilterSet):
    """Toggle inclusion of soft-deleted records.

    When ``include_deleted=true`` the queryset will include soft-deleted rows
    by calling ``all_with_deleted()`` (if the manager provides it).

    Parameters
    ----------
    include_deleted : bool
        Pass ``true`` to include soft-deleted records.
    """

    include_deleted = filters.BooleanFilter(
        field_name="deleted_at",
        method="filter_deleted",
        help_text="Include soft-deleted records.",
    )

    def filter_deleted(self, queryset: QuerySet, name: str, value: bool) -> QuerySet:
        """Include or exclude soft-deleted records."""
        if value:
            if hasattr(queryset, "all_with_deleted"):
                return queryset.all_with_deleted()
        else:
            if hasattr(queryset, "active"):
                return queryset.active()

        return queryset

    class Meta:
        model = None
        fields: ClassVar[list[str]] = []
