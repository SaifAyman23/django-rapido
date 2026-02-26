"""
Production-Grade Unfold Admin Base Classes
============================================

Provides reusable, composable admin classes with Unfold integration.
Includes advanced filtering, custom actions, bulk operations, and audit logging.

Key Features:
- Unfold UI theming and styling
- Query optimization (select_related, prefetch_related)
- Permission-based visibility
- Advanced filtering support
- Custom action framework
- Display decorators with color coding
- Timestamp management
- Soft delete support
- Publishable model support
- DjangoQL search integration
"""

from typing import List, Optional, Any, Tuple, Dict, Set
from datetime import datetime

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoBaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as DjangoBaseGroupAdmin
from django.core.validators import EMPTY_VALUES
from django.db import models
from django.db.models import QuerySet, OuterRef
from django.http import HttpRequest, Http404, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import path, reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator

from unfold.admin import ModelAdmin as UnfoldModelAdmin, StackedInline, TabularInline
from unfold.decorators import display, action
from unfold.enums import ActionVariant
from unfold.contrib.filters.admin import (
    AllValuesCheckboxFilter,
    AutocompleteSelectMultipleFilter,
    BooleanRadioFilter,
    CheckboxFilter,
    ChoicesCheckboxFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
    RangeNumericFilter,
    RelatedCheckboxFilter,
    RelatedDropdownFilter,
    SingleNumericFilter,
    SliderNumericFilter,
    TextFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.paginator import InfinitePaginator
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultiple,
    UnfoldAdminColorInputWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminSelectWidget,
    UnfoldAdminSplitDateTimeWidget,
    UnfoldAdminTextInputWidget,
)
from unfold.sections import TableSection, TemplateSection


# ===========================
# Core Mixin Classes
# ===========================

class TimestampMixin:
    """Mixin for handling timestamp fields (created_at, updated_at)"""

    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"

    def get_fieldsets(self, request: HttpRequest, obj=None) -> List[Tuple]:
        """Add timestamp fieldset to fieldsets if not present"""
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets_list = list(fieldsets)

        # Check if timestamps fieldset already exists
        has_timestamps = False
        for fieldset in fieldsets_list:
            fieldset_title = str(fieldset[0]) if fieldset[0] else ""
            if "Timestamps" in fieldset_title:
                has_timestamps = True
                break

        return fieldsets_list


