"""
Ultimate Django admin customization for Unfold
Provides production-grade admin interface with:
- Advanced filtering
- Custom actions
- Bulk operations
- Audit logging
- Permission-based visibility
- Unfold UI theme integration
"""

from typing import List, Optional, Any, Tuple, Dict
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.decorators import display, action

from common.models import CustomUser, AuditLog

# ===========================
# Unfold Configuration Mixin
# ===========================

class UnfoldConfigMixin:
    """Mixin with Unfold-specific configuration that all child admins inherit"""

    # Sidebar and display
    compress_fields = True
    list_per_page = 25
    list_max_show_all = 100
    search_help_text = _("Search across key fields")
    date_hierarchy = "created_at"
    
    # Query optimization (inherited by all child admins)
    select_related_fields: List[str] = []
    prefetch_related_fields: List[str] = []
    
    # Unfold-specific settings
    readonly_fields = ["id", "created_at", "updated_at"]
    
    # Actions configuration
    actions_selection_counter = True
    actions_detail = False
    
    # Default ordering
    ordering = ["-created_at"]


# ===========================
# Custom Admin Base Classes
# ===========================

class BaseModelAdmin(UnfoldConfigMixin, ModelAdmin):
    """
    Base model admin with full Unfold integration and common functionality
    
    All child admins automatically inherit:
    - Unfold UI theming and styling
    - Query optimization (select_related, prefetch_related)
    - Permission handling
    - Timestamp management
    - Action support with selection counter
    - Enhanced display formatting
    """

    # Display Settings
    date_hierarchy = "created_at"
    list_per_page = 25
    search_help_text = _("Search across key fields")

    # Common Readonly Fields
    readonly_fields = ["id", "created_at", "updated_at"]

    # Timestamps Fieldset (Collapsed)
    fieldsets_extend = [
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at", "id"),
                "classes": ("collapse",),
                "description": _("Automatically managed timestamps"),
            },
        ),
    ]

    # Actions Configuration
    actions_selection_counter = True
    actions_detail = False

    def get_fieldsets(self, request: HttpRequest, obj=None) -> List[Tuple]:
        """
        Add timestamp fieldset to all child admins
        This ensures every admin has consistent timestamp management
        """
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets_list = list(fieldsets)

        # Check if timestamps fieldset already exists
        has_timestamps = any(
            _("Timestamps") in str(fieldset[0]) for fieldset in fieldsets_list
        )

        # Add timestamps fieldset if not present
        if not has_timestamps and self.fieldsets_extend:
            fieldsets_list.extend(self.fieldsets_extend)

        return fieldsets_list

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        Optimize queryset with select_related and prefetch_related
        
        Child classes can set:
        - select_related_fields = ['author', 'category']
        - prefetch_related_fields = ['tags', 'comments']
        """
        qs = super().get_queryset(request)

        # Apply select_related for foreign keys
        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)

        # Apply prefetch_related for reverse relations
        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)

        return qs

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


class SoftDeleteModelAdmin(BaseModelAdmin):
    """
    Admin for models with soft delete support
    
    Inherits from BaseModelAdmin to get:
    - Unfold UI theming
    - Query optimization
    - Permission handling
    - Timestamp management
    
    Adds:
    - Soft delete display
    - Restore action
    - Filtering of deleted/active records
    """

    # List Display
    list_display = ["__str__", "deleted_at_display", "is_deleted_display"]

    # Soft Delete Filtering
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        Show only active records to regular staff
        Show all records (including deleted) to superusers
        """
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            # Superusers can see deleted records
            if hasattr(qs, "all_with_deleted"):
                return qs.all_with_deleted()
        else:
            # Regular staff only sees active records
            if hasattr(qs, "active"):
                return qs.active()

        return qs

    # Display Methods
    @display(
        description=_("Deleted At"),
        ordering="deleted_at",
    )
    def deleted_at_display(self, obj):
        """Display soft delete timestamp with red styling"""
        if obj.deleted_at:
            return format_html(
                '<span style="color: #dc2626; font-weight: 500;">{}</span>',
                obj.deleted_at.strftime("%Y-%m-%d %H:%M"),
            )
        return "-"

    @display(description=_("Deleted"))
    def is_deleted_display(self, obj):
        """Display deletion status with color coding"""
        if obj.is_deleted:
            return format_html(
                '<span style="background-color: #fee2e2; color: #dc2626; '
                'padding: 4px 8px; border-radius: 4px; font-weight: 500;">Yes</span>'
            )
        return format_html(
            '<span style="background-color: #dcfce7; color: #16a34a; '
            'padding: 4px 8px; border-radius: 4px; font-weight: 500;">No</span>'
        )

    # Actions
    actions = ["restore_deleted_records"]

    @action(
        description=_("Restore selected records"),
        permissions=["change"],
    )
    def restore_deleted_records(self, request: HttpRequest, queryset: QuerySet):
        """Restore soft-deleted records"""
        if not hasattr(queryset, "restore"):
            self.message_user(
                request,
                _("This model does not support restoration"),
                level=admin.messages.ERROR,
            )
            return

        count = queryset.restore()
        self.message_user(
            request,
            _("Successfully restored {} record(s).").format(count),
            level=admin.messages.SUCCESS,
        )


