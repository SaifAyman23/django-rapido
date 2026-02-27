"""
CustomUser Admin - Simplified Example
======================================

Clean implementation using simplified base classes.
"""

from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import QuerySet
from django.http import HttpRequest

from unfold.contrib.filters.admin import (
    BooleanRadioFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
    RelatedCheckboxFilter,
    TextFilter,
)
from unfold.decorators import display, action

from .unfold_admin_bases import (
    BaseUserAdmin,
    BaseGroupAdmin,
    ReadOnlyAdmin,
)
from common.models import CustomUser, AuditLog


# ===========================
# CustomUser Admin
# ===========================

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Custom user admin with Unfold integration.
    
    Features:
    - Email/username display
    - Verification badges
    - 2FA status
    - Bulk actions
    - Query optimization
    """
    
    # List Display
    list_display = [
        "email",
        "username",
        "full_name",
        "verified_badge",
        "is_active",
        "is_staff",
        "date_joined",
    ]
    
    # Filtering
    list_filter = [
        ("is_verified", BooleanRadioFilter),
        ("two_factor_enabled", BooleanRadioFilter),
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
        ("groups", RelatedCheckboxFilter),
        ("created_at", RangeDateFilter),
    ]
    
    # Search
    search_fields = [
        "email",
        "username",
        "first_name",
        "last_name",
        "phone_number",
    ]
    
    # Fields
    fieldsets = (
        (None, {
            "fields": ("username", "password", "email")
        }),
        ("Personal Info", {
            "fields": ("first_name", "last_name", "phone_number", "avatar", "bio"),
        }),
        ("Verification", {
            "fields": ("is_verified", "verification_token"),
            "classes": ("collapse",),
        }),
        ("Security", {
            "fields": ("two_factor_enabled",),
            "classes": ("collapse",),
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "verified_at", "last_login_at"),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = [
        "created_at",
        "updated_at",
        "verified_at",
        "last_login_at",
    ]
    
    # Actions
    actions = [
        "verify_users",
        "unverify_users",
        "activate_users",
        "deactivate_users",
    ]
    
    # Display Methods
    
    @display(description="Full Name")
    def full_name(self, obj: CustomUser) -> str:
        """Show full name or username"""
        name = obj.get_full_name()
        return name if name else obj.username or "-"
    
    @display(description="Verified", ordering="is_verified")
    def verified_badge(self, obj: CustomUser) -> str:
        """Show verification status"""
        if obj.is_verified:
            return self.badge("✓ Verified", "green")
        return self.badge("Unverified", "red")
    
    # Actions
    
    @action(description="Mark as verified")
    def verify_users(self, request: HttpRequest, queryset: QuerySet):
        """Verify selected users"""
        count = 0
        for user in queryset:
            if not user.is_verified and hasattr(user, "verify_email"):
                user.verify_email()
                count += 1
        self.message_user(request, f"Verified {count} user(s)")
    
    @action(description="Mark as unverified")
    def unverify_users(self, request: HttpRequest, queryset: QuerySet):
        count = queryset.update(is_verified=False)
        self.message_user(request, f"Unverified {count} user(s)")
    
    @action(description="Activate selected users")
    def activate_users(self, request: HttpRequest, queryset: QuerySet):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} user(s)")
    
    @action(description="Deactivate selected users")
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} user(s)")


# ===========================
# Group Admin
# ===========================

admin.site.unregister(Group)

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    """Enhanced group admin"""
    
    ordering = []


# ===========================
# AuditLog Admin
# ===========================

@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdmin):
    """
    Audit log admin - read-only records.
    
    Features:
    - Color-coded actions
    - Advanced filtering
    - User/object search
    - Immutable records
    """
    
    # List Display
    list_display = [
        "timestamp_display",
        "action_badge",
        "user_display",
        "object_display",
    ]
    
    list_per_page = 50
    
    # Filtering
    list_filter = [
        ("timestamp", RangeDateTimeFilter),
        ("user", RelatedCheckboxFilter),
    ]
    
    # Search
    search_fields = [
        "object_repr",
        "user__email",
        "user__username",
        "object_id",
    ]
    
    # Ordering
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]
    
    # Fields
    fieldsets = (
        ("Action", {
            "fields": ("timestamp", "action", "user")
        }),
        ("Object", {
            "fields": ("content_type", "object_id", "object_repr"),
        }),
        ("Changes", {
            "fields": ("changes_display",),
            "classes": ("collapse",),
        }),
        ("Request Info", {
            "fields": ("ip_address", "user_agent"),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = [
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
    
    # Query Optimization
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("user")
    
    # Display Methods
    
    @display(description="Time", ordering="timestamp")
    def timestamp_display(self, obj: AuditLog) -> str:
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    @display(description="Action", ordering="action")
    def action_badge(self, obj: AuditLog) -> str:
        """Show action with color coding"""
        colors = {
            "create": "green",
            "update": "blue",
            "delete": "red",
            "restore": "yellow",
            "publish": "purple",
        }
        color = colors.get(obj.action, "gray")
        label = obj.get_action_display() if hasattr(obj, "get_action_display") else obj.action
        return self.badge(label.title(), color)
    
    @display(description="User", ordering="user__email")
    def user_display(self, obj: AuditLog) -> str:
        """Show user info"""
        if not obj.user:
            return "-"
        name = obj.user.get_full_name()
        if name:
            return f"{name} ({obj.user.email})"
        return obj.user.email or obj.user.username or "-"
    
    @display(description="Object")
    def object_display(self, obj: AuditLog) -> str:
        """Show object info"""
        model = obj.content_type.model.title()
        return f"{model} #{obj.object_id}"
    
    @display(description="Changes")
    def changes_display(self, obj: AuditLog) -> str:
        """Show formatted changes"""
        import json
        
        if not obj.changes:
            return "-"
        
        try:
            if isinstance(obj.changes, str):
                changes = json.loads(obj.changes)
            else:
                changes = obj.changes
            
            formatted = json.dumps(changes, indent=2, ensure_ascii=False)
            return format_html(
                '<pre style="background: #f3f4f6; padding: 12px; '
                'border-radius: 4px; font-family: monospace; '
                'font-size: 12px; overflow-x: auto;">{}</pre>',
                formatted
            )
        except (json.JSONDecodeError, TypeError):
            return str(obj.changes)