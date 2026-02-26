"""
Ultimate Django admin customization for unfold
Provides production-grade admin interface with:
- Advanced filtering
- Custom actions
- Bulk operations
- Audit logging
- Permission-based visibility
"""

from typing import List, Optional, Any, Dict, Tuple
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import QuerySet
from django.http import HttpRequest
from django.contrib.admin import widgets
from django.db import models
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display, action
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from django.contrib.admin.models import LogEntry

from common.models import CustomUser, AuditLog


# ===========================
# Custom Admin Base Classes (Unfold Compliant)
# ===========================

class BaseModelAdmin(ModelAdmin):
    """
    Base model admin with common functionality
    Fully compliant with django-unfold for consistent styling across all inheriting admins
    """

    # --- Unfold Required Configuration ---
    
    # Enable compressed form fields (Unfold feature)
    compressed_fields = True
    
    # Enable list fullscreen toggle
    list_fullscreen = True
    
    # Enable list filter submit button
    list_filter_submit = True
    
    # Preserve filters on back button
    preserve_filters = True
    
    # Enable warning before leaving unsaved form
    warn_unsaved_form = True
    
    # --- Display settings ---
    date_hierarchy = "created_at"
    list_per_page = 25
    list_max_show_all = 200
    search_help_text = "Search across key fields"

    # --- Common readonly fields ---
    readonly_fields = ["id", "created_at", "updated_at", "created_at_readonly", "updated_at_readonly"]
    
    # --- Fieldsets configuration (Unfold compatible) ---
    fieldsets: Tuple = ()
    
    # Additional fieldsets to extend
    fieldsets_extend: List = [
        (
            _("Timestamps"),
            {
                "fields": ("created_at_readonly", "updated_at_readonly"),
                "classes": ("collapse",),
            },
        ),
    ]
    
    # --- List configuration ---
    list_display = ["__str__", "id_display"]
    list_display_links = ["__str__"]
    
    # --- Actions configuration ---
    actions = []
    actions_detail = []  # Unfold: Actions on detail page
    
    # --- Unfold specific configurations ---
    
    # Custom templates for Unfold
    add_form_template = "admin/unfold/model/add.html"
    change_form_template = "admin/unfold/model/change.html"
    change_list_template = "admin/unfold/model/change_list.html"
    delete_confirmation_template = "admin/unfold/model/delete_confirmation.html"
    delete_selected_confirmation_template = "admin/unfold/model/delete_selected_confirmation.html"
    object_history_template = "admin/unfold/model/object_history.html"
    
    # Unfold tabs configuration
    tabs = []  # Add tabs for detail view
    
    # Unfold action buttons configuration
    actions_list = []   # Top toolbar actions
    actions_row = []    # Actions on each row in changelist
    actions_detail = [] # Actions on detail page
    
    # Unfold fieldset configuration
    fieldset_classes = {
        "collapse": "collapse",
        "wide": "wide",
    }

    # --- Display methods with Unfold @display decorator ---
    @display(
        description=_("ID"),
        ordering="id",
        label=True,
        label_color="gray",
    )
    def id_display(self, obj):
        """Display ID with badge styling"""
        return f"#{obj.id}"

    @display(
        description=_("Created"),
        ordering="created_at",
        header=True,  # Unfold: Show in header
    )
    def created_at_readonly(self, obj):
        """Readonly created_at display"""
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return "-"

    @display(
        description=_("Updated"),
        ordering="updated_at",
        header=True,
    )
    def updated_at_readonly(self, obj):
        """Readonly updated_at display"""
        if obj.updated_at:
            return obj.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        return "-"

    @display(
        description=_("Status"),
        ordering="is_active",
    )
    def status_display(self, obj):
        """Generic status display - override in child classes"""
        return "-"

    # --- Custom Unfold toolbar actions ---
    @action(description=_("Export selected"))
    def export_action(self, request: HttpRequest, queryset: QuerySet):
        """Example export action"""
        count = queryset.count()
        self.message_user(request, f"Would export {count} items (not implemented).")

    export_action.allowed_permissions = ['view']

    # --- Permission methods (Unfold compatible) ---
    def get_fieldsets(self, request: HttpRequest, obj=None):
        """Add timestamp fieldset"""
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets = list(fieldsets) if fieldsets else []
        
        # Add extended fieldsets if they exist and obj exists (for edit form)
        if hasattr(self, "fieldsets_extend") and self.fieldsets_extend:
            fieldsets.extend(self.fieldsets_extend)
            
        return fieldsets

    def get_readonly_fields(self, request: HttpRequest, obj=None):
        """Get readonly fields with Unfold compatibility"""
        readonly = list(super().get_readonly_fields(request, obj))
        
        if obj:  # Editing existing object
            readonly.extend(["id", "created_at", "updated_at"])
            
        return readonly

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related and prefetch_related"""
        qs = super().get_queryset(request)

        # Add select_related for foreign keys
        if hasattr(self, "select_related_fields") and self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)

        # Add prefetch_related for reverse relations
        if hasattr(self, "prefetch_related_fields") and self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)

        return qs

    def get_list_display(self, request: HttpRequest):
        """Get list display with Unfold compatibility"""
        list_display = super().get_list_display(request)
        
        # Ensure we don't have duplicates
        if "id_display" not in list_display and hasattr(self, "id_display"):
            list_display = list(list_display) + ["id_display"]
            
        return list_display

    def get_actions(self, request: HttpRequest):
        """Get actions with Unfold compatibility"""
        actions = super().get_actions(request)
        
        # Add custom actions if user has permissions
        if request.user.is_superuser:
            if "export_action" not in actions:
                actions["export_action"] = self.get_action("export_action")
                
        return actions

    # --- Permission checks (Unfold compatible) ---
    def has_add_permission(self, request: HttpRequest) -> bool:
        """Check add permission"""
        return request.user.is_staff

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Check change permission"""
        if obj is None:
            return request.user.is_staff
        return request.user.is_staff

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """Check delete permission - only superusers can delete"""
        return request.user.is_superuser

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        """Check view permission"""
        return request.user.is_staff

    def has_module_permission(self, request: HttpRequest) -> bool:
        """Check module permission"""
        return request.user.is_staff

    # --- Unfold-specific methods for better UX ---
    def get_extra_context(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Add extra context for Unfold templates
        This is crucial for Unfold styling to work properly
        """
        context = super().get_extra_context(request)
        
        # Add common context variables
        context.update({
            "site_title": _("Django Admin"),
            "site_header": _("Administration"),
            "title": self.get_admin_title(request),
        })
        
        return context

    def get_admin_title(self, request: HttpRequest) -> str:
        """Get admin title for current view"""
        opts = self.model._meta
        return f"{opts.app_config.verbose_name} - {opts.verbose_name_plural}"

    def get_form(self, request, obj=None, **kwargs):
        """Override form to ensure Unfold widgets are used"""
        form = super().get_form(request, obj, **kwargs)
        
        # Ensure all fields use Unfold-compatible widgets
        # This is automatically handled by Unfold when using ModelAdmin
        return form


class SoftDeleteModelAdmin(BaseModelAdmin):
    """Admin for models with soft delete - inherits Unfold styling from BaseModelAdmin"""

    list_display = ["__str__", "deleted_at_display", "is_deleted_display", "status_display"]
    list_filter = ["deleted_at", "is_deleted"]

    @display(
        description=_("Deleted At"),
        ordering="deleted_at",
        label=True,
        label_color="red",
    )
    def deleted_at_display(self, obj):
        """Display deleted timestamp"""
        if hasattr(obj, "deleted_at") and obj.deleted_at:
            return format_html(
                '<span style="color: red;">{}</span>',
                obj.deleted_at.strftime("%Y-%m-%d %H:%M"),
            )
        return "-"

    @display(
        description=_("Deleted"),
        ordering="is_deleted",
        boolean=True,
    )
    def is_deleted_display(self, obj):
        """Display deletion status as boolean"""
        return getattr(obj, "is_deleted", False)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Include deleted records for superusers"""
        qs = super().get_queryset(request)

        # If model has all_with_deleted method, use it for superusers
        if request.user.is_superuser and hasattr(qs, "all_with_deleted"):
            return qs.all_with_deleted()

        return qs

    # --- Unfold-compatible actions ---
    @action(description=_("Restore selected records"))
    def restore_deleted_records(self, request: HttpRequest, queryset: QuerySet):
        """Restore soft-deleted records"""
        count = 0
        for obj in queryset:
            if hasattr(obj, "restore"):
                obj.restore()
                count += 1
        self.message_user(request, f"Restored {count} record(s).")

    restore_deleted_records.allowed_permissions = ['change']

    # Add to actions list
    actions = BaseModelAdmin.actions + ["restore_deleted_records"]


class PublishableModelAdmin(BaseModelAdmin):
    """Admin for publishable models - inherits Unfold styling from BaseModelAdmin"""

    list_display = ["__str__", "status_display", "published_at_display"]
    list_filter = ["status", "published_at"]

    fieldsets_extend = BaseModelAdmin.fieldsets_extend + [
        (
            _("Publication"),
            {
                "fields": ("status", "published_at"),
                "classes": ("wide",),
            },
        ),
    ]

    @display(
        description=_("Status"),
        ordering="status",
    )
    def status_display(self, obj):
        """Display publication status with color coding"""
        if not hasattr(obj, "status"):
            return "-"
            
        colors = {
            "draft": "gray",
            "published": "green",
            "archived": "orange",
        }
        color = colors.get(obj.status, "gray")

        # Get status display if available
        if hasattr(obj, "get_status_display"):
            status_text = obj.get_status_display()
        else:
            status_text = obj.status.capitalize()

        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; color: white; '
            'border-radius: 3px; font-size: 0.85em;">{}</span>',
            color,
            status_text,
        )

    @display(
        description=_("Published At"),
        ordering="published_at",
        header=True,
    )
    def published_at_display(self, obj):
        """Display publication timestamp"""
        if hasattr(obj, "published_at") and obj.published_at:
            return obj.published_at.strftime("%Y-%m-%d %H:%M")
        return "-"

    # --- Unfold-compatible actions ---
    @action(description=_("Publish selected"))
    def publish_records(self, request: HttpRequest, queryset: QuerySet):
        """Publish selected records"""
        count = 0
        for obj in queryset:
            if hasattr(obj, "publish"):
                obj.publish()
                count += 1
        self.message_user(request, f"Published {count} record(s).")

    @action(description=_("Unpublish selected"))
    def unpublish_records(self, request: HttpRequest, queryset: QuerySet):
        """Unpublish selected records"""
        if hasattr(queryset, "update") and hasattr(queryset.model, "status"):
            count = queryset.update(status="draft")
            self.message_user(request, f"Unpublished {count} record(s).")

    @action(description=_("Archive selected"))
    def archive_records(self, request: HttpRequest, queryset: QuerySet):
        """Archive selected records"""
        if hasattr(queryset, "update") and hasattr(queryset.model, "status"):
            count = queryset.update(status="archived")
            self.message_user(request, f"Archived {count} record(s).")

    # Add to actions list
    actions = BaseModelAdmin.actions + [
        "publish_records",
        "unpublish_records",
        "archive_records"
    ]