class PublishableModelAdmin(BaseModelAdmin):
    """
    Admin for publishable models (draft/published/archived)
    
    Inherits from BaseModelAdmin to get:
    - Unfold UI theming
    - Query optimization
    - Permission handling
    - Timestamp management
    
    Adds:
    - Status display with color coding
    - Publish/unpublish/archive actions
    - Publication timestamp display
    """

    # List Display
    list_display = ["__str__", "status_display", "published_at_display"]

    # Filtering
    list_filter = ["status", "published_at"]

    # Display Methods
    @display(
        description=_("Status"),
        ordering="status",
    )
    def status_display(self, obj):
        """Display publication status with color-coded badge"""
        colors = {
            "draft": ("gray", "#6b7280"),
            "published": ("green", "#16a34a"),
            "archived": ("orange", "#ea580c"),
        }

        bg_light, color = colors.get(obj.status, ("gray", "#6b7280"))

        return format_html(
            '<span style="background-color: {bg}20; color: {color}; '
            'padding: 4px 8px; border-radius: 4px; font-weight: 500;">{label}</span>',
            bg=color,
            color=color,
            label=obj.get_status_display(),
        )

    @display(
        description=_("Published At"),
        ordering="published_at",
    )
    def published_at_display(self, obj):
        """Display publication timestamp"""
        if obj.published_at:
            return obj.published_at.strftime("%Y-%m-%d %H:%M")
        return "-"

    # Actions
    actions = ["publish_records", "unpublish_records", "archive_records"]

    @action(
        description=_("Publish selected records"),
        permissions=["change"],
    )
    def publish_records(self, request: HttpRequest, queryset: QuerySet):
        """Publish selected records"""
        if not hasattr(queryset.first(), "publish"):
            self.message_user(
                request,
                _("This model does not support publishing"),
                level=admin.messages.ERROR,
            )
            return

        count = 0
        for obj in queryset:
            obj.publish()
            count += 1

        self.message_user(
            request,
            _("Published {} record(s).").format(count),
            level=admin.messages.SUCCESS,
        )

    @action(
        description=_("Unpublish selected records"),
        permissions=["change"],
    )
    def unpublish_records(self, request: HttpRequest, queryset: QuerySet):
        """Unpublish selected records (back to draft)"""
        count = queryset.update(status="draft")
        self.message_user(
            request,
            _("Unpublished {} record(s).").format(count),
            level=admin.messages.SUCCESS,
        )

    @action(
        description=_("Archive selected records"),
        permissions=["change"],
    )
    def archive_records(self, request: HttpRequest, queryset: QuerySet):
        """Archive selected records"""
        count = queryset.update(status="archived")
        self.message_user(
            request,
            _("Archived {} record(s).").format(count),
            level=admin.messages.SUCCESS,
        )


# ===========================
# Custom User Admin (Unfold-Compliant)
# ===========================

