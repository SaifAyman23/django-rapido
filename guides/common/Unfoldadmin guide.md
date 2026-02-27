# Django Unfold Admin Integration Guide

**A comprehensive guide to using Unfold Admin base classes for modern, clean Django admin interfaces**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Base Classes](#base-classes)
4. [Display Methods](#display-methods)
5. [Actions](#actions)
6. [Filtering & Searching](#filtering--searching)
7. [Common Patterns](#common-patterns)
8. [Advanced Features](#advanced-features)
9. [Best Practices](#best-practices)
10. [Examples](#examples)

---

## Overview

Unfold Admin provides a modern, clean alternative to Django's default admin interface. It includes:

- **Better UI/UX** — Modern, responsive design
- **Advanced filtering** — Range filters, checkbox filters, text filters
- **Rich display methods** — Colored badges, formatted output
- **Easier customization** — Clean base classes with sensible defaults
- **Less boilerplate** — Pre-configured classes for common patterns

### Why Use It?

- **Modern look & feel** without custom styling
- **Consistency** across all your admin interfaces
- **Better performance** with query optimization helpers
- **User-friendly** filtering and searching
- **Mobile-responsive** by default

### Quick Start

```python
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display, action

@admin.register(Article)
class ArticleAdmin(UnfoldModelAdmin):
    list_display = ["title", "status_badge", "created_at"]
    
    @display(description="Status")
    def status_badge(self, obj):
        color = "green" if obj.is_published else "red"
        return self.badge(obj.get_status_display(), color)
```

---

## Architecture

### The Hierarchy

```
UnfoldModelAdmin (from unfold)
    ↓
BaseAdmin (our base class)
    ↓
Your Admin Classes
    ├── ReadOnlyAdmin
    ├── SoftDeleteAdmin
    ├── BaseUserAdmin
    └── BaseGroupAdmin
```

### Why This Structure?

1. **UnfoldModelAdmin** provides Unfold's modern UI
2. **BaseAdmin** adds sensible defaults and helpers
3. **Specialized classes** handle specific patterns (soft deletes, read-only, users)

### Key Files

| File | Purpose |
|------|---------|
| `unfold_admin_bases.py` | Base classes with common functionality |
| `admin.py` | Your specific admin classes (CustomUserAdmin, etc.) |

---

## Base Classes

### BaseAdmin

The foundation for all admin classes. Includes sensible defaults and helpers.

```python
from unfold_admin_bases import BaseAdmin

@admin.register(Article)
class ArticleAdmin(BaseAdmin):
    list_display = ["title", "author", "created_at"]
```

**Defaults:**

| Setting | Value | Purpose |
|---------|-------|---------|
| `list_per_page` | 25 | Items per page |
| `list_fullwidth` | True | Use full width |
| `list_display` | `["__str__", "created_at"]` | Default columns |
| `readonly_fields` | `["created_at", "updated_at"]` | Standard timestamps |
| `date_hierarchy` | "created_at" | Quick navigation |
| `ordering` | `["-created_at"]` | Newest first |
| `actions_selection_counter` | True | Show count of selected |

**Inherited Methods:**

```python
def badge(self, text: str, color: str = "gray") -> str:
    """
    Create colored badges for status display.
    
    Colors: green, red, blue, yellow, purple, gray
    
    Usage:
        return self.badge("Active", "green")
    
    Output: [Active] (colored box)
    """
```

### ReadOnlyAdmin

For logs, audit trails, and immutable records. No editing allowed.

```python
from unfold_admin_bases import ReadOnlyAdmin

@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdmin):
    list_display = ["timestamp", "action", "user", "object_display"]
```

**Permissions:**

| Method | Allows | Notes |
|--------|--------|-------|
| `add` | False | Cannot create |
| `change` | False | Cannot edit |
| `delete` | Superuser only | Superusers can delete for cleanup |

**Use Cases:**

- Audit logs
- Change logs
- Event trails
- Activity records
- Immutable snapshots

### SoftDeleteAdmin

For models with soft deletes (`is_deleted` field). Shows deletion status and restore functionality.

```python
from unfold_admin_bases import SoftDeleteAdmin

@admin.register(Article)
class ArticleAdmin(SoftDeleteAdmin):
    list_display = ["title", "is_deleted_badge", "created_at"]
```

**Built-in Features:**

- Status badge showing active/deleted
- Filter by deletion status
- Bulk restore action
- Automatic queryset filtering for non-superusers

**Requirements:**

Your model must have:

```python
class Article(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Optional: custom manager
    def active(self):
        return self.filter(is_deleted=False)
```

**Display Method:**

```python
@display(description="Status")
def is_deleted_badge(self, obj) -> str:
    """Colored badge showing deletion status"""
    if obj.is_deleted:
        return self.badge("Deleted", "red")
    return self.badge("Active", "green")
```

### BaseUserAdmin

Enhanced user admin with verification, 2FA support, and query optimization.

```python
from unfold_admin_bases import BaseUserAdmin
from myapp.models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ["email", "username", "is_active", "is_staff"]
```

**Defaults:**

- Email and username columns
- Is active/staff/superuser filters
- Search by username, email, name
- Groups and permissions management
- Query optimization (prefetch groups/permissions)
- Ordered by date joined

**Override for Custom Fields:**

```python
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = [
        "email",
        "username",
        "verified_badge",  # Custom field
        "is_active",
    ]
    
    @display(description="Verified")
    def verified_badge(self, obj):
        if obj.is_verified:
            return self.badge("✓ Verified", "green")
        return self.badge("Unverified", "red")
```

### BaseGroupAdmin

Enhanced group admin with permission counting.

```python
from unfold_admin_bases import BaseGroupAdmin
from django.contrib.auth.models import Group

admin.site.unregister(Group)

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    pass  # Already configured
```

**Built-in:**

- Group name column
- Permission count
- Search by group name
- Clean, minimal display

---

## Display Methods

Display methods format data for the list and change views. Unfold's `@display` decorator provides better control than the old `short_description` approach.

### Basic Display Method

```python
from unfold.decorators import display

@display(description="Title")
def title_display(self, obj) -> str:
    return obj.title.upper()
```

### Colored Badges

Use the inherited `badge()` method:

```python
@display(description="Status", ordering="status")
def status_badge(self, obj) -> str:
    """Show colored badge based on status"""
    colors = {
        "active": "green",
        "pending": "yellow",
        "inactive": "red",
    }
    color = colors.get(obj.status, "gray")
    return self.badge(obj.get_status_display(), color)
```

**Available Colors:**

```python
colors = {
    "green": ("#dcfce7", "#16a34a"),      # Light green
    "red": ("#fee2e2", "#dc2626"),        # Light red
    "blue": ("#bfdbfe", "#2563eb"),       # Light blue
    "yellow": ("#fef3c7", "#d97706"),     # Light yellow
    "purple": ("#f3e8ff", "#9333ea"),     # Light purple
    "gray": ("#f3f4f6", "#6b7280"),       # Light gray
}
```

### Rich HTML Output

Use `format_html()` for formatted output:

```python
from django.utils.html import format_html

@display(description="Email")
def email_display(self, obj) -> str:
    """Show email with link"""
    return format_html(
        '<a href="mailto:{}">{}</a>',
        obj.email,
        obj.email
    )

@display(description="JSON Data")
def data_display(self, obj) -> str:
    """Show formatted JSON"""
    import json
    formatted = json.dumps(obj.data, indent=2)
    return format_html(
        '<pre style="background: #f3f4f6; padding: 12px; '
        'border-radius: 4px; font-size: 12px;">{}</pre>',
        formatted
    )
```

### Links and References

```python
from django.urls import reverse
from django.utils.html import format_html

@display(description="Author")
def author_link(self, obj) -> str:
    """Link to author admin"""
    if not obj.author:
        return "-"
    url = reverse('admin:auth_user_change', args=[obj.author.id])
    return format_html(
        '<a href="{}">{}</a>',
        url,
        obj.author.get_full_name() or obj.author.username
    )
```

### Conditional Formatting

```python
@display(description="Health")
def health_status(self, obj) -> str:
    """Color-coded health status"""
    if obj.health > 80:
        return self.badge("Healthy", "green")
    elif obj.health > 50:
        return self.badge("Degraded", "yellow")
    else:
        return self.badge("Critical", "red")
```

### Display Attributes

The `@display` decorator accepts:

```python
@display(
    description="Column Title",      # Column header
    ordering="field_name",            # Enable sorting
    boolean=False,                    # Show as yes/no
)
```

---

## Actions

Actions are bulk operations on selected items. Use the `@action` decorator.

### Basic Action

```python
from unfold.decorators import action

@action(description="Activate selected items")
def activate_items(self, request, queryset):
    """Activate selected items"""
    count = queryset.update(is_active=True)
    self.message_user(request, f"Activated {count} item(s)")
```

**In list_display:**

```python
class ArticleAdmin(BaseAdmin):
    list_display = ["title", "status_badge"]
    actions = ["publish_articles", "archive_articles"]
    
    @action(description="Publish selected articles")
    def publish_articles(self, request, queryset):
        count = queryset.update(status='published', published_at=now())
        self.message_user(request, f"Published {count} article(s)")
    
    @action(description="Archive selected articles")
    def archive_articles(self, request, queryset):
        count = queryset.update(is_archived=True)
        self.message_user(request, f"Archived {count} article(s)")
```

### With Permissions

```python
@action(description="Delete permanently")
def delete_permanently(self, request, queryset):
    if not request.user.is_superuser:
        self.message_user(request, "Not allowed", level="error")
        return
    
    count, _ = queryset.delete()
    self.message_user(request, f"Permanently deleted {count} item(s)")
```

### Action Helper Pattern

```python
class BaseAdmin(UnfoldModelAdmin):
    def message_user_success(self, request, message):
        """Success message"""
        self.message_user(request, message)
    
    def message_user_error(self, request, message):
        """Error message"""
        from django.contrib import messages
        messages.error(request, message)

@action(description="Verify users")
def verify_users(self, request, queryset):
    try:
        count = 0
        for user in queryset:
            if not user.is_verified:
                user.verify_email()
                count += 1
        self.message_user_success(request, f"Verified {count} user(s)")
    except Exception as e:
        self.message_user_error(request, f"Error: {str(e)}")
```

### Common Actions

```python
# Activate/Deactivate
@action(description="Activate selected")
def activate(self, request, queryset):
    queryset.update(is_active=True)

@action(description="Deactivate selected")
def deactivate(self, request, queryset):
    queryset.update(is_active=False)

# Publish/Unpublish
@action(description="Publish selected")
def publish(self, request, queryset):
    queryset.update(status='published')

@action(description="Unpublish selected")
def unpublish(self, request, queryset):
    queryset.update(status='draft')

# Mark/Unmark
@action(description="Mark as featured")
def mark_featured(self, request, queryset):
    queryset.update(is_featured=True)

@action(description="Unmark as featured")
def unmark_featured(self, request, queryset):
    queryset.update(is_featured=False)
```

---

## Filtering & Searching

Unfold provides advanced filtering options beyond Django's default.

### Search Fields

```python
class ArticleAdmin(BaseAdmin):
    search_fields = [
        "title",           # Exact field
        "content",         # Full-text
        "author__email",   # Related field
        "tags__name",      # Many-to-many
    ]
```

### List Filter - Basic

```python
class ArticleAdmin(BaseAdmin):
    list_filter = [
        "is_published",    # Boolean
        "status",          # Choice field
        "created_at",      # Date field
        "author",          # Foreign key
    ]
```

### List Filter - Advanced (Unfold)

```python
from unfold.contrib.filters.admin import (
    BooleanRadioFilter,      # Yes/No radio buttons
    RangeDateFilter,         # Date range picker
    RangeDateTimeFilter,     # DateTime range picker
    RelatedCheckboxFilter,   # Checkbox list for relations
    TextFilter,             # Text search filter
)

class ArticleAdmin(BaseAdmin):
    list_filter = [
        ("is_published", BooleanRadioFilter),
        ("status", RelatedCheckboxFilter),
        ("created_at", RangeDateFilter),
        ("author", RelatedCheckboxFilter),
    ]
```

### Custom Filter Example

```python
class ArticleAdmin(BaseAdmin):
    list_filter = [
        ("is_published", BooleanRadioFilter),
        ("status", RelatedCheckboxFilter),
        ("created_at", RangeDateFilter),
        ("author", RelatedCheckboxFilter),
    ]
```

**Benefits:**

- **BooleanRadioFilter** — Better UX than checkboxes
- **RangeDateFilter** — Pick date ranges visually
- **RelatedCheckboxFilter** — Check multiple relations at once
- **TextFilter** — Search within field values

---

## Common Patterns

### Pattern 1: Status Badges with Sorting

```python
class ArticleAdmin(BaseAdmin):
    list_display = ["title", "status_badge", "created_at"]
    
    @display(description="Status", ordering="status")
    def status_badge(self, obj) -> str:
        """Sortable status badge"""
        colors = {
            "draft": "gray",
            "published": "green",
            "archived": "red",
        }
        return self.badge(
            obj.get_status_display(),
            colors.get(obj.status, "gray")
        )
```

**Key:** The `ordering="status"` parameter makes the column sortable.

### Pattern 2: Related Object Display

```python
class ArticleAdmin(BaseAdmin):
    list_display = ["title", "author_link", "created_at"]
    
    @display(description="Author")
    def author_link(self, obj) -> str:
        """Link to related author"""
        if not obj.author:
            return "-"
        from django.urls import reverse
        url = reverse('admin:auth_user_change', args=[obj.author.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.author.get_full_name() or obj.author.username
        )
```

### Pattern 3: Count Displays

```python
class AuthorAdmin(BaseAdmin):
    list_display = ["name", "article_count", "verified_badge"]
    
    @display(description="Articles")
    def article_count(self, obj) -> str:
        """Count related articles"""
        count = obj.articles.count()
        return self.badge(str(count), "blue")
```

### Pattern 4: Timestamp Formatting

```python
from django.utils.dateformat import format as format_date

class EventAdmin(BaseAdmin):
    list_display = ["name", "timestamp_display"]
    
    @display(description="When", ordering="timestamp")
    def timestamp_display(self, obj) -> str:
        """Format timestamp nicely"""
        return format_date(obj.timestamp, "M d, Y H:i:s")
```

### Pattern 5: Query Optimization

```python
class ArticleAdmin(BaseAdmin):
    list_display = ["title", "author_name", "tag_count"]
    
    def get_queryset(self, request):
        """Optimize queries with select/prefetch"""
        qs = super().get_queryset(request)
        # Reduce queries: avoid N+1 for author lookups
        return qs.select_related('author').prefetch_related('tags')
    
    @display(description="Author")
    def author_name(self, obj) -> str:
        """Uses prefetched author"""
        return obj.author.get_full_name() or "-"
    
    @display(description="Tags")
    def tag_count(self, obj) -> str:
        """Uses prefetched tags"""
        return str(obj.tags.count())
```

### Pattern 6: Permission-Based Display

```python
class ArticleAdmin(BaseAdmin):
    list_display = ["title", "author", "status_badge"]
    
    def get_list_display(self, request):
        """Show different columns based on permissions"""
        display = list(self.list_display)
        if request.user.is_superuser:
            display.append("internal_notes")
        return display
```

### Pattern 7: Readonly Fields with Fieldsets

```python
class ArticleAdmin(BaseAdmin):
    fieldsets = (
        ("Content", {
            "fields": ("title", "content", "author")
        }),
        ("Status", {
            "fields": ("status", "is_published", "published_at")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)  # Collapsed by default
        }),
    )
    
    readonly_fields = ["created_at", "updated_at"]
```

### Pattern 8: Soft Delete with Queryset Filtering

```python
class ArticleAdmin(SoftDeleteAdmin):
    list_display = ["title", "is_deleted_badge"]
    
    def get_queryset(self, request):
        """Show all to superusers, only active to others"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(is_deleted=False)
        return qs
```

---

## Advanced Features

### Fieldsets & Collapsible Sections

```python
class ArticleAdmin(BaseAdmin):
    fieldsets = (
        (None, {
            "fields": ("title", "content", "author"),
            "description": "Article content details"
        }),
        ("Publishing", {
            "fields": ("status", "is_published", "published_at"),
        }),
        ("Advanced Options", {
            "fields": ("is_featured", "tags", "seo_keywords"),
            "classes": ("collapse",)  # Collapsed by default
        }),
        ("System", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = ["created_at", "updated_at"]
```

### Inline Editing

Use `BaseTabularInline` and `BaseStackedInline`:

```python
from unfold_admin_bases import BaseTabularInline, BaseStackedInline

class CommentInline(BaseTabularInline):
    """Inline comments - compact table view"""
    model = Comment
    extra = 1
    fields = ["author", "content", "created_at"]
    readonly_fields = ["created_at"]

class AttachmentInline(BaseStackedInline):
    """Inline attachments - expanded view"""
    model = Attachment
    extra = 1
    fields = ["title", "file", "description"]

class ArticleAdmin(BaseAdmin):
    inlines = [CommentInline, AttachmentInline]
```

### Date Hierarchy Navigation

```python
class ArticleAdmin(BaseAdmin):
    date_hierarchy = "created_at"  # Quick navigation by date
```

Shows: Year → Month → Day drill-down in list view.

### Custom Ordering

```python
class ArticleAdmin(BaseAdmin):
    ordering = ["-created_at"]  # Newest first
    # or
    ordering = ["-is_published", "-created_at"]  # Published first, then newest
```

### Raw ID Fields (for Large Relations)

```python
class ArticleAdmin(BaseAdmin):
    raw_id_fields = ("author",)  # Use popup picker instead of dropdown
```

Useful when the related model has thousands of records.

### Autocomplete Fields

Requires `search_fields` on the related admin:

```python
class AuthorAdmin(BaseAdmin):
    search_fields = ["name", "email"]

class ArticleAdmin(BaseAdmin):
    autocomplete_fields = ["author"]  # Search instead of dropdown
```

---

## Best Practices

### 1. Use Sensible Defaults

```python
# ✅ Good - inherits sensible defaults
class ArticleAdmin(BaseAdmin):
    list_display = ["title", "author", "status"]

# ❌ Bad - duplicating defaults
class ArticleAdmin(BaseAdmin):
    list_display = ["title", "author", "status", "created_at"]
    list_per_page = 25
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]
```

BaseAdmin already has good defaults.

### 2. Optimize Queries

```python
# ✅ Good - prefetch related data
def get_queryset(self, request):
    qs = super().get_queryset(request)
    return qs.select_related('author').prefetch_related('tags')

# ❌ Bad - causes N+1 queries
def get_queryset(self, request):
    return super().get_queryset(request)
```

### 3. Use Display Decorators

```python
# ✅ Good - modern, clean
@display(description="Status", ordering="status")
def status_badge(self, obj):
    return self.badge(obj.get_status_display(), "green")

# ❌ Old - outdated syntax
def status_badge(self, obj):
    return obj.get_status_display()
status_badge.short_description = "Status"
status_badge.admin_order_field = "status"
```

### 4. Keep Actions Focused

```python
# ✅ Good - single responsibility
@action(description="Publish selected")
def publish(self, request, queryset):
    count = queryset.update(status='published')
    self.message_user(request, f"Published {count}")

# ❌ Bad - too many operations
@action(description="Publish & notify & log")
def publish(self, request, queryset):
    queryset.update(status='published')
    # ... send emails
    # ... update cache
    # ... complex logging
```

### 5. Use Readonly for Immutable Fields

```python
# ✅ Good
readonly_fields = ["created_at", "updated_at", "id"]

# ❌ Bad - users see fields they can't edit
list_display = ["title", "created_at", "updated_at"]
# (without marking readonly, it's confusing)
```

### 6. Filter for User Context

```python
# ✅ Good - non-superusers only see their own
def get_queryset(self, request):
    qs = super().get_queryset(request)
    if request.user.is_superuser:
        return qs
    return qs.filter(author=request.user)

# ❌ Bad - everyone sees everything
def get_queryset(self, request):
    return super().get_queryset(request)
```

### 7. Use Conditional Actions

```python
# ✅ Good - action only for published
@action(description="Archive published articles")
def archive_published(self, request, queryset):
    count = queryset.filter(status='published').update(
        status='archived'
    )
    self.message_user(request, f"Archived {count}")

# ❌ Bad - runs on everything
@action(description="Archive")
def archive(self, request, queryset):
    queryset.update(status='archived')
```

### 8. Use Collapsible Sections

```python
# ✅ Good - clean, organized
fieldsets = (
    ("Main", {"fields": ("title", "content")}),
    ("Advanced", {"fields": ("meta_tags",), "classes": ("collapse",)}),
)

# ❌ Bad - too many fields visible
fieldsets = (
    (None, {"fields": ("title", "content", "meta_tags", "seo_...")}),
)
```

---

## Examples

### Example 1: Complete User Admin

```python
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Complete user management"""
    
    list_display = [
        "email",
        "username",
        "verified_badge",
        "is_active",
        "date_joined",
    ]
    
    list_filter = [
        ("is_verified", BooleanRadioFilter),
        ("is_active", BooleanRadioFilter),
        ("groups", RelatedCheckboxFilter),
        ("created_at", RangeDateFilter),
    ]
    
    search_fields = [
        "email",
        "username",
        "first_name",
        "last_name",
    ]
    
    fieldsets = (
        (None, {
            "fields": ("username", "password", "email")
        }),
        ("Personal Info", {
            "fields": ("first_name", "last_name", "avatar", "bio")
        }),
        ("Verification", {
            "fields": ("is_verified", "verified_at"),
            "classes": ("collapse",)
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "groups"),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "date_joined"),
            "classes": ("collapse",)
        }),
    )
    
    readonly_fields = [
        "created_at",
        "date_joined",
        "verified_at",
    ]
    
    actions = ["verify_users", "activate_users"]
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.prefetch_related("groups")
    
    @display(description="Verified", ordering="is_verified")
    def verified_badge(self, obj):
        if obj.is_verified:
            return self.badge("✓ Verified", "green")
        return self.badge("Unverified", "red")
    
    @action(description="Mark as verified")
    def verify_users(self, request, queryset):
        count = 0
        for user in queryset:
            if not user.is_verified:
                user.verify_email()
                count += 1
        self.message_user(request, f"Verified {count} user(s)")
    
    @action(description="Activate users")
    def activate_users(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} user(s)")
```

### Example 2: Read-Only Audit Log

```python
@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdmin):
    """Immutable audit log"""
    
    list_display = [
        "timestamp_display",
        "action_badge",
        "user_display",
        "object_display",
    ]
    
    list_filter = [
        ("timestamp", RangeDateTimeFilter),
        ("user", RelatedCheckboxFilter),
    ]
    
    search_fields = [
        "object_repr",
        "user__email",
        "user__username",
    ]
    
    date_hierarchy = "timestamp"
    list_per_page = 50
    
    fieldsets = (
        ("Action", {
            "fields": ("timestamp", "action", "user")
        }),
        ("Object", {
            "fields": ("content_type", "object_id", "object_repr")
        }),
        ("Request Info", {
            "fields": ("ip_address", "user_agent"),
            "classes": ("collapse",)
        }),
    )
    
    readonly_fields = [
        "timestamp",
        "action",
        "user",
        "content_type",
        "object_id",
        "object_repr",
        "ip_address",
        "user_agent",
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")
    
    @display(description="Time", ordering="timestamp")
    def timestamp_display(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    @display(description="Action", ordering="action")
    def action_badge(self, obj):
        colors = {
            "create": "green",
            "update": "blue",
            "delete": "red",
        }
        return self.badge(
            obj.get_action_display(),
            colors.get(obj.action, "gray")
        )
    
    @display(description="User", ordering="user__email")
    def user_display(self, obj):
        if not obj.user:
            return "-"
        return f"{obj.user.email}"
```

### Example 3: Article with Soft Deletes

```python
@admin.register(Article)
class ArticleAdmin(SoftDeleteAdmin):
    """Article management with soft deletes"""
    
    list_display = [
        "title",
        "author",
        "status_badge",
        "is_deleted_badge",
        "created_at",
    ]
    
    list_filter = [
        ("status", RelatedCheckboxFilter),
        ("is_published", BooleanRadioFilter),
        ("is_deleted", BooleanRadioFilter),
        ("author", RelatedCheckboxFilter),
        ("created_at", RangeDateFilter),
    ]
    
    search_fields = ["title", "content", "author__email"]
    
    fieldsets = (
        ("Content", {
            "fields": ("title", "content", "author")
        }),
        ("Publishing", {
            "fields": ("status", "is_published", "published_at")
        }),
        ("Deletion", {
            "fields": ("is_deleted", "deleted_at"),
            "classes": ("collapse",)
        }),
        ("System", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    readonly_fields = [
        "created_at",
        "updated_at",
        "published_at",
        "deleted_at",
    ]
    
    actions = [
        "publish_articles",
        "restore_items",
    ]
    
    inlines = [CommentInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Show all to superusers, only active to others
        if not request.user.is_superuser:
            qs = qs.filter(is_deleted=False)
        return qs.select_related('author')
    
    @display(description="Status", ordering="status")
    def status_badge(self, obj):
        colors = {
            "draft": "gray",
            "published": "green",
            "archived": "red",
        }
        return self.badge(
            obj.get_status_display(),
            colors.get(obj.status, "gray")
        )
    
    @action(description="Publish selected articles")
    def publish_articles(self, request, queryset):
        from django.utils.timezone import now
        count = queryset.update(status='published', published_at=now())
        self.message_user(request, f"Published {count} article(s)")
```

---

## Troubleshooting

### Problem: Date hierarchy not working

**Check:** Do you have a DateTimeField or DateField?

```python
# ✅ Correct
date_hierarchy = "created_at"  # If created_at is a DateTimeField

# ❌ Wrong
date_hierarchy = "name"  # CharField doesn't have dates
```

### Problem: Searching not working

**Check:** Are fields in search_fields?

```python
# ✅ Correct
search_fields = ["title", "content"]

# ❌ Wrong
search_fields = ["title"]  # Missing content
```

### Problem: Too many queries (N+1)

**Check:** Are you using select_related/prefetch_related?

```python
# ✅ Correct
def get_queryset(self, request):
    qs = super().get_queryset(request)
    return qs.select_related('author')

# ❌ Wrong
def get_queryset(self, request):
    return super().get_queryset(request)
```

### Problem: Readonly fields showing on create form

**Check:** Use `get_readonly_fields()` for conditional:

```python
def get_readonly_fields(self, request, obj=None):
    """Make timestamps readonly, but not on create"""
    if obj:  # Editing
        return self.readonly_fields
    return []  # Creating - no readonly
```

### Problem: Actions not appearing

**Check:** Is the action in the `actions` list?

```python
# ✅ Correct
class MyAdmin(BaseAdmin):
    actions = ["my_action"]
    
    @action(description="My action")
    def my_action(self, request, queryset):
        pass

# ❌ Wrong - missing from list
class MyAdmin(BaseAdmin):
    # actions not defined
    
    @action(description="My action")
    def my_action(self, request, queryset):
        pass
```

---

## Summary

| Feature | Usage |
|---------|-------|
| **BaseAdmin** | Sensible defaults, badge helper |
| **ReadOnlyAdmin** | Immutable records (logs, audit) |
| **SoftDeleteAdmin** | Soft-deleted models with restore |
| **BaseUserAdmin** | User management with optimization |
| **@display** | Format list columns |
| **@action** | Bulk operations |
| **Filters** | Range, checkbox, boolean filters |
| **Inline** | Edit related objects inline |
| **Fieldsets** | Organize form fields |

---

## Next Steps

1. Replace Django's default admin imports with Unfold
2. Use BaseAdmin as your foundation
3. Add specialized classes (ReadOnly, SoftDelete) as needed
4. Use @display decorators for custom formatting
5. Optimize queries with select_related/prefetch_related
6. Add filters and search for better navigation

---

## Questions?

Refer to:
1. **Base Classes** section for class selection
2. **Display Methods** section for formatting
3. **Common Patterns** section for real examples
4. **Examples** section for complete implementations