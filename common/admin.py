"""
CustomUser Admin - Simplified Example
======================================

Clean implementation using simplified base classes.
"""

from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

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
from django.contrib.admin.models import LogEntry


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

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
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



@admin.register(LogEntry)
class LogEntryAdmin(ReadOnlyAdmin):
    """
    Django admin log - read-only records from django_admin_log table.
    
    Features:
    - Track all admin actions
    - User activity monitoring
    - Object change history
    - Immutable records
    """
    
    # List Display
    list_display = [
        "action_time_display",
        "user_link",
        "content_type_display",
        "object_link",
        "action_flag_display",
        "change_message_short",
    ]
    
    list_per_page = 50
    
    # Filtering
    list_filter = [
        ("action_flag", admin.ChoicesFieldListFilter),
        ("content_type", RelatedCheckboxFilter),
        ("action_time", RangeDateTimeFilter),
        ("user", RelatedCheckboxFilter),
    ]
    
    # Search
    search_fields = [
        "object_repr",
        "change_message",
        "user__username",
        "user__email",
    ]
    
    # Ordering
    date_hierarchy = "action_time"
    ordering = ["-action_time"]
    
    # Fields
    fieldsets = (
        ("Basic Info", {
            "fields": ("action_time", "user", "action_flag")
        }),
        ("Object", {
            "fields": ("content_type", "object_id", "object_repr"),
        }),
        ("Change Details", {
            "fields": ("change_message_display",),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = [
        "action_time",
        "user",
        "content_type",
        "object_id",
        "object_repr",
        "action_flag",
        "change_message_display",
    ]
    
    # Query Optimization
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            "user", 
            "content_type"
        )
    
    # Display Methods
    
    @display(description="Time", ordering="action_time")
    def action_time_display(self, obj: LogEntry) -> str:
        """Format timestamp for display"""
        return obj.action_time.strftime("%Y-%m-%d %H:%M:%S")
    
    @display(description="User", ordering="user__username")
    def user_link(self, obj: LogEntry) -> str:
        """Show user with link"""
        if not obj.user:
            return self.badge("System", "gray")
        
        # Try to link to user (works with both auth.User and CustomUser)
        user_model = obj.user._meta.model_name
        app_label = obj.user._meta.app_label
        
        return format_html(
            '<a href="{}" style="text-decoration: none;">{}</a>',
            f"/admin/{app_label}/{user_model}/{obj.user.id}/change/",
            self.badge(str(obj.user), "blue")
        )
    
    @display(description="Content Type")
    def content_type_display(self, obj: LogEntry) -> str:
        """Show content type with app label"""
        if not obj.content_type:
            return "-"
        return f"{obj.content_type.app_label}.{obj.content_type.model}"
    
    @display(description="Object")
    def object_link(self, obj: LogEntry) -> str:
        """Show object with link if possible"""
        if not obj.content_type or not obj.object_id:
            return obj.object_repr or "-"
        
        try:
            # Try to create link to the object
            app_label = obj.content_type.app_label
            model = obj.content_type.model
            return format_html(
                '<a href="{}" style="text-decoration: none;">{}</a>',
                f"/admin/{app_label}/{model}/{obj.object_id}/change/",
                self.badge(obj.object_repr[:50], "green")
            )
        except:
            return obj.object_repr or "-"
    
    @display(description="Action", ordering="action_flag")
    def action_flag_display(self, obj: LogEntry) -> str:
        """Show action flag with color coding"""
        colors = {
            1: "green",   # ADDITION
            2: "blue",    # CHANGE
            3: "red",     # DELETION
        }
        labels = {
            1: "Added",
            2: "Changed", 
            3: "Deleted",
        }
        color = colors.get(obj.action_flag, "gray")
        label = labels.get(obj.action_flag, f"Unknown ({obj.action_flag})")
        
        return self.badge(label, color)
    
    @display(description="Message")
    def change_message_short(self, obj: LogEntry) -> str:
        """Short version of change message"""
        if not obj.change_message:
            return "-"
        return obj.change_message[:50] + "..." if len(obj.change_message) > 50 else obj.change_message
    
    @display(description="Full Message")
    def change_message_display(self, obj: LogEntry) -> str:
        """Show formatted change message"""
        if not obj.change_message:
            return "-"
        
        try:
            # Try to parse as JSON for pretty display
            import json
            if obj.change_message.startswith('[') or obj.change_message.startswith('{'):
                parsed = json.loads(obj.change_message)
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background: #f3f4f6; padding: 12px; '
                    'border-radius: 4px; font-family: monospace; '
                    'font-size: 12px; overflow-x: auto;">{}</pre>',
                    formatted
                )
        except:
            pass
        
        # Plain text display
        return format_html(
            '<pre style="background: #f3f4f6; padding: 12px; '
            'border-radius: 4px; font-family: monospace; '
            'font-size: 12px; overflow-x: auto;">{}</pre>',
            obj.change_message
        )
    
    # Permissions
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
    
    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return request.user.is_superuser


        