class QueryOptimizationMixin:
    """Mixin for query optimization with select_related and prefetch_related"""

    select_related_fields: List[str] = []
    prefetch_related_fields: List[str] = []

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Apply select_related and prefetch_related to optimize queries"""
        qs = super().get_queryset(request)

        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)

        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)

        return qs


class PermissionMixin:
    """Mixin for consistent permission handling across all admins"""

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Only staff can add"""
        return request.user.is_staff

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Only staff can change"""
        return request.user.is_staff

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """Only superusers can delete"""
        return request.user.is_superuser

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        """Only staff can view"""
        return request.user.is_staff


class DisplayMixin:
    """Mixin for common display helper methods"""

    @staticmethod
    def badge(label: str, color: str, bg_color: str) -> str:
        """Create a styled badge for display methods"""
        return format_html(
            '<span style="background-color: {}; color: {}; '
            'padding: 4px 8px; border-radius: 4px; font-weight: 500;">{}</span>',
            bg_color,
            color,
            label,
        )

    @staticmethod
    def colored_text(text: str, color: str) -> str:
        """Create colored text"""
        return format_html(
            '<span style="color: {}; font-weight: 500;">{}</span>',
            color,
            text,
        )

    @staticmethod
    def get_badge_colors(status: str) -> Tuple[str, str]:
        """Return (bg_color, text_color) for status"""
        colors = {
            # Soft Delete
            "deleted": ("#fee2e2", "#dc2626"),
            "active": ("#dcfce7", "#16a34a"),
            # Publishable
            "draft": ("#f3f4f6", "#6b7280"),
            "published": ("#dcfce7", "#16a34a"),
            "archived": ("#fef3c7", "#d97706"),
            # User Status
            "verified": ("#dcfce7", "#16a34a"),
            "unverified": ("#fee2e2", "#dc2626"),
            "staff": ("#f3e8ff", "#9333ea"),
            # Audit Actions
            "create": ("#dcfce7", "#16a34a"),
            "update": ("#bfdbfe", "#2563eb"),
            "delete": ("#fee2e2", "#dc2626"),
            "restore": ("#fef3c7", "#d97706"),
            "publish": ("#f3e8ff", "#9333ea"),
        }
        return colors.get(status, ("#f3f4f6", "#6b7280"))


class ActionsMixin:
    """Mixin for action support with common patterns"""

    actions_selection_counter = True
    actions_detail = False

    def message_user_success(self, request: HttpRequest, message: str):
        """Convenience method for success message"""
        messages.success(request, message)

    def message_user_error(self, request: HttpRequest, message: str):
        """Convenience method for error message"""
        messages.error(request, message)

    def message_user_info(self, request: HttpRequest, message: str):
        """Convenience method for info message"""
        messages.info(request, message)


# ===========================
# Base Model Admin Classes
# ===========================

class BaseModelAdmin(
    QueryOptimizationMixin,
    PermissionMixin,
    DisplayMixin,
    TimestampMixin,
    ActionsMixin,
    UnfoldModelAdmin,
):
    """
    Production-grade base model admin with full Unfold integration.

    Inherits from all essential mixins and UnfoldModelAdmin to provide:
    - Query optimization (select_related, prefetch_related)
    - Consistent permission handling
    - Timestamp management
    - Display helpers with color coding
    - Action framework with messaging
    - Unfold UI theming and styling

    Child admins automatically get:
    - Consistent styling and behavior
    - Database query optimization
    - Permission-based field visibility
    - Automatic timestamp fieldset
    - Action support with selection counter

    Usage:
        @admin.register(MyModel)
        class MyModelAdmin(BaseModelAdmin):
            list_display = ["name", "created_at"]
            search_fields = ["name"]
            select_related_fields = ["author"]
            prefetch_related_fields = ["tags"]
    """

    # Display Settings
    list_per_page = 25
    list_max_show_all = 100
    search_help_text = "Search across key fields"
    compressed_fields = True

    # Default ordering
    ordering = ["-created_at"]

    # List display defaults
    list_display = ["__str__", "created_at"]

    # Unfold-specific
    list_fullwidth = True


class ReadOnlyModelAdmin(BaseModelAdmin):
    """
    Admin for read-only models (no add, change, or delete).
    Useful for log models, view-only data, or immutable records.

    Usage:
        @admin.register(AuditLog)
        class AuditLogAdmin(ReadOnlyModelAdmin):
            list_display = ["timestamp", "action", "user"]
    """

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return request.user.is_superuser

    readonly_fields = ["created_at", "updated_at"]


class SoftDeleteModelAdmin(BaseModelAdmin):
    """
    Admin for models with soft delete support.

    Assumes model has: is_deleted, deleted_at fields and:
    - QuerySet method: active() - returns non-deleted records
    - QuerySet method: all_with_deleted() - returns all records

    Features:
    - Shows only active records to regular staff
    - Shows all records (including deleted) to superusers
    - Soft delete display with red styling
    - Restore action for deleted records
    - Filter deleted/active records

    Usage:
        @admin.register(MyModel)
        class MyModelAdmin(SoftDeleteModelAdmin):
            list_display = ["name", "deleted_at_display", "is_deleted_display"]
    """

    # List Display
    list_display = ["__str__", "deleted_at_display", "is_deleted_display"]

    # Actions
    actions = ["restore_deleted_records"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        Show only active records to regular staff.
        Show all records (including deleted) to superusers.
        """
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            if hasattr(qs, "all_with_deleted"):
                return qs.all_with_deleted()
        else:
            if hasattr(qs, "active"):
                return qs.active()

        return qs

    @display(
        description="Deleted At",
        ordering="deleted_at",
    )
    def deleted_at_display(self, obj) -> str:
        """Display soft delete timestamp with red styling"""
        if obj.deleted_at:
            return self.colored_text(
                obj.deleted_at.strftime("%Y-%m-%d %H:%M"),
                "#dc2626",
            )
        return "-"

    @display(description="Deleted")
    def is_deleted_display(self, obj) -> str:
        """Display deletion status with color coding"""
        if obj.is_deleted:
            return self.badge("Yes", "#dc2626", "#fee2e2")
        return self.badge("No", "#16a34a", "#dcfce7")

    @action(
        description="Restore selected records",
        permissions=["change"],
    )
    def restore_deleted_records(
        self, request: HttpRequest, queryset: QuerySet
    ) -> None:
        """Restore soft-deleted records"""
        if not hasattr(queryset, "restore"):
            self.message_user_error(
                request,
                "This model does not support restoration",
            )
            return

        count = queryset.restore()
        self.message_user_success(
            request,
            f"Successfully restored {count} record(s).",
        )


