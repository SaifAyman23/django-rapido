"""
Ultimate reusable Django REST Framework pagination
Provides production-grade pagination with:
- Multiple pagination strategies
- Performance optimization
- Cache integration
- Custom metadata
"""

from typing import Dict, Any, Optional

from rest_framework.pagination import PageNumberPagination, CursorPagination, LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.request import Request
from django.core.paginator import Paginator, EmptyPage
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


# ===========================
# Page Number Pagination
# ===========================

class StandardPagination(PageNumberPagination):
    """Standard page-based pagination"""

    page_size = 10
    page_size_query_param = "page_size"
    page_size_query_description = "Page size (default: 10, max: 100)"
    max_page_size = 100
    page_query_param = "page"
    page_query_description = "Page number"

    def get_paginated_response(self, data: list) -> Response:
        """Enhanced response with metadata"""
        return Response({
            "pagination": {
                "count": self.page.paginator.count,
                "page_size": self.page_size,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "has_next": self.page.has_next(),
                "has_previous": self.page.has_previous(),
            },
            "links": {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            },
            "results": data,
        })


class LargePagination(PageNumberPagination):
    """Pagination for large datasets"""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500
    page_query_param = "page"

    def get_paginated_response(self, data: list) -> Response:
        return Response({
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "page_size": self.page_size,
            "total_pages": self.page.paginator.num_pages,
            "results": data,
        })


