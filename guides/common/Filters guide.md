# Django REST Framework Filters Guide

**A comprehensive guide to implementing production-grade filtering**

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Filtering](#basic-filtering)
3. [Custom Filter Classes](#custom-filter-classes)
4. [Date Range Filtering](#date-range-filtering)
5. [Status & Boolean Filters](#status--boolean-filters)
6. [Search Filters](#search-filters)
7. [Range Filters](#range-filters)
8. [Composite Filters](#composite-filters)
9. [Performance Optimization](#performance-optimization)
10. [Best Practices](#best-practices)

---

## Overview

Django-filters provides a way to filter querysets based on user input through URL parameters. It's essential for building powerful, user-friendly APIs.

### Why Use Filters?

- **User Control** — Let users query exactly what they need
- **Performance** — Return only necessary data
- **API Quality** — Professional, flexible endpoints
- **DRY** — Reusable filter classes

### Quick Start

```python
from django_filters import rest_framework as filters
from rest_framework import viewsets

class ArticleFilter(filters.FilterSet):
    class Meta:
        model = Article
        fields = ['status', 'author']

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filterset_class = ArticleFilter
```

**Usage:**

```bash
GET /articles/?status=published
GET /articles/?author=5
GET /articles/?status=published&author=5
```

---

## Basic Filtering

### Simple Field Filters

```python
class ArticleFilter(filters.FilterSet):
    """Basic field filtering"""
    
    class Meta:
        model = Article
        fields = {
            'status': ['exact'],           # Exact match
            'title': ['icontains'],        # Case-insensitive contains
            'created_at': ['gte', 'lte'],  # Greater than, less than
            'author': ['exact'],           # Foreign key
        }
```

**Usage:**

```bash
GET /articles/?status=published
GET /articles/?title__icontains=django
GET /articles/?created_at__gte=2025-01-01
GET /articles/?author=5
```

### Lookup Expressions

| Lookup | Example | Description |
|--------|---------|-------------|
| `exact` | `?status=published` | Exact match |
| `iexact` | `?title__iexact=Django` | Case-insensitive exact |
| `contains` | `?title__contains=Django` | Contains (case-sensitive) |
| `icontains` | `?title__icontains=django` | Contains (case-insensitive) |
| `gt`, `gte` | `?price__gt=10` | Greater than (or equal) |
| `lt`, `lte` | `?price__lt=100` | Less than (or equal) |
| `startswith` | `?title__startswith=How` | Starts with |
| `endswith` | `?title__endswith=Guide` | Ends with |
| `in` | `?id__in=1,2,3` | In list |
| `isnull` | `?deleted_at__isnull=true` | Is null |

### Multiple Field Filters

```python
class ArticleFilter(filters.FilterSet):
    """Filter multiple fields"""
    
    class Meta:
        model = Article
        fields = {
            'status': ['exact', 'in'],
            'title': ['icontains', 'istartswith'],
            'author__username': ['icontains'],
            'created_at': ['gte', 'lte', 'exact'],
            'tags__name': ['iexact', 'in'],
        }
```

**Usage:**

```bash
# Multiple statuses
GET /articles/?status__in=published,draft

# Title contains
GET /articles/?title__icontains=django

# Author search
GET /articles/?author__username__icontains=john

# Date range
GET /articles/?created_at__gte=2025-01-01&created_at__lte=2025-02-28

# Tags
GET /articles/?tags__name__in=python,django
```

---

## Custom Filter Classes

### CharInFilter (Comma-separated Values)

```python
from django_filters import rest_framework as filters

class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """Filter for comma-separated string values"""
    pass

class ArticleFilter(filters.FilterSet):
    status = CharInFilter(
        field_name='status',
        lookup_expr='in',
        help_text="Comma-separated statuses: published,draft"
    )
    
    class Meta:
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/?status=published,draft,archived
```

### UUIDInFilter

```python
class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    """Filter for multiple UUIDs"""
    pass

class ArticleFilter(filters.FilterSet):
    ids = UUIDInFilter(
        field_name='id',
        lookup_expr='in',
        help_text="Comma-separated UUIDs"
    )
    
    class Meta:
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/?ids=abc-123,def-456,ghi-789
```

### Custom Method Filter

```python
class ArticleFilter(filters.FilterSet):
    search = filters.CharFilter(
        method='search_filter',
        help_text="Search across title and content"
    )
    
    def search_filter(self, queryset, name, value):
        """Custom search logic"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(title__icontains=value) | 
            Q(content__icontains=value)
        )
    
    class Meta:
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/?search=django
# Searches both title AND content
```

---

## Date Range Filtering

### DateRangeFilter

```python
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
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/?start_date=2025-01-01
GET /articles/?end_date=2025-12-31
GET /articles/?start_date=2025-01-01&end_date=2025-12-31
```

### Recent Filter (Last N Days)

```python
from datetime import timedelta
from django.utils import timezone

class RecentFilter(filters.FilterSet):
    """Filter recent records"""
    
    recent_days = filters.NumberFilter(
        method="filter_recent",
        help_text="Filter records from last N days",
    )
    
    def filter_recent(self, queryset, name, value):
        """Filter records from last N days"""
        if not value:
            return queryset
        
        cutoff_date = timezone.now() - timedelta(days=int(value))
        return queryset.filter(created_at__gte=cutoff_date)
    
    class Meta:
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/?recent_days=7    # Last 7 days
GET /articles/?recent_days=30   # Last 30 days
```

### Date Shortcuts

```python
class ArticleFilter(filters.FilterSet):
    """Date shortcuts: today, this_week, this_month"""
    
    date_filter = filters.CharFilter(
        method='filter_by_date_range',
        help_text="Options: today, this_week, this_month, this_year"
    )
    
    def filter_by_date_range(self, queryset, name, value):
        """Filter by predefined date ranges"""
        now = timezone.now()
        
        if value == 'today':
            start = now.replace(hour=0, minute=0, second=0)
            return queryset.filter(created_at__gte=start)
        
        elif value == 'this_week':
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0)
            return queryset.filter(created_at__gte=start)
        
        elif value == 'this_month':
            start = now.replace(day=1, hour=0, minute=0, second=0)
            return queryset.filter(created_at__gte=start)
        
        elif value == 'this_year':
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0)
            return queryset.filter(created_at__gte=start)
        
        return queryset
    
    class Meta:
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/?date_filter=today
GET /articles/?date_filter=this_week
GET /articles/?date_filter=this_month
```

---

## Status & Boolean Filters

### StatusFilter

```python
class StatusFilter(filters.FilterSet):
    """Filter by status"""
    
    status = filters.CharFilter(
        field_name="status",
        method="filter_status",
        help_text="Filter by single or multiple statuses (comma-separated)",
    )
    
    def filter_status(self, queryset, name, value):
        """Filter by single or multiple statuses"""
        statuses = value.split(",") if value else []
        
        if statuses:
            return queryset.filter(status__in=statuses)
        
        return queryset
    
    class Meta:
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/?status=published
GET /articles/?status=published,draft
```

### VerifiedFilter

```python
class VerifiedFilter(filters.FilterSet):
    """Filter by verification status"""
    
    verified = filters.BooleanFilter(
        field_name="is_verified",
        help_text="Filter verified/unverified records",
    )
    
    class Meta:
        model = User
        fields = []
```

**Usage:**

```bash
GET /users/?verified=true
GET /users/?verified=false
```

### ActiveFilter

```python
class ActiveFilter(filters.FilterSet):
    """Filter by active status"""
    
    active = filters.BooleanFilter(
        field_name="is_active",
        help_text="Filter active/inactive records",
    )
    
    class Meta:
        model = User
        fields = []
```

**Usage:**

```bash
GET /users/?active=true
GET /users/?active=false
```

### PublishedFilter

```python
class PublishedFilter(filters.FilterSet):
    """Filter published vs draft"""
    
    published = filters.BooleanFilter(
        field_name="status",
        method="filter_published",
        help_text="Filter published/draft records",
    )
    
    def filter_published(self, queryset, name, value):
        """Filter by published status"""
        if value is None:
            return queryset
        
        status = "published" if value else "draft"
        return queryset.filter(status=status)
    
    class Meta:
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/?published=true   # Only published
GET /articles/?published=false  # Only drafts
```

---

## Search Filters

### SearchableFilterSet

```python
from django.db.models import Q

class SearchableFilterSet(filters.FilterSet):
    """Base filterset with search capabilities"""
    
    search = filters.CharFilter(
        method="search_filter",
        help_text="Search across multiple fields",
    )
    
    search_fields = []  # Override in subclass
    
    def search_filter(self, queryset, name, value):
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
```

**Usage in Subclass:**

```python
class ArticleFilter(SearchableFilterSet):
    """Article filtering with search"""
    
    search_fields = ['title', 'content', 'author__username']
    
    class Meta:
        model = Article
        fields = ['status']
```

**API Usage:**

```bash
GET /articles/?search=django
# Searches title, content, and author username
```

### Advanced Search with Weights

```python
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

class AdvancedSearchFilter(filters.FilterSet):
    """Search with relevance ranking (PostgreSQL only)"""
    
    search = filters.CharFilter(
        method='search_filter',
        help_text="Full-text search"
    )
    
    def search_filter(self, queryset, name, value):
        """Full-text search with ranking"""
        if not value:
            return queryset
        
        # Create search vector
        vector = SearchVector('title', weight='A') + SearchVector('content', weight='B')
        query = SearchQuery(value)
        
        # Filter and rank
        return queryset.annotate(
            rank=SearchRank(vector, query)
        ).filter(
            rank__gte=0.1
        ).order_by('-rank')
    
    class Meta:
        model = Article
        fields = []
```

---

## Range Filters

### RangeFilter (Numeric)

```python
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
        model = Product
        fields = []
```

**Usage:**

```bash
GET /products/?min_value=10
GET /products/?max_value=100
GET /products/?min_value=10&max_value=100
```

### PriceRangeFilter

```python
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
        model = Product
        fields = []
```

**Usage:**

```bash
GET /products/?min_price=10.00
GET /products/?max_price=99.99
GET /products/?min_price=10&max_price=99.99
```

### RatingFilter

```python
class RatingFilter(filters.FilterSet):
    """Filter by rating"""
    
    min_rating = filters.NumberFilter(
        field_name="rating",
        lookup_expr="gte",
        help_text="Minimum rating (1-5)",
    )
    rating_count_min = filters.NumberFilter(
        field_name="rating_count",
        lookup_expr="gte",
        help_text="Minimum number of ratings",
    )
    
    class Meta:
        model = Product
        fields = []
```

**Usage:**

```bash
GET /products/?min_rating=4.0
GET /products/?rating_count_min=10
GET /products/?min_rating=4.0&rating_count_min=10
```

---

## Composite Filters

### StandardUserFilter

```python
class StandardUserFilter(SearchableFilterSet):
    """Standard user filtering with search"""
    
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
        model = User
        fields = ["search", "active", "verified", "staff"]
```

**Usage:**

```bash
GET /users/?search=john
GET /users/?active=true
GET /users/?verified=true&staff=false
GET /users/?search=john&active=true
```

### StandardContentFilter

```python
class StandardContentFilter(SearchableFilterSet):
    """Standard content filtering"""
    
    search_fields = ["title", "description", "slug"]
    
    status = filters.CharFilter(
        field_name="status",
        help_text="Filter by status",
    )
    author = filters.CharFilter(
        field_name="user__username",
        help_text="Filter by author username",
    )
    published_start = filters.DateTimeFilter(
        field_name="published_at",
        lookup_expr="gte",
        help_text="Published after this date",
    )
    published_end = filters.DateTimeFilter(
        field_name="published_at",
        lookup_expr="lte",
        help_text="Published before this date",
    )
    
    class Meta:
        model = Article
        fields = ["search", "status", "author"]
```

**Usage:**

```bash
GET /articles/?search=django
GET /articles/?status=published
GET /articles/?author=john
GET /articles/?published_start=2025-01-01
GET /articles/?search=django&status=published&author=john
```

### AuthorFilter

```python
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
        model = Article
        fields = []
```

### TagFilter

```python
class TagFilter(filters.FilterSet):
    """Filter by tags"""
    
    tags = filters.CharFilter(
        field_name="tags__name",
        method="filter_tags",
        help_text="Filter by tags (comma-separated)",
    )
    
    def filter_tags(self, queryset, name, value):
        """Filter by multiple tags"""
        tags = value.split(",") if value else []
        
        if tags:
            return queryset.filter(tags__name__in=tags).distinct()
        
        return queryset
    
    class Meta:
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/?tags=python
GET /articles/?tags=python,django,web
```

### DeletedFilter (Soft Deletes)

```python
class DeletedFilter(filters.FilterSet):
    """Filter soft-deleted records"""
    
    include_deleted = filters.BooleanFilter(
        field_name="deleted_at",
        method="filter_deleted",
        help_text="Include deleted records",
    )
    
    def filter_deleted(self, queryset, name, value):
        """Include or exclude deleted records"""
        if value:
            # Include deleted (use manager method if available)
            if hasattr(queryset, "all_with_deleted"):
                return queryset.all_with_deleted()
        else:
            # Only active
            if hasattr(queryset, "active"):
                return queryset.active()
        
        return queryset
    
    class Meta:
        model = Article
        fields = []
```

**Usage:**

```bash
GET /articles/                       # Only active
GET /articles/?include_deleted=true  # Include deleted
```

---

## Performance Optimization

### 1. Use select_related and prefetch_related

```python
class OptimizedArticleViewSet(viewsets.ModelViewSet):
    """Optimized queryset for filtering"""
    
    filterset_class = ArticleFilter
    
    def get_queryset(self):
        """Optimize queryset before filtering"""
        return Article.objects.select_related(
            'author',
            'category'
        ).prefetch_related(
            'tags',
            'comments'
        )
```

### 2. Add Database Indexes

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, db_index=True)  # Indexed
    author = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),  # Composite index
            models.Index(fields=['-created_at']),           # Descending
        ]
```

### 3. Limit Search Fields

❌ **Bad:**

```python
class ArticleFilter(SearchableFilterSet):
    search_fields = ['title', 'content', 'author__username', 'author__email', 
                     'category__name', 'tags__name', 'comments__content']
```

✅ **Good:**

```python
class ArticleFilter(SearchableFilterSet):
    search_fields = ['title', 'author__username']  # Only essential fields
```

### 4. Use count() Efficiently

```python
# In views
def list(self, request):
    queryset = self.filter_queryset(self.get_queryset())
    
    # Cache count if needed multiple times
    count = queryset.count()
    
    # Use pagination to avoid loading all records
    page = self.paginate_queryset(queryset)
    serializer = self.get_serializer(page, many=True)
    
    return self.get_paginated_response(serializer.data)
```

### 5. Avoid N+1 Queries

```python
class ArticleFilter(filters.FilterSet):
    """Filter with optimized queries"""
    
    author = filters.CharFilter(field_name='author__username')
    
    class Meta:
        model = Article
        fields = ['author', 'status']

# In ViewSet
class ArticleViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # Prevent N+1 when filtering by author
        return Article.objects.select_related('author')
```

---

## Best Practices

### 1. Provide Help Text

✅ **Good:**

```python
class ArticleFilter(filters.FilterSet):
    search = filters.CharFilter(
        method='search_filter',
        help_text="Search across title, content, and author. Example: ?search=django"
    )
    
    status = filters.CharFilter(
        help_text="Filter by status. Options: draft, published, archived"
    )
```

### 2. Validate Filter Values

```python
class ArticleFilter(filters.FilterSet):
    status = filters.CharFilter(
        method='filter_status',
        help_text="Filter by status"
    )
    
    def filter_status(self, queryset, name, value):
        """Validate and filter by status"""
        valid_statuses = ['draft', 'published', 'archived']
        
        if value not in valid_statuses:
            # Return empty queryset or raise error
            return queryset.none()
        
        return queryset.filter(status=value)
```

### 3. Use Distinct When Needed

```python
class ArticleFilter(filters.FilterSet):
    tags = filters.CharFilter(
        method='filter_tags',
    )
    
    def filter_tags(self, queryset, name, value):
        """Filter by tags with distinct()"""
        tags = value.split(',')
        # Use distinct() to avoid duplicates
        return queryset.filter(tags__name__in=tags).distinct()
```

### 4. Document Filter Combinations

```python
class ArticleFilter(filters.FilterSet):
    """
    Article filtering
    
    Examples:
        GET /articles/?status=published&search=django
        GET /articles/?author=john&created_after=2025-01-01
        GET /articles/?tags=python,django&min_rating=4.0
    """
    pass
```

### 5. Provide Filter Summary

```python
def get_filter_summary(queryset, filters_applied: dict) -> dict:
    """Get summary of applied filters"""
    return {
        "total_records": queryset.count(),
        "filters_applied": filters_applied,
        "query": str(queryset.query) if queryset else "",
    }

# Usage in view
filtered_qs = self.filter_queryset(self.get_queryset())
summary = get_filter_summary(filtered_qs, request.query_params)
```

### 6. Handle Empty Results Gracefully

```python
class ArticleFilter(filters.FilterSet):
    search = filters.CharFilter(
        method='search_filter',
    )
    
    def search_filter(self, queryset, name, value):
        """Search with fallback"""
        if not value:
            return queryset
        
        results = queryset.filter(
            Q(title__icontains=value) | 
            Q(content__icontains=value)
        )
        
        # Log if no results
        if not results.exists():
            logger.info(f"No results for search: {value}")
        
        return results
```

### 7. Test Filters Thoroughly

```python
class ArticleFilterTest(TestCase):
    def test_status_filter(self):
        """Test status filtering"""
        # Create test data
        Article.objects.create(title="Test 1", status="published")
        Article.objects.create(title="Test 2", status="draft")
        
        # Apply filter
        filterset = ArticleFilter(
            data={'status': 'published'},
            queryset=Article.objects.all()
        )
        
        # Verify results
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first().status, 'published')
    
    def test_date_range_filter(self):
        """Test date range filtering"""
        # Create test data with dates
        past = timezone.now() - timedelta(days=30)
        recent = timezone.now() - timedelta(days=5)
        
        Article.objects.create(title="Old", created_at=past)
        Article.objects.create(title="New", created_at=recent)
        
        # Filter last 7 days
        filterset = ArticleFilter(
            data={'recent_days': 7},
            queryset=Article.objects.all()
        )
        
        self.assertEqual(filterset.qs.count(), 1)
```

---

## Filter Utilities

### Apply Filters Programmatically

```python
def apply_filters(queryset, filters_dict: dict) -> QuerySet:
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

# Usage
filters = {
    'status': 'published',
    'created_at__gte': '2025-01-01',
    'author__username': 'john'
}
filtered = apply_filters(Article.objects.all(), filters)
```

### Get Filter Parameters from Request

```python
def get_filter_params(request) -> dict:
    """Extract filter parameters from request"""
    params = {}
    
    for key, value in request.query_params.items():
        # Skip pagination params
        if key in ['page', 'page_size', 'limit', 'offset']:
            continue
        
        # Skip empty values
        if not value:
            continue
        
        params[key] = value
    
    return params

# Usage in view
def list(self, request):
    filter_params = get_filter_params(request)
    logger.info(f"Filters applied: {filter_params}")
    return super().list(request)
```

---

## Common Patterns

### Pattern 1: Blog Posts

```python
class BlogPostFilter(SearchableFilterSet):
    """Blog post filtering"""
    
    search_fields = ['title', 'content', 'author__username']
    
    status = filters.CharFilter()
    author = filters.CharFilter(field_name='author__username')
    category = filters.CharFilter(field_name='category__slug')
    tags = filters.CharFilter(method='filter_tags')
    
    published_after = filters.DateTimeFilter(
        field_name='published_at',
        lookup_expr='gte'
    )
    published_before = filters.DateTimeFilter(
        field_name='published_at',
        lookup_expr='lte'
    )
    
    def filter_tags(self, queryset, name, value):
        tags = value.split(',')
        return queryset.filter(tags__slug__in=tags).distinct()
    
    class Meta:
        model = BlogPost
        fields = ['search', 'status', 'author', 'category']
```

### Pattern 2: E-commerce Products

```python
class ProductFilter(SearchableFilterSet):
    """Product filtering"""
    
    search_fields = ['name', 'description', 'sku']
    
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    
    category = filters.CharFilter(field_name='category__slug')
    brand = filters.CharFilter(field_name='brand__slug')
    
    in_stock = filters.BooleanFilter(
        field_name='stock_quantity',
        method='filter_in_stock'
    )
    
    min_rating = filters.NumberFilter(field_name='rating', lookup_expr='gte')
    
    on_sale = filters.BooleanFilter(
        field_name='sale_price',
        method='filter_on_sale'
    )
    
    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock_quantity__gt=0)
        return queryset.filter(stock_quantity=0)
    
    def filter_on_sale(self, queryset, name, value):
        if value:
            return queryset.filter(sale_price__isnull=False)
        return queryset.filter(sale_price__isnull=True)
    
    class Meta:
        model = Product
        fields = ['search', 'category', 'brand']
```

### Pattern 3: User Management

```python
class UserFilter(SearchableFilterSet):
    """User filtering"""
    
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    active = filters.BooleanFilter(field_name='is_active')
    verified = filters.BooleanFilter(field_name='is_verified')
    staff = filters.BooleanFilter(field_name='is_staff')
    
    joined_after = filters.DateTimeFilter(
        field_name='date_joined',
        lookup_expr='gte'
    )
    joined_before = filters.DateTimeFilter(
        field_name='date_joined',
        lookup_expr='lte'
    )
    
    role = filters.CharFilter(field_name='role')
    
    class Meta:
        model = User
        fields = ['search', 'active', 'verified', 'staff', 'role']
```

---

## Summary

| Filter Type | Use Case | Example |
|-------------|----------|---------|
| **CharInFilter** | Multiple string values | `?status=draft,published` |
| **DateRangeFilter** | Date ranges | `?start_date=2025-01-01&end_date=2025-12-31` |
| **RecentFilter** | Last N days | `?recent_days=7` |
| **StatusFilter** | Entity status | `?status=published` |
| **SearchableFilterSet** | Multi-field search | `?search=django` |
| **PriceRangeFilter** | Price filtering | `?min_price=10&max_price=100` |
| **RatingFilter** | Rating filtering | `?min_rating=4.0` |
| **TagFilter** | Tag filtering | `?tags=python,django` |
| **AuthorFilter** | Author filtering | `?author=john` |
| **DeletedFilter** | Soft delete filtering | `?include_deleted=true` |

---

## Next Steps

1. Identify filterable fields in your models
2. Create appropriate filter classes
3. Add indexes for filtered fields
4. Optimize queries with select_related/prefetch_related
5. Write tests for filters
6. Document filter parameters
7. Monitor filter performance

---

**Key Takeaways:**

- Use django-filter for powerful filtering
- Provide multiple filter options
- Add help text for documentation
- Optimize with database indexes
- Use distinct() when joining tables
- Test filters thoroughly
- Monitor query performance
- Validate filter inputs