# ===========================
# Custom User Admin (Unfold Compliant)
# ===========================

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    """
    Custom user admin with Unfold styling
    Inherits from both Django's BaseUserAdmin and Unfold's ModelAdmin
    """

    # --- Unfold Required Configuration ---
    compressed_fields = True
    list_fullscreen = True
    list_filter_submit = True
    preserve_filters = True
    warn_unsaved_form = True

    # --- ModelAdmin configuration ---
    model = CustomUser
    
    # --- Unfold forms (important for proper styling) ---
    add_form = UserCreationForm
    change_form = UserChangeForm
    change_password_form = AdminPasswordChangeForm

    # --- Fieldsets with Unfold styling ---
    fieldsets = (
        (None, {
            "fields": ("id", "email", "password", "username"),
            "classes": ("wide",),
        }),
        (
            _("Personal info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone_number",
                    "bio",
                    "avatar",
                ),
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
                "classes": ("wide",),
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

    # --- List display with Unfold @display decorators ---
    list_display = [
        "email",
        "username",
        "full_name",
        "verified_display",
        "active_display",
        "staff_display",
        "created_at_readonly",
    ]
    
    list_filter = ["is_verified", "is_active", "is_staff", "created_at"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "verified_at",
        "last_login_at",
        "created_at_readonly",
        "updated_at_readonly",
    ]

    # Performance optimizations
    select_related_fields = []
    prefetch_related_fields = ["groups", "user_permissions"]

    # --- Unfold display methods ---
    @display(
        description=_("Full Name"),
        ordering="first_name",
    )
    def full_name(self, obj):
        """Display full name"""
        return obj.get_full_name() or "-"

    @display(
        description=_("Verified"),
        ordering="is_verified",
        boolean=True,
        label={
            True: "success",
            False: "danger",
        },
    )
    def verified_display(self, obj):
        """Display verification status as boolean"""
        return obj.is_verified

    @display(
        description=_("Active"),
        ordering="is_active",
        boolean=True,
        label={
            True: "success",
            False: "danger",
        },
    )
    def active_display(self, obj):
        """Display active status as boolean"""
        return obj.is_active

    @display(
        description=_("Staff"),
        ordering="is_staff",
        boolean=True,
        label={
            True: "info",
            False: "gray",
        },
    )
    def staff_display(self, obj):
        """Display staff status as boolean"""
        return obj.is_staff

    @display(
        description=_("Created"),
        ordering="created_at",
        header=True,
    )
    def created_at_readonly(self, obj):
        """Display created timestamp"""
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M")
        return "-"

    @display(
        description=_("Updated"),
        ordering="updated_at",
    )
    def updated_at_readonly(self, obj):
        """Display updated timestamp"""
        if obj.updated_at:
            return obj.updated_at.strftime("%Y-%m-%d %H:%M")
        return "-"

    # --- Unfold actions ---
    @action(description=_("Verify selected users"))
    def verify_users(self, request: HttpRequest, queryset: QuerySet):
        """Verify selected users"""
        for user in queryset:
            if hasattr(user, "verify_email"):
                user.verify_email()
        self.message_user(request, f"Verified {queryset.count()} user(s).")

    @action(description=_("Activate selected users"))
    def activate_users(self, request: HttpRequest, queryset: QuerySet):
        """Activate selected users"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} user(s).")

    @action(description=_("Deactivate selected users"))
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet):
        """Deactivate selected users"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} user(s).")

    actions = ["verify_users", "activate_users", "deactivate_users"]

    # --- Permission methods ---
    def get_readonly_fields(self, request: HttpRequest, obj=None):
        """Get readonly fields"""
        readonly = list(super().get_readonly_fields(request, obj))
        
        if obj:  # Editing existing user
            readonly.extend(["id", "created_at", "updated_at"])
            
        return readonly

    def get_extra_context(self, request: HttpRequest) -> Dict[str, Any]:
        """Add extra context for Unfold templates"""
        context = super().get_extra_context(request)
        context.update({
            "site_title": _("User Administration"),
            "site_header": _("User Management"),
        })
        return context


# ===========================
# Audit Log Admin (Unfold Compliant)
# ===========================

@admin.register(AuditLog)
class AuditLogAdmin(BaseModelAdmin):
    """Audit log admin - inherits Unfold styling from BaseModelAdmin"""

    model = AuditLog
    
    # --- Unfold configuration ---
    compressed_fields = True
    list_fullscreen = True
    
    # --- List display ---
    list_display = [
        "timestamp",
        "action_display",
        "user_link",
        "object_repr",
        "ip_address",
    ]
    
    list_filter = ["action", "timestamp", "user", "content_type"]
    search_fields = ["object_repr", "user__email", "object_id", "ip_address"]
    date_hierarchy = "timestamp"
    
    # --- Readonly fields ---
    readonly_fields = [
        "id",
        "action",
        "content_type",
        "object_id",
        "object_repr",
        "changes_json",
        "user",
        "ip_address",
        "user_agent",
        "timestamp",
        "created_at_readonly",
    ]

    # Performance optimizations
    select_related_fields = ["user", "content_type"]
    prefetch_related_fields = []

    # --- Unfold display methods ---
    @display(
        description=_("Action"),
        ordering="action",
        label=True,
    )
    def action_display(self, obj):
        """Display action with color coding"""
        colors = {
            "create": "success",
            "update": "info",
            "delete": "danger",
            "restore": "warning",
            "publish": "purple",
        }
        
        if hasattr(obj, "get_action_display"):
            action_text = obj.get_action_display()
        else:
            action_text = obj.action.capitalize()
            
        return format_html(
            '<span class="bg-{}-100 text-{}-800 dark:bg-{}-900 dark:text-{}-300 px-2 py-1 rounded-full text-xs font-medium">'
            '{}</span>',
            colors.get(obj.action, "gray"),
            colors.get(obj.action, "gray"),
            colors.get(obj.action, "gray"),
            colors.get(obj.action, "gray"),
            action_text,
        )

    @display(
        description=_("User"),
        ordering="user__email",
    )
    def user_link(self, obj):
        """Link to user if exists"""
        if obj.user and obj.user_id:
            url = reverse(f"admin:{obj.user._meta.app_label}_{obj.user._meta.model_name}_change", 
                         args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return "-"

    @display(
        description=_("Changes"),
    )
    def changes_json(self, obj):
        """Display changes as formatted JSON"""
        if not obj.changes:
            return "-"
            
        import json
        try:
            formatted = json.dumps(obj.changes, indent=2, ensure_ascii=False)
            return format_html('<pre class="text-xs">{}</pre>', formatted)
        except:
            return str(obj.changes)

    # --- Permission overrides ---
    def has_add_permission(self, request: HttpRequest) -> bool:
        """Prevent manual creation"""
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Prevent editing"""
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """Only superuser can delete"""
        return request.user.is_superuser

    # --- Actions ---
    @action(description=_("Export selected logs"))
    def export_logs(self, request: HttpRequest, queryset: QuerySet):
        """Export selected audit logs"""
        count = queryset.count()
        self.message_user(request, f"Would export {count} logs (implement as CSV/JSON).")

    actions = ["export_logs"]


# ===========================
# Optional: Register LogEntry with Unfold styling
# ===========================

@admin.register(LogEntry)
class LogEntryAdmin(ModelAdmin):
    """Django's built-in LogEntry admin with Unfold styling"""
    
    model = LogEntry
    
    list_display = [
        "action_time",
        "user",
        "content_type",
        "object_repr",
        "action_flag_display",
        "change_message",
    ]
    
    list_filter = ["action_time", "user", "content_type", "action_flag"]
    search_fields = ["object_repr", "change_message"]
    date_hierarchy = "action_time"
    
    readonly_fields = ["action_time", "user", "content_type", "object_id", 
                       "object_repr", "action_flag", "change_message"]
    
    @display(
        description=_("Action Flag"),
        ordering="action_flag",
        label=True,
    )
    def action_flag_display(self, obj):
        """Display action flag with color"""
        colors = {
            1: "success",   # ADDITION
            2: "info",      # CHANGE
            3: "danger",    # DELETION
        }
        flags = {
            1: "Added",
            2: "Changed", 
            3: "Deleted",
        }
        
        color = colors.get(obj.action_flag, "gray")
        text = flags.get(obj.action_flag, "Unknown")
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 dark:bg-{}-900 dark:text-{}-300 px-2 py-1 rounded-full text-xs font-medium">'
            '{}</span>',
            color, color, color, color, text
        )
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
    
    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return request.user.is_superuser