"""
CustomUser Admin Implementation
=================================

Example of how to implement CustomUserAdmin using the reusable
Unfold admin base classes.

This shows the best practices combining:
1. BaseModelAdmin features (query optimization, permissions, timestamps)
2. Django's BaseUserAdmin functionality
3. Unfold UI theming and styling
4. Custom display decorators with color coding
5. Bulk action framework
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from unfold.contrib.filters.admin import (
    BooleanRadioFilter,
    RangeDateFilter,
    RelatedCheckboxFilter,
    ChoicesCheckboxFilter,
    TextFilter,
    RangeDateTimeFilter,
)
from unfold.decorators import display, action

from .unfold_admin_bases import BaseUserAdmin, ReadOnlyModelAdmin
from common.models import CustomUser, AuditLog


# ===========================
# Custom Filters
# ===========================

class VerifiedFilter(BooleanRadioFilter):
    """Filter users by verification status"""
    title = "Verified"
    parameter_name = "is_verified"


class TwoFactorFilter(BooleanRadioFilter):
    """Filter users by 2FA status"""
    title = "2FA Enabled"
    parameter_name = "two_factor_enabled"


class ActiveFilter(BooleanRadioFilter):
    """Filter users by active status"""
    title = "Active"
    parameter_name = "is_active"


class StaffFilter(BooleanRadioFilter):
    """Filter users by staff status"""
    title = "Staff"
    parameter_name = "is_staff"


# ===========================
# CustomUser Admin
# ===========================

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Custom user admin with full Unfold integration.

    Inherits from BaseUserAdmin which provides:
    ✓ All BaseModelAdmin features
    ✓ Django's UserAdmin functionality
    ✓ Query optimization (select_related, prefetch_related)
    ✓ Permission handling
    ✓ Timestamp management
    ✓ Display helpers

    Features:
    - Email/username/full name display
    - Verification status with badge
    - 2FA status indicator
    - Active/staff/superuser badges
    - Advanced filtering
    - Bulk actions (verify, activate, deactivate)
    - Custom fieldsets with tabs
    - Query optimization
    """

    # ===========================
    # List Configuration
    # ===========================

    list_display = [
        "email_display",
        "username",
        "full_name",
        "verified_display",
        "two_factor_display",
        "active_display",
        "staff_display",
        "created_at",
    ]

    list_per_page = 25
    list_fullwidth = True

    # ===========================
    # Filtering
    # ===========================

    list_filter = [
        ("is_verified", VerifiedFilter),
        ("two_factor_enabled", TwoFactorFilter),
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
        ("groups", RelatedCheckboxFilter),
        ("created_at", RangeDateFilter),
        ("verified_at", RangeDateFilter),
    ]

    # ===========================
    # Search
    # ===========================

    search_fields = [
        "email",
        "username",
        "first_name",
        "last_name",
        "phone_number",
    ]

    # ===========================
    # Field Organization
    # ===========================

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "username",
                    "password",
                    "email",
                ),
            },
        ),
        (
            "Personal Info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone_number",
                    "avatar",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "Biography",
            {
                "fields": ("bio",),
                "classes": ("tab",),
                "description": "User biography and about information",
            },
        ),
        (
            "Verification",
            {
                "fields": (
                    "is_verified",
                    "verification_token",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "Security",
            {
                "fields": (
                    "two_factor_enabled",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "verified_at",
                    "last_login_at",
                ),
                "classes": ("collapse",),
                "description": "Automatically managed timestamps",
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                ),
                "description": "Create a new user account",
            },
        ),
    )

    # ===========================
    # Readonly Fields
    # ===========================

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "verified_at",
        "last_login_at",
    ]

    # ===========================
    # Query Optimization
    # ===========================

    select_related_fields = []
    prefetch_related_fields = [
        "groups",
        "user_permissions",
    ]

    # ===========================
    # Actions
    # ===========================

    actions = [
        "verify_users",
        "unverify_users",
        "activate_users",
        "deactivate_users",
        "make_staff",
        "remove_staff",
    ]

    # ===========================
    # Display Methods
    # ===========================

    @display(description="Email")
    def email_display(self, obj: CustomUser) -> str:
        """Display email address"""
        return obj.email or "-"

    @display(description="Full Name")
    def full_name(self, obj: CustomUser) -> str:
        """Display user's full name or fallback to username"""
        full = obj.get_full_name()
        return full if full else (obj.username or "-")

    @display(description="Verified")
    def verified_display(self, obj: CustomUser) -> str:
        """Display verification status with badge"""
        if obj.is_verified:
            return self.badge(
                "✓ Verified",
                color="#16a34a",
                bg_color="#dcfce7",
            )
        return self.badge(
            "Unverified",
            color="#dc2626",
            bg_color="#fee2e2",
        )

    @display(description="2FA")
    def two_factor_display(self, obj: CustomUser) -> str:
        """Display 2FA status"""
        if obj.two_factor_enabled:
            return self.badge(
                "Enabled",
                color="#16a34a",
                bg_color="#dcfce7",
            )
        return "-"

    @display(description="Active")
    def active_display(self, obj: CustomUser) -> str:
        """Display active status"""
        if obj.is_active:
            return self.badge(
                "Active",
                color="#16a34a",
                bg_color="#dcfce7",
            )
        return self.badge(
            "Inactive",
            color="#dc2626",
            bg_color="#fee2e2",
        )

    @display(description="Staff")
    def staff_display(self, obj: CustomUser) -> str:
        """Display staff status"""
        if obj.is_staff:
            return self.badge(
                "Staff",
                color="#9333ea",
                bg_color="#f3e8ff",
            )
        return "-"

    # ===========================
    # Actions - Verification
    # ===========================

    @action(
        description="Mark selected users as verified",
        permissions=["change"],
    )
    def verify_users(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Verify selected users"""
        count = 0
        for user in queryset:
            if not user.is_verified:
                user.verify_email()
                count += 1

        self.message_user_success(
            request,
            f"Verified {count} user(s).",
        )

    @action(
        description="Mark selected users as unverified",
        permissions=["change"],
    )
    def unverify_users(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Unverify selected users"""
        count = queryset.update(is_verified=False)
        self.message_user_success(
            request,
            f"Unverified {count} user(s).",
        )

    # ===========================
    # Actions - Status
    # ===========================

    @action(
        description="Activate selected users",
        permissions=["change"],
    )
    def activate_users(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Activate selected users"""
        count = queryset.update(is_active=True)
        self.message_user_success(
            request,
            f"Activated {count} user(s).",
        )

    @action(
        description="Deactivate selected users",
        permissions=["change"],
    )
    def deactivate_users(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Deactivate selected users"""
        count = queryset.update(is_active=False)
        self.message_user_success(
            request,
            f"Deactivated {count} user(s).",
        )

    # ===========================
    # Actions - Permissions
    # ===========================

    @action(
        description="Make selected users staff",
        permissions=["change"],
    )
    def make_staff(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Make selected users staff"""
        count = queryset.update(is_staff=True)
        self.message_user_success(
            request,
            f"Made {count} user(s) staff.",
        )

    @action(
        description="Remove staff from selected users",
        permissions=["change"],
    )
    def remove_staff(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Remove staff from selected users"""
        count = queryset.update(is_staff=False)
        self.message_user_success(
            request,
            f"Removed staff from {count} user(s).",
        )

    # ===========================
    # Permissions
    # ===========================

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: CustomUser = None,
    ) -> bool:
        """Only superusers can delete users"""
        return request.user.is_superuser

    # ===========================
    # Custom Methods
    # ===========================

    def get_form(self, request, obj=None, **kwargs):
        """Customize form"""
        form = super().get_form(request, obj, **kwargs)
        
        # Make email required on creation
        if obj is None:
            form.base_fields["email"].required = True
        
        return form

    def save_model(self, request, obj, form, change):
        """Track who created/modified the user"""
        if not change:
            # Creating new user
            obj.created_by = request.user
        else:
            # Modifying existing user
            obj.modified_by = request.user
        
        super().save_model(request, obj, form, change)

# ===========================
# Optional: Group Admin
# ===========================

from .unfold_admin_bases import GroupAdmin

admin.site.unregister(Group)

@admin.register(Group)
class GroupAdminEnhanced(GroupAdmin):
    """
    Enhanced group admin with Unfold integration.

    Inherits from GroupAdmin (which extends BaseModelAdmin)
    to get all standard features plus Django's GroupAdmin.
    """

    list_display = [
        "name",
        "permission_count",
    ]

    search_fields = ["name"]
    
    ordering = []

    fieldsets = (
        (
            None,
            {"fields": ("name",)},
        ),
        (
            "Permissions",
            {
                "fields": ("permissions",),
                "classes": ("collapse",),
            },
        ),
    )

    date_hierarchy = None

    readonly_fields = []
    
    filter_horizontal = ("permissions",)

    @display(description="Permissions")
    def permission_count(self, obj) -> str:
        """Display permission count"""
        count = obj.permissions.count()
        return f"{count} permission(s)"


# ===========================
# Custom Filters for AuditLog
# ===========================

class ActionFilter(ChoicesCheckboxFilter):
    """Filter audit logs by action type"""
    title = "Action"
    parameter_name = "action"


class UserEmailFilter(TextFilter):
    """Filter audit logs by user email"""
    title = "User Email"
    parameter_name = "user__email__icontains"


# ===========================
# AuditLogAdmin
# ===========================

@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyModelAdmin):
    """
    Audit log admin with read-only, immutable records.

    Inherits from ReadOnlyModelAdmin which provides:
    ✓ No add/change permissions (immutable)
    ✓ Only superusers can delete
    ✓ All BaseModelAdmin features
    ✓ Query optimization
    ✓ Timestamp management
    ✓ Permission handling

    Features:
    - Color-coded action display
    - Advanced filtering (action, user, date, type)
    - Email-based user search
    - Date-based filtering
    - Object representation display
    - All fields readonly
    - Optimized queries
    - Change details view
    - JSON changes display
    """

    # ===========================
    # List Configuration
    # ===========================

    list_display = [
        "timestamp_display",
        "action_display",
        "user_display",
        "object_display",
        "content_type",
    ]

    list_per_page = 50
    list_fullwidth = True

    # ===========================
    # Filtering
    # ===========================

    list_filter = [
        ("action", ActionFilter),
        ("timestamp", RangeDateTimeFilter),
        ("user", RelatedCheckboxFilter),
        ("content_type", RelatedCheckboxFilter),
        UserEmailFilter,
    ]

    # ===========================
    # Search
    # ===========================

    search_fields = [
        "object_repr",
        "user__email",
        "user__username",
        "object_id",
        "changes",
    ]

    # ===========================
    # Ordering & Hierarchy
    # ===========================

    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]

    # ===========================
    # Field Organization
    # ===========================

    fieldsets = (
        (
            "Action Info",
            {
                "fields": (
                    "timestamp",
                    "action",
                    "user",
                ),
            },
        ),
        (
            "Object",
            {
                "fields": (
                    "content_type",
                    "object_id",
                    "object_repr",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "Changes",
            {
                "fields": ("changes_display",),
                "classes": ("tab", "collapse"),
                "description": "JSON representation of changes made",
            },
        ),
        (
            "Request",
            {
                "fields": (
                    "ip_address",
                    "user_agent",
                ),
                "classes": ("tab", "collapse"),
                "description": "Request information",
            },
        ),
        (
            "System",
            {
                "fields": ("id",),
                "classes": ("collapse",),
            },
        ),
    )

    # ===========================
    # Readonly Fields
    # ===========================

    readonly_fields = [
        "id",
        "timestamp",
        "action",
        "user",
        "content_type",
        "object_id",
        "object_repr",
        "changes_display",
        "ip_address",
        "user_agent",
    ]

    # ===========================
    # Query Optimization
    # ===========================

    select_related_fields = [
        "user",
        "content_type",
    ]
    prefetch_related_fields = []

    # ===========================
    # Display Methods
    # ===========================

    @display(
        description="Timestamp",
        ordering="timestamp",
    )
    def timestamp_display(self, obj: AuditLog) -> str:
        """Display timestamp with formatting"""
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @display(
        description="Action",
        ordering="action",
    )
    def action_display(self, obj: AuditLog) -> str:
        """Display action with color coding"""
        colors = {
            "create": ("#16a34a", "#dcfce7"),      # Green
            "update": ("#2563eb", "#bfdbfe"),      # Blue
            "delete": ("#dc2626", "#fee2e2"),      # Red
            "restore": ("#d97706", "#fef3c7"),     # Amber
            "publish": ("#9333ea", "#f3e8ff"),     # Purple
        }

        color, bg = colors.get(obj.action, ("#6b7280", "#f3f4f6"))

        return format_html(
            '<span style="background-color: {bg}; color: {color}; '
            'padding: 4px 8px; border-radius: 4px; font-weight: 500;">{label}</span>',
            bg=bg,
            color=color,
            label=obj.get_action_display(),
        )

    @display(
        description="User",
        ordering="user__email",
    )
    def user_display(self, obj: AuditLog) -> str:
        """Display user information"""
        if obj.user:
            full_name = obj.user.get_full_name()
            if full_name:
                return f"{full_name} ({obj.user.email})"
            return obj.user.email or obj.user.username or "-"
        return "-"

    @display(
        description="Object",
        ordering="object_repr",
    )
    def object_display(self, obj: AuditLog) -> str:
        """Display object information"""
        return f"{obj.content_type.model.title()} #{obj.object_id}"

    @display(description="Changes")
    def changes_display(self, obj: AuditLog) -> str:
        """Display changes in formatted JSON"""
        import json
        
        if not obj.changes:
            return "-"
        
        try:
            changes = json.loads(obj.changes) if isinstance(obj.changes, str) else obj.changes
            # Format as readable JSON
            formatted = json.dumps(changes, indent=2, ensure_ascii=False)
            return format_html(
                '<pre style="background-color: #f3f4f6; padding: 12px; '
                'border-radius: 4px; overflow-x: auto; '
                'font-family: monospace; font-size: 12px;">{}</pre>',
                formatted,
            )
        except (json.JSONDecodeError, TypeError):
            return obj.changes or "-"

    # ===========================
    # Permissions (Inherited from ReadOnlyModelAdmin)
    # ===========================

    # No need to override - ReadOnlyModelAdmin already provides:
    # - has_add_permission() → False
    # - has_change_permission() → False
    # - has_delete_permission() → only superuser

    # ===========================
    # Custom Methods
    # ===========================

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        Optimize queryset for audit logs.
        
        Use select_related for ForeignKey fields.
        """
        qs = super().get_queryset(request)
        
        # Already handled by select_related_fields
        # But can add additional optimizations here if needed
        return qs

    def changelist_view(self, request, extra_context=None):
        """Add custom context to changelist view"""
        extra_context = extra_context or {}
        
        # Add total audit log count
        extra_context["total_logs"] = AuditLog.objects.count()
        
        return super().changelist_view(request, extra_context=extra_context)