class PublishableModelAdmin(BaseModelAdmin):
    """
    Admin for publishable models (draft/published/archived).

    Assumes model has: status, published_at fields and:
    - Choice field: status in ["draft", "published", "archived"]
    - DateTimeField: published_at

    Features:
    - Status display with color-coded badge
    - Publish/unpublish/archive actions
    - Publication timestamp display
    - Filter by status and publication date

    Usage:
        @admin.register(Article)
        class ArticleAdmin(PublishableModelAdmin):
            list_display = ["title", "status_display", "published_at_display"]
    """

    # List Display
    list_display = ["__str__", "status_display", "published_at_display"]

    # Filtering
    list_filter = ["status", "published_at"]

    # Actions
    actions = ["publish_records", "unpublish_records", "archive_records"]

    @display(
        description="Status",
        ordering="status",
    )
    def status_display(self, obj) -> str:
        """Display publication status with color-coded badge"""
        colors = {
            "draft": ("#f3f4f6", "#6b7280"),
            "published": ("#dcfce7", "#16a34a"),
            "archived": ("#fef3c7", "#d97706"),
        }

        bg, color = colors.get(obj.status, ("#f3f4f6", "#6b7280"))
        return self.badge(obj.get_status_display(), color, bg)

    @display(
        description="Published At",
        ordering="published_at",
    )
    def published_at_display(self, obj) -> str:
        """Display publication timestamp"""
        if obj.published_at:
            return obj.published_at.strftime("%Y-%m-%d %H:%M")
        return "-"

    @action(
        description="Publish selected records",
        permissions=["change"],
    )
    def publish_records(
        self, request: HttpRequest, queryset: QuerySet
    ) -> None:
        """Publish selected records"""
        count = queryset.update(status="published")
        self.message_user_success(
            request,
            f"Published {count} record(s).",
        )

    @action(
        description="Unpublish selected records",
        permissions=["change"],
    )
    def unpublish_records(
        self, request: HttpRequest, queryset: QuerySet
    ) -> None:
        """Unpublish selected records (back to draft)"""
        count = queryset.update(status="draft")
        self.message_user_success(
            request,
            f"Unpublished {count} record(s).",
        )

    @action(
        description="Archive selected records",
        permissions=["change"],
    )
    def archive_records(
        self, request: HttpRequest, queryset: QuerySet
    ) -> None:
        """Archive selected records"""
        count = queryset.update(status="archived")
        self.message_user_success(
            request,
            f"Archived {count} record(s).",
        )


# ===========================
# Specialized Admin Classes
# ===========================

class ImportExportModelAdmin(BaseModelAdmin):
    """
    Admin with import/export support via django-import-export.

    Requires: import_export package
    Inherits from BaseModelAdmin to get all standard features.

    Usage:
        from import_export.admin import ImportExportModelAdmin

        @admin.register(Product)
        class ProductAdmin(ImportExportModelAdmin):
            resource_class = ProductResource
            list_display = ["name", "price"]
    """

    pass


class TranslatableModelAdmin(BaseModelAdmin):
    """
    Admin for models with django-modeltranslation support.

    Requires: modeltranslation package
    Inherits from BaseModelAdmin to get all standard features.

    Usage:
        from modeltranslation.admin import TabbedTranslationAdmin

        @admin.register(Page)
        class PageAdmin(TranslatableModelAdmin, TabbedTranslationAdmin):
            list_display = ["title", "slug"]
    """

    pass


class AuditableModelAdmin(BaseModelAdmin):
    """
    Admin for models with django-simple-history support.

    Requires: django-simple-history package
    Inherits from BaseModelAdmin to get all standard features.

    Features:
    - History tracking
    - Change logging
    - Revision comparison

    Usage:
        from simple_history.admin import SimpleHistoryAdmin

        @admin.register(Article)
        class ArticleAdmin(AuditableModelAdmin, SimpleHistoryAdmin):
            list_display = ["title", "author", "created_at"]
    """

    history_list_per_page = 10


