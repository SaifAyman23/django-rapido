"""
Simple Unfold Admin Base Classes
=================================

Clean, practical admin classes with Unfold integration.
Less complexity, fewer errors, easier to maintain.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.admin import StackedInline, TabularInline
from unfold.decorators import display, action


# ===========================
# Base Admin
# ===========================

class BaseAdmin(UnfoldModelAdmin):
    """
    Simple base admin with common settings.
    
    Usage:
        @admin.register(MyModel)
        class MyModelAdmin(BaseAdmin):
            list_display = ["name", "created_at"]
    """
    
    # Display
    list_per_page = 25
    list_fullwidth = True
    
    # Default fields
    list_display = ["__str__", "created_at"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    
    # Actions
    actions_selection_counter = True
    
    # Helper for colored badges
    def badge(self, text: str, color: str = "gray") -> str:
        """Create colored badge"""
        colors = {
            "green": ("#dcfce7", "#16a34a"),
            "red": ("#fee2e2", "#dc2626"),
            "blue": ("#bfdbfe", "#2563eb"),
            "yellow": ("#fef3c7", "#d97706"),
            "purple": ("#f3e8ff", "#9333ea"),
            "gray": ("#f3f4f6", "#6b7280"),
        }
        bg, fg = colors.get(color, colors["gray"])
        return format_html(
            '<span style="background: {}; color: {}; '
            'padding: 4px 8px; border-radius: 4px; font-weight: 500;">{}</span>',
            bg, fg, text
        )


# ===========================
# Read-Only Admin
# ===========================

class ReadOnlyAdmin(BaseAdmin):
    """
    Admin for logs and immutable records.
    
    Usage:
        @admin.register(AuditLog)
        class AuditLogAdmin(ReadOnlyAdmin):
            list_display = ["timestamp", "action", "user"]
    """
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
    
    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return request.user.is_superuser


# ===========================
# Soft Delete Admin
# ===========================

class SoftDeleteAdmin(BaseAdmin):
    """
    Admin for models with soft delete (is_deleted field).
    
    Usage:
        @admin.register(Article)
        class ArticleAdmin(SoftDeleteAdmin):
            list_display = ["title", "is_deleted_badge"]
    """
    
    list_display = ["__str__", "is_deleted_badge", "created_at"]
    list_filter = ["is_deleted"]
    actions = ["restore_items"]
    
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Show all items to superusers, only active to others"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser and hasattr(qs, "active"):
            return qs.active()
        return qs
    
    @display(description="Status", ordering="is_deleted")
    def is_deleted_badge(self, obj) -> str:
        """Show deletion status"""
        if obj.is_deleted:
            return self.badge("Deleted", "red")
        return self.badge("Active", "green")
    
    @action(description="Restore deleted items")
    def restore_items(self, request: HttpRequest, queryset: QuerySet):
        """Restore soft-deleted items"""
        if hasattr(queryset, "restore"):
            count = queryset.restore()
        else:
            count = queryset.update(is_deleted=False, deleted_at=None)
        self.message_user(request, f"Restored {count} item(s)")


# ===========================
# User Admin
# ===========================

class BaseUserAdmin(BaseAdmin, DjangoUserAdmin):
    """
    Enhanced user admin with Unfold styling.
    
    Usage:
        @admin.register(CustomUser)
        class CustomUserAdmin(BaseUserAdmin):
            list_display = ["email", "username", "is_active"]
    """
    
    list_display = ["username", "email", "is_active", "is_staff", "date_joined"]
    list_filter = ["is_active", "is_staff", "is_superuser", "groups"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize user queries"""
        return super().get_queryset(request).prefetch_related("groups", "user_permissions")


# ===========================
# Group Admin
# ===========================

class BaseGroupAdmin(BaseAdmin, DjangoGroupAdmin):
    """
    Enhanced group admin with Unfold styling.
    
    Usage:
        @admin.register(Group)
        class GroupAdmin(BaseGroupAdmin):
            pass
    """
    
    list_display = ["name", "permission_count"]
    search_fields = ["name"]
    
    # Remove inherited fields that cause issues
    date_hierarchy = None
    readonly_fields = []
    
    @display(description="Permissions")
    def permission_count(self, obj) -> str:
        count = obj.permissions.count()
        return f"{count}"


# ===========================
# Inline Classes
# ===========================

class BaseTabularInline(TabularInline):
    """Simple tabular inline"""
    extra = 1


class BaseStackedInline(StackedInline):
    """Simple stacked inline"""
    extra = 1
    classes = ["collapse"]