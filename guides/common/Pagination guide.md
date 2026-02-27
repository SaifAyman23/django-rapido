# Django REST Framework Pagination Guide

**A comprehensive guide to implementing production-grade pagination strategies**

---

## Table of Contents

1. [Overview](#overview)
2. [Pagination Types](#pagination-types)
3. [Page Number Pagination](#page-number-pagination)
4. [Cursor-Based Pagination](#cursor-based-pagination)
5. [Limit-Offset Pagination](#limit-offset-pagination)
6. [Custom Pagination](#custom-pagination)
7. [Performance Optimization](#performance-optimization)
8. [Common Patterns](#common-patterns)
9. [Best Practices](#best-practices)
10. [Comparison & Selection](#comparison--selection)

---

## Overview

Pagination divides large datasets into manageable chunks. DRF provides three main strategies, each with different performance and usability tradeoffs.

### Why Pagination Matters

- **Performance** — Don't load millions of records at once
- **User Experience** — Better navigation and faster load times
- **Database** — Reduced query load with limits
- **Network** — Smaller responses, less bandwidth

### Quick Start

```python
from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    pagination_class = StandardPagination
```

**Usage:**

```bash
# Default page size
GET /articles/

# Custom page size
GET /articles/?page_size=20

# Specific page
GET /articles/?page=2
```

---

## Pagination Types

### Quick Comparison

| Type | Best For | Speed | SEO | Offset Size | Use Case |
|------|----------|-------|-----|-------------|----------|
| **Page Number** | User browsing | Good | Good | Fixed | Blog posts, product listings |
| **Cursor** | Timelines, feeds | Excellent | Bad | Variable | Real-time feeds, large datasets |
| **Limit-Offset** | APIs, mobile | Good | Bad | Fixed | Mobile apps, API clients |

---

## Page Number Pagination

Traditional page-based pagination. Users navigate by page numbers (1, 2, 3, etc.).

### StandardPagination

Simple, clean page-based pagination suitable for most use cases.

```python
class StandardPagination(PageNumberPagination):
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
```

**Response Example:**

```json
{
  "pagination": {
    "count": 256,
    "page_size": 10,
    "total_pages": 26,
    "current_page": 1,
    "has_next": true,
    "has_previous": false
  },
  "links": {
    "next": "http://example.com/articles/?page=2",
    "previous": null
  },
  "results": [...]
}
```

**Usage:**

```bash
GET /articles/              # Page 1, size 10
GET /articles/?page=2       # Page 2
GET /articles/?page_size=20 # Custom page size
GET /articles/?page=3&page_size=50  # Page 3, 50 items
```

**Use Cases:**

- Blog listings
- Article archives
- Product catalogs
- Admin interfaces
- Any user-facing listing

**Advantages:**

- Easy to understand for users
- Good for search engines (`page=1`, `page=2`)
- Supports full sorting
- Users can jump to specific page
- Works well with filters

**Disadvantages:**

- Requires `COUNT(*)` on every request (slow on large tables)
- Slower with large datasets and high page numbers
- Data shifts when items inserted/deleted at beginning
- Not ideal for real-time data
- Can return inconsistent results if data changes

**Configuration:**

```python
class StandardPagination(PageNumberPagination):
    page_size = 10                          # Default items per page
    page_size_query_param = "page_size"     # Allow client to set size
    max_page_size = 100                     # Maximum allowed size
    page_query_param = "page"               # Query parameter name
    page_size_query_description = "..."     # Schema description
```

### LargePagination

For large datasets with more items per page.

```python
class LargePagination(PageNumberPagination):
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
```

**Use Cases:**

- Data exports (CSV, Excel)
- Large result sets (100k+ records)
- Admin data tables
- Bulk operations
- Analytics data

### SmallPagination

For mobile and small screens with fewer items.

```python
class SmallPagination(PageNumberPagination):
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
```

**Use Cases:**

- Mobile apps
- Small screens (smartphones)
- Touch-friendly interfaces
- Low-bandwidth connections
- Limited display space

---

## Cursor-Based Pagination

Uses a cursor (opaque pointer) instead of page numbers. Excellent for real-time data where items are constantly added/removed.

### How Cursors Work

Instead of page numbers, cursors encode position information:

```
Request 1: GET /feed/?cursor=cD0yMDI1LTAyLTI3KzEwOjMwOjQ1
Response includes "next" cursor:
  "next": "?cursor=cD0yMDI1LTAyLTI3KzA5OjU0OjMyLjEyMzQ1Ng=="

Request 2: GET /feed/?cursor=cD0yMDI1LTAyLTI3KzA5OjU0OjMyLjEyMzQ1Ng==
```

### StandardCursorPagination

Best for feeds, timelines, real-time data.

```python
class StandardCursorPagination(CursorPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    page_size_query_description = "Page size (default: 10, max: 100)"
    ordering = "-created_at"  # MUST be set
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
```

**Response Example:**

```json
{
  "pagination": {
    "page_size": 10,
    "next": "http://example.com/feed/?cursor=cD0yMDI1LTAy...",
    "previous": "http://example.com/feed/?cursor=cD0yMDI1LTA...",
    "count": 5234
  },
  "results": [...]
}
```

**Usage:**

```bash
GET /feed/                              # First page
GET /feed/?cursor=cD0yMDI1LTAy...      # Next page (use 'next' from response)
GET /feed/?cursor=cD0yMDI1LTA...       # Previous page
```

**Use Cases:**

- Social media feeds
- Real-time notifications
- Activity streams
- Chat history
- Event logs
- Large datasets (millions of records)

**Advantages:**

- **Excellent performance** — No COUNT(*) needed
- Consistent results even if data changes
- Handles insertions/deletions gracefully
- Perfect for real-time data
- Works with large datasets (100M+ records)
- Backward compatible (data added before cursor still works)

**Disadvantages:**

- Cannot jump to specific page
- No total count provided
- Cannot sort by arbitrary fields (limited to cursor field)
- Opaque cursors (harder to debug)
- Backward navigation slower than forward

**Important:** Must set `ordering` attribute

```python
class StandardCursorPagination(CursorPagination):
    ordering = "-created_at"  # Required!
    # Cursor is based on this field
    # Works best with: timestamps, IDs
    # Avoid: names, descriptions (non-unique)
```

### TimestampCursorPagination

Cursor-based pagination using timestamp ordering.

```python
class TimestampCursorPagination(CursorPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"  # Order by timestamp
    cursor_query_param = "cursor"

    def get_paginated_response(self, data: list) -> Response:
        return Response({
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })
```

**Best for:** Feeds ordered by time (most recent first)

### IdCursorPagination

Cursor-based pagination using ID ordering.

```python
class IdCursorPagination(CursorPagination):
    page_size = 10
    ordering = "-id"  # Order by ID descending
    cursor_query_param = "cursor"
```

**Best for:** Consistent ordering by primary key

---

## Limit-Offset Pagination

Specifies how many items to return (`limit`) and where to start (`offset`).

### StandardLimitOffsetPagination

```python
class StandardLimitOffsetPagination(LimitOffsetPagination):
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
```

**Response Example:**

```json
{
  "count": 256,
  "next": "http://example.com/articles/?limit=10&offset=10",
  "previous": null,
  "limit": 10,
  "offset": 0,
  "results": [...]
}
```

**Usage:**

```bash
GET /articles/                  # First 10 items
GET /articles/?limit=20         # First 20 items
GET /articles/?offset=10        # Skip 10, get next 10
GET /articles/?limit=20&offset=40  # Skip 40, get 20 items
```

**Use Cases:**

- REST APIs
- Mobile apps
- Programmatic access
- Flexible result sets
- Offset-based navigation

**Advantages:**

- Simple and intuitive (`skip N, get M`)
- Good for APIs
- Flexible result sizes
- Easy to debug
- Works well with sorting

**Disadvantages:**

- Requires `COUNT(*)` (slow on large tables)
- Slow for large offsets (`offset=1000000`)
- Data inconsistency with insertions
- Not efficient for large datasets

### OffsetPagination

Simplified version with sensible defaults.

```python
class OffsetPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100
```

---

## Custom Pagination

Specialized pagination for specific use cases.

### OptimizedPagination

Pagination with caching for better performance.

```python
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
```

**Benefits:**

- Caches page metadata (count, num_pages)
- Reduces database queries
- 5-minute TTL (configurable)
- Automatic cache invalidation

**Use Cases:**

- Frequently accessed pages
- Heavy queries with filters
- Read-heavy endpoints
- Public data

**Note:** Cache key doesn't include filters, so results are same for all filters on a page. Customize as needed.

### NoCountPagination

Pagination that skips `COUNT(*)` for massive performance boost.

```python
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
```

**Key Difference:**

- Fetches `page_size + 1` items
- Uses length to detect "has_next"
- No `COUNT(*)` query
- Doesn't return total count

**Performance Impact:**

- Original: `SELECT COUNT(*), SELECT items LIMIT 10`
- NoCount: `SELECT items LIMIT 11` (2x faster!)

**Use Cases:**

- Very large tables (millions of rows)
- Expensive COUNT queries
- When total count not needed
- High-traffic endpoints

**Limitations:**

- No total count in response
- Can't show "page 5 of 47"
- Client doesn't know total items

### DynamicPagination

Adjusts page size based on device type.

```python
class DynamicPagination(StandardPagination):
    """Pagination that adjusts page size based on device"""

    def get_page_size(self, request: Request) -> int:
        """Dynamic page size based on user agent"""
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        # Mobile devices
        if any(device in user_agent for device in ["mobile", "android", "iphone"]):
            return 5  # Small screens

        # Tablets
        if any(device in user_agent for device in ["tablet", "ipad"]):
            return 15  # Medium screens

        # Desktop
        return self.page_size  # Full size
```

**Behavior:**

- iPhone: 5 items per page
- iPad: 15 items per page
- Desktop: 10 items per page (or configured size)

**Use Cases:**

- Mobile-first apps
- Responsive design
- Multi-device support
- Auto-tuned UX

### SearchPagination

Optimized for search results with additional metadata.

```python
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
```

**Response Example:**

```json
{
  "search_metadata": {
    "total_results": 543,
    "current_page": 1,
    "total_pages": 28,
    "results_per_page": 20
  },
  "links": {
    "next": "http://example.com/search/?q=django&page=2",
    "previous": null
  },
  "results": [...]
}
```

**Use Cases:**

- Search endpoints
- Filter results
- Analytics queries
- User-facing search

### ProgressivePagination

Supports progressive/infinite loading.

```python
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
```

**Response Example:**

```json
{
  "pagination": {
    "current": 1,
    "total": 26,
    "size": 10,
    "total_count": 256,
    "has_next": true,
    "has_previous": false
  },
  "next_cursor": 2,
  "results": [...]
}
```

**Use Cases:**

- "Load more" buttons
- Infinite scroll
- Mobile apps
- Dynamic content loading

---

## Performance Optimization

### Strategy 1: Use Cursor Pagination for Large Tables

```python
# ✅ Good for millions of rows
class ArticleViewSet(viewsets.ModelViewSet):
    pagination_class = StandardCursorPagination

# ❌ Bad for millions of rows
class ArticleViewSet(viewsets.ModelViewSet):
    pagination_class = StandardPagination
```

**Impact:** 10x faster for large offsets

### Strategy 2: Use NoCountPagination When Total Not Needed

```python
# ✅ Good when you don't need total count
class CommentViewSet(viewsets.ModelViewSet):
    pagination_class = NoCountPagination

# ❌ Slower if you don't need total count
class CommentViewSet(viewsets.ModelViewSet):
    pagination_class = StandardPagination
```

**Impact:** Eliminates `COUNT(*)` query

### Strategy 3: Combine with QuerySet Optimization

```python
class ArticleViewSet(viewsets.ModelViewSet):
    pagination_class = StandardPagination

    def get_queryset(self):
        # Optimize before pagination
        return Article.objects.select_related('author').prefetch_related('tags')
```

**Impact:** Fewer database hits overall

### Strategy 4: Cache Expensive Pages

```python
class HeavyArticleViewSet(viewsets.ModelViewSet):
    pagination_class = OptimizedPagination
```

**Impact:** Repeated page requests served from cache

### Strategy 5: Use Smaller Page Sizes

```python
class StandardPagination(PageNumberPagination):
    page_size = 10      # Smaller = faster
    max_page_size = 50  # Prevent abuse
```

**Impact:** Faster queries, less memory

---

## Common Patterns

### Pattern 1: Search Results with Pagination

```python
class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    pagination_class = SearchPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering = ['-created_at']
```

**Usage:**

```bash
GET /articles/?search=django&page=1&page_size=20
```

### Pattern 2: Feed with Cursor Pagination

```python
class FeedViewSet(viewsets.ModelViewSet):
    queryset = FeedItem.objects.all()
    serializer_class = FeedItemSerializer
    pagination_class = StandardCursorPagination
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
```

**Usage:**

```bash
GET /feed/
GET /feed/?cursor=<next_cursor_from_response>
```

### Pattern 3: Large Data Export

```python
class ExportViewSet(viewsets.ViewSet):
    pagination_class = LargePagination
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        # Can handle 500 items at once
        pass
```

### Pattern 4: Mobile API

```python
class MobileAPIViewSet(viewsets.ModelViewSet):
    pagination_class = DynamicPagination
    # Automatically smaller on phones, larger on tablets
```

### Pattern 5: Infinite Scroll

```python
class TimelineViewSet(viewsets.ModelViewSet):
    pagination_class = ProgressivePagination
    # Frontend checks has_next and loads more
```

---

## Best Practices

### 1. Choose Based on Use Case

```python
# ✅ Blog with user browsing
pagination_class = StandardPagination

# ✅ Social feed with new items
pagination_class = StandardCursorPagination

# ✅ Mobile app with flexible pagination
pagination_class = DynamicPagination

# ✅ Search results
pagination_class = SearchPagination
```

### 2. Set Sensible Defaults

```python
# ✅ Good defaults
class StandardPagination(PageNumberPagination):
    page_size = 10              # Reasonable default
    max_page_size = 100         # Prevent abuse
    page_size_query_param = "page_size"  # Allow override

# ❌ Bad defaults
page_size = 1000                # Too large
max_page_size = None            # No limit
```

### 3. Optimize Queryset Before Pagination

```python
def get_queryset(self):
    # Do this BEFORE pagination
    return Article.objects.select_related('author')

# NOT after pagination in serializer
```

### 4. Cache When Possible

```python
# Cache popular pages
class OptimizedPagination(StandardPagination):
    def paginate_queryset(self, queryset, request, view=None):
        # Check cache first
        pass
```

### 5. Use Appropriate Pagination Type

| Data | Type | Reason |
|------|------|--------|
| Blog posts | Page number | Users browse by page |
| Social feed | Cursor | New items added constantly |
| API data | Limit-offset | Programmatic access |
| Large table | Cursor or NoCount | Performance |
| Search | Page number | Show results count |

### 6. Handle Edge Cases

```python
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
```

### 7. Test Pagination

```python
def test_pagination():
    response = client.get('/articles/?page=1&page_size=10')
    assert response.status_code == 200
    assert len(response.data['results']) == 10
    assert 'pagination' in response.data
    assert response.data['pagination']['total_pages'] > 0
```

### 8. Document Page Size Options

```python
class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    page_size_query_description = (
        "Page size (default: 10, max: 100). "
        "Recommended: 10-20 for web, 5-10 for mobile"
    )
    max_page_size = 100
```

---

## Comparison & Selection

### Page Number vs Cursor vs Limit-Offset

| Feature | Page Number | Cursor | Limit-Offset |
|---------|-------------|--------|--------------|
| **Easy to understand** | ✅ Yes | ❌ No | ✅ Yes |
| **Good for SEO** | ✅ Yes | ❌ No | ❌ No |
| **Performance on large tables** | ❌ Slow | ✅ Fast | ❌ Slow |
| **Handles real-time data** | ❌ No | ✅ Yes | ❌ No |
| **Can jump to page** | ✅ Yes | ❌ No | ✅ Yes |
| **Total count needed** | ✅ Yes | ❌ No | ✅ Yes |
| **Backward pagination** | ✅ Yes | ⚠️ Slow | ✅ Yes |
| **Consistent results** | ❌ No | ✅ Yes | ❌ No |

### Selection Decision Tree

```
Is this for user-facing browsing?
  └─ Yes → Use Page Number Pagination
  └─ No → Is this a feed/timeline?
    └─ Yes → Use Cursor Pagination
    └─ No → Is this an API?
      └─ Yes → Use Limit-Offset Pagination
      └─ No → Use best fit for your case
```

---

## Utility Functions

### Get Page Statistics

```python
from .pagination import get_page_stats

stats = get_page_stats(Article.objects.all(), page_size=10)
# {
#   "total_items": 256,
#   "page_size": 10,
#   "total_pages": 26,
#   "page_range": [1, 2, 3, ..., 26]
# }
```

### Get Page Data

```python
from .pagination import get_page_data

data = get_page_data(Article.objects.all(), page_number=2, page_size=10)
# {
#   "data": [...],
#   "page_number": 2,
#   "total_pages": 26,
#   "has_next": True,
#   "has_previous": True
# }
```

---

## Summary

| Class | Use When |
|-------|----------|
| **StandardPagination** | User-facing browsing, blogs, archives |
| **LargePagination** | Exporting large datasets |
| **SmallPagination** | Mobile apps, small screens |
| **StandardCursorPagination** | Feeds, timelines, real-time data |
| **TimestampCursorPagination** | Activity streams, recent-first ordering |
| **IdCursorPagination** | Consistent ID-based ordering |
| **StandardLimitOffsetPagination** | REST APIs, mobile apps |
| **OffsetPagination** | Simple API pagination |
| **OptimizedPagination** | High-traffic endpoints, caching needed |
| **NoCountPagination** | Massive tables, COUNT(*) too slow |
| **DynamicPagination** | Multi-device support |
| **SearchPagination** | Search results |
| **ProgressivePagination** | Infinite scroll, progressive loading |

---

## Next Steps

1. Choose appropriate pagination type for your use case
2. Configure page sizes
3. Optimize querysets
4. Add caching where needed
5. Test edge cases
6. Monitor performance

---

## Questions?

Refer to:
1. **Pagination Types** section for overview
2. **Common Patterns** section for real examples
3. **Comparison & Selection** for choosing right type
4. **Best Practices** for optimization tips