class SmallPagination(PageNumberPagination):
    """Pagination for small datasets / mobile"""

    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 20

    def get_paginated_response(self, data: list) -> Response:
        return Response({
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


# ===========================
# Cursor-Based Pagination
# ===========================

class StandardCursorPagination(CursorPagination):
    """Cursor-based pagination for better performance"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    page_size_query_description = "Page size (default: 10, max: 100)"
    ordering = "-created_at"
    cursor_query_param = "cursor"
    cursor_query_description = "Cursor for pagination"

    def get_paginated_response(self, data: list) -> Response:
        return Response({
            "pagination": {
                "page_size": self.page_size,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "count": self.count,
            },
            "results": data,
        })


class TimestampCursorPagination(CursorPagination):
    """Cursor-based pagination using timestamp"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"
    cursor_query_param = "cursor"

    def get_paginated_response(self, data: list) -> Response:
        return Response({
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


class IdCursorPagination(CursorPagination):
    """Cursor-based pagination using ID"""

    page_size = 10
    ordering = "-id"
    cursor_query_param = "cursor"


# ===========================
# Limit-Offset Pagination
# ===========================

class StandardLimitOffsetPagination(LimitOffsetPagination):
    """Limit-offset pagination"""

    default_limit = 10
    limit_query_param = "limit"
    limit_query_description = "Limit for pagination"
    offset_query_param = "offset"
    offset_query_description = "Offset for pagination"
    max_limit = 100

    def get_paginated_response(self, data: list) -> Response:
        return Response({
            "count": self.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "limit": self.limit,
            "offset": self.offset,
            "results": data,
        })


class OffsetPagination(LimitOffsetPagination):
    """Simple offset pagination"""

    default_limit = 20
    max_limit = 100


# ===========================
# Custom Pagination
# ===========================

class OptimizedPagination(StandardPagination):
    """Pagination with query optimization"""

    def paginate_queryset(self, queryset, request, view=None):
        """Add caching for page info"""
        # Check cache first
        cache_key = self._get_cache_key(request)
        cached_result = cache.get(cache_key)

        if cached_result:
            self.page = cached_result
            return list(self.page)

        # Get paginated results
        result = super().paginate_queryset(queryset, request, view)

        # Cache the page info
        if self.page:
            cache.set(cache_key, self.page, timeout=300)  # 5 minutes

        return result

    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key"""
        page = request.query_params.get(self.page_query_param, 1)
        page_size = request.query_params.get(self.page_size_query_param, self.page_size)
        path = request.path
        return f"pagination:{path}:{page}:{page_size}"


class NoCountPagination(PageNumberPagination):
    """Pagination that skips count() for performance"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """Paginate without counting total results"""
        # Request one extra item to determine if there's a next page
        self.limit = self.get_page_size(request) + 1
        self.offset = self.get_offset(request)

        self.request = request
        self.queryset_items = queryset[self.offset : self.offset + self.limit]

        # Check if there's a next page
        self.has_next = len(self.queryset_items) > self.get_page_size(request)
        self.queryset_items = self.queryset_items[: self.get_page_size(request)]

        return list(self.queryset_items)

    def get_paginated_response(self, data: list) -> Response:
        return Response({
            "next": self.get_next_link() if self.has_next else None,
            "previous": self.get_previous_link(),
            "results": data,
        })

    def get_next_link(self) -> Optional[str]:
        """Get next link if there's a next page"""
        if not self.has_next:
            return None

        url = self.request.build_absolute_uri()
        offset = self.offset + self.get_page_size(self.request)

        return f"{url.split('?')[0]}?offset={offset}&limit={self.get_page_size(self.request)}"

    def get_previous_link(self) -> Optional[str]:
        """Get previous link"""
        if self.offset <= 0:
            return None

        url = self.request.build_absolute_uri()
        offset = max(self.offset - self.get_page_size(self.request), 0)

        if offset <= 0:
            return f"{url.split('?')[0]}?limit={self.get_page_size(self.request)}"

        return f"{url.split('?')[0]}?offset={offset}&limit={self.get_page_size(self.request)}"

    def get_page_size(self, request: Request) -> int:
        """Get page size from request"""
        if self.page_size_query_param:
            try:
                return int(request.query_params.get(self.page_size_query_param, self.page_size))
            except (ValueError, TypeError):
                pass
        return self.page_size


class DynamicPagination(StandardPagination):
    """Pagination that adjusts page size based on device"""

    def get_page_size(self, request: Request) -> int:
        """Dynamic page size based on user agent"""
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        # Mobile devices
        if any(device in user_agent for device in ["mobile", "android", "iphone"]):
            return 5

        # Tablets
        if any(device in user_agent for device in ["tablet", "ipad"]):
            return 15

        # Desktop
        return self.page_size


class SearchPagination(StandardPagination):
    """Pagination optimized for search results"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data: list) -> Response:
        return Response({
            "search_metadata": {
                "total_results": self.page.paginator.count,
                "current_page": self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "results_per_page": self.page_size,
            },
            "links": {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            },
            "results": data,
        })


class ProgressivePagination(StandardPagination):
    """Pagination with progressive loading support"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data: list) -> Response:
        return Response({
            "pagination": {
                "current": self.page.number,
                "total": self.page.paginator.num_pages,
                "size": self.page_size,
                "total_count": self.page.paginator.count,
                "has_next": self.page.has_next(),
                "has_previous": self.page.has_previous(),
            },
            "next_cursor": self._get_next_cursor(),
            "results": data,
        })

    def _get_next_cursor(self) -> Optional[int]:
        """Get cursor for next page"""
        if self.page.has_next():
            return self.page.next_page_number()
        return None


# ===========================
# Utility Functions
# ===========================

def get_page_stats(queryset, page_size: int = 10) -> Dict[str, Any]:
    """Get pagination statistics"""
    paginator = Paginator(queryset, page_size)

    return {
        "total_items": paginator.count,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "page_range": list(paginator.page_range),
    }


def get_page_data(queryset, page_number: int = 1, page_size: int = 10):
    """Get data for a specific page"""
    try:
        paginator = Paginator(queryset, page_size)
        page = paginator.page(page_number)
        return {
            "data": list(page),
            "page_number": page.number,
            "total_pages": paginator.num_pages,
            "has_next": page.has_next(),
            "has_previous": page.has_previous(),
        }
    except EmptyPage:
        logger.warning(f"Requested page {page_number} is empty")
        return {
            "data": [],
            "page_number": page_number,
            "total_pages": 0,
            "has_next": False,
            "has_previous": False,
        }