@admin.register(CustomUser)
class CustomUserAdmin(UnfoldConfigMixin, BaseUserAdmin):
    """
    Custom user admin with Unfold integration
    
    Inherits from BaseUserAdmin and UnfoldConfigMixin to get:
    - Unfold UI theming
    - Query optimization
    - Permission handling
    - Custom display decorators
    """

    model = CustomUser

    # Fieldsets
    fieldsets = (
        (None, {"fields": ("id", "email", "password", "username")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone_number",
                    "bio",
                    "avatar",
                )
            },
        ),
        (
            _("Verification"),
            {
                "fields": (
                    "is_verified",
                    "verified_at",
                    "verification_token",
                    "two_factor_enabled",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "fields": ("last_login_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )

    # List Display
    list_display = [
        "email",
        "username",
        "full_name",
        "verified_display",
        "active_display",
        "staff_display",
    ]

    # Filtering
    list_filter = ["is_verified", "is_active", "is_staff", "created_at"]

    # Search
    search_fields = ["email", "username", "first_name", "last_name"]

    # Ordering
    ordering = ["-created_at"]

    # Readonly Fields
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "verified_at",
        "last_login_at",
    ]

    # Query Optimization
    select_related_fields = []
    prefetch_related_fields = ["groups", "user_permissions"]

    # Display Methods
    @display(description=_("Full Name"))
    def full_name(self, obj):
        """Display user's full name or username"""
        return obj.get_full_name() or obj.username or "-"

    @display(description=_("Verified"))
    def verified_display(self, obj):
        """Display verification status with badge"""
        if obj.is_verified:
            return format_html(
                '<span style="background-color: #dcfce7; color: #16a34a; '
                'padding: 4px 8px; border-radius: 4px; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="background-color: #fee2e2; color: #dc2626; '
            'padding: 4px 8px; border-radius: 4px;">Unverified</span>'
        )

    @display(description=_("Active"))
    def active_display(self, obj):
        """Display active status with badge"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #dcfce7; color: #16a34a; '
                'padding: 4px 8px; border-radius: 4px; font-weight: bold;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #fee2e2; color: #dc2626; '
            'padding: 4px 8px; border-radius: 4px; font-weight: bold;">Inactive</span>'
        )

    @display(description=_("Staff"))
    def staff_display(self, obj):
        """Display staff status"""
        if obj.is_staff:
            return format_html(
                '<span style="background-color: #f3e8ff; color: #9333ea; '
                'padding: 4px 8px; border-radius: 4px; font-weight: 500;">Staff</span>'
            )
        return "-"

    # Actions
    actions = ["verify_users", "activate_users", "deactivate_users"]

    @action(
        description=_("Mark selected as verified"),
        permissions=["change"],
    )
    def verify_users(self, request: HttpRequest, queryset: QuerySet):
        """Verify selected users"""
        count = 0
        for user in queryset:
            user.verify_email()
            count += 1

        self.message_user(
            request,
            _("Verified {} user(s).").format(count),
            level=admin.messages.SUCCESS,
        )

    @action(
        description=_("Activate selected users"),
        permissions=["change"],
    )
    def activate_users(self, request: HttpRequest, queryset: QuerySet):
        """Activate selected users"""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            _("Activated {} user(s).").format(count),
            level=admin.messages.SUCCESS,
        )

    @action(
        description=_("Deactivate selected users"),
        permissions=["change"],
    )
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet):
        """Deactivate selected users"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            _("Deactivated {} user(s).").format(count),
            level=admin.messages.SUCCESS,
        )


# ===========================
# Audit Log Admin (Unfold-Compliant)
# ===========================

@admin.register(AuditLog)
class AuditLogAdmin(BaseModelAdmin):
    """
    Audit log admin with Unfold integration
    
    Inherits from BaseModelAdmin to get:
    - Unfold UI theming
    - Query optimization
    - Permission handling
    - Timestamp management
    
    Adds:
    - Read-only (immutable) audit log
    - Action display with color coding
    """

    model = AuditLog

    # List Display
    list_display = ["timestamp", "action_display", "user", "object_repr", "content_type"]

    # Filtering
    list_filter = ["action", "timestamp", "user", "content_type"]

    # Search
    search_fields = ["object_repr", "user__email", "object_id"]

    # Date Hierarchy
    date_hierarchy = "timestamp"
    
    ordering = ["-timestamp"]

    # All Readonly (Audit Trail is Immutable)
    readonly_fields = [
        "id",
        "action",
        "content_type",
        "object_id",
        "object_repr",
        "changes",
        "user",
        "ip_address",
        "user_agent",
        "timestamp",
    ]

    # Permissions
    def has_add_permission(self, request: HttpRequest) -> bool:
        """Prevent manual audit log creation"""
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Prevent editing audit logs"""
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """Only superusers can delete audit logs"""
        return request.user.is_superuser

    # Display Methods
    @display(description=_("Action"))
    def action_display(self, obj):
        """Display action with color coding"""
        colors = {
            "create": ("#dcfce7", "#16a34a"),      # Green
            "update": ("#bfdbfe", "#2563eb"),      # Blue
            "delete": ("#fee2e2", "#dc2626"),      # Red
            "restore": ("#fef3c7", "#d97706"),     # Amber
            "publish": ("#f3e8ff", "#9333ea"),     # Purple
        }

        bg_light, color = colors.get(obj.action, ("#f3f4f6", "#6b7280"))

        return format_html(
            '<span style="background-color: {bg}; color: {color}; '
            'padding: 4px 8px; border-radius: 4px; font-weight: 500;">{label}</span>',
            bg=bg_light,
            color=color,
            label=obj.get_action_display(),
        )