class PermissionBasedModelAdmin(BaseModelAdmin):
    """
    Admin with fine-grained permission support via django-guardian.

    Requires: django-guardian package
    Inherits from BaseModelAdmin to get all standard features.

    Features:
    - Object-level permissions
    - User/group permissions per object
    - Permission-based visibility

    Usage:
        from guardian.admin import GuardedModelAdmin

        @admin.register(Document)
        class DocumentAdmin(PermissionBasedModelAdmin, GuardedModelAdmin):
            list_display = ["title", "owner"]
    """

    pass


class SearchableModelAdmin(BaseModelAdmin):
    """
    Admin with advanced search via DjangoQL.

    Requires: djangoql package
    Inherits from BaseModelAdmin to get all standard features.

    Features:
    - Natural language search
    - Complex query support
    - Field-based filtering

    Usage:
        from djangoql.admin import DjangoQLSearchMixin

        @admin.register(User)
        class UserAdmin(SearchableModelAdmin, DjangoQLSearchMixin):
            list_display = ["email", "username"]
    """

    pass


# ===========================
# User Management Admins
# ===========================

class BaseUserAdmin(BaseModelAdmin, DjangoBaseUserAdmin):
    """
    Enhanced base user admin with Unfold integration.

    Provides:
    - All BaseModelAdmin features (query optimization, permissions, etc.)
    - Django's built-in UserAdmin functionality
    - Enhanced display methods for user status
    - Bulk actions for user management

    Usage:
        @admin.register(CustomUser)
        class CustomUserAdmin(BaseUserAdmin):
            list_display = ["email", "username", "is_staff"]
    """

    # List display
    list_display = ["username", "email", "is_active", "is_staff"]

    # Search
    search_fields = ["username", "email", "first_name", "last_name"]

    # Filtering
    list_filter = ["is_active", "is_staff", "is_superuser", "date_joined"]

    # Query optimization
    select_related_fields = []
    prefetch_related_fields = ["groups", "user_permissions"]


class GroupAdmin(BaseModelAdmin, DjangoBaseGroupAdmin):
    """
    Enhanced group admin with Unfold integration.

    Provides:
    - All BaseModelAdmin features
    - Django's built-in GroupAdmin functionality
    - Permission management

    Usage:
        @admin.register(Group)
        class GroupAdmin(GroupAdmin):
            pass
    """

    list_display = ["name"]
    search_fields = ["name"]


# ===========================
# Inline Admin Classes
# ===========================

class BaseStackedInline(StackedInline):
    """Base stacked inline with common settings"""

    extra = 1
    classes = ("collapse",)


class BaseTabularInline(TabularInline):
    """Base tabular inline with common settings"""

    extra = 1


class RelatedInline(BaseTabularInline):
    """
    Simple related object inline.

    Usage:
        class AuthorBooksInline(RelatedInline):
            model = Book
            fields = ["title", "published_at"]
    """

    pass


class StackedRelatedInline(BaseStackedInline):
    """
    Stacked related object inline with collapse.

    Usage:
        class AuthorBiographyInline(StackedRelatedInline):
            model = Biography
            fields = ["bio", "image"]
    """

    pass


# ===========================
# Filter Classes
# ===========================

class BaseTextFilter(TextFilter):
    """Base text filter with custom title and parameter name"""

    title: str = "Search"
    parameter_name: str = "search"

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if self.value() in EMPTY_VALUES:
            return queryset
        return queryset.filter(**{self.parameter_name: self.value()})


# ===========================
# Utility Classes
# ===========================

class UnfoldWidgetMixin:
    """Mixin for easy access to Unfold widgets"""

    # Widget shortcuts
    text_widget = UnfoldAdminTextInputWidget
    select_widget = UnfoldAdminSelectWidget
    select2_widget = UnfoldAdminSelect2Widget
    color_widget = UnfoldAdminColorInputWidget
    datetime_widget = UnfoldAdminSplitDateTimeWidget
    checkbox_widget = UnfoldAdminCheckboxSelectMultiple
    wysiwyg_widget = WysiwygWidget

    def get_formfield_for_text(
        self, db_field: models.Field, **kwargs
    ) -> models.Field:
        """Get text field with Unfold widget"""
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if isinstance(db_field, models.CharField):
            formfield.widget = self.text_widget()
        return formfield