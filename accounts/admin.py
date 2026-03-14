from django.contrib import admin
from common.unfold_admin_bases import BaseAdmin
from unfold.contrib.filters.admin import RangeDateTimeFilter, BooleanRadioFilter
from unfold.decorators import display

from .models import OTPRecord, PasswordResetToken, UserPreferences

@admin.register(OTPRecord)
class OTPRecordAdmin(BaseAdmin):
    list_display = ["user_display", "type_badge", "otp", "attempts", "is_used_badge", "expires_at", "created_at"]
    list_filter = [
        "type", 
        ("is_used", BooleanRadioFilter), 
        ("expires_at", RangeDateTimeFilter),
        ("created_at", RangeDateTimeFilter)
    ]
    search_fields = ["user__email", "user__username", "otp"]
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]

    @display(description="User", ordering="user__email")
    def user_display(self, obj):
        return obj.user.email
    
    @display(description="Type", ordering="type")
    def type_badge(self, obj):
        return self.badge(obj.get_type_display(), "purple")

    @display(description="Status", ordering="is_used")
    def is_used_badge(self, obj):
        if obj.is_used:
            return self.badge("Used", "green")
        return self.badge("Pending", "yellow")


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(BaseAdmin):
    list_display = ["user_display", "id", "is_used_badge", "expires_at", "created_at"]
    list_filter = [
        ("is_used", BooleanRadioFilter), 
        ("expires_at", RangeDateTimeFilter),
        ("created_at", RangeDateTimeFilter)
    ]
    search_fields = ["user__email", "user__username", "id"]
    autocomplete_fields = ["user"]
    readonly_fields = ["id", "created_at", "updated_at"]

    @display(description="User", ordering="user__email")
    def user_display(self, obj):
        return obj.user.email
    
    @display(description="Status", ordering="is_used")
    def is_used_badge(self, obj):
        if obj.is_used:
            return self.badge("Used", "green")
        return self.badge("Pending", "yellow")


@admin.register(UserPreferences)
class UserPreferencesAdmin(BaseAdmin):
    list_display = ["user_display", "job_types_display", "created_at", "updated_at"]
    search_fields = ["user__email", "user__username", "job_titles", "locations"]
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]

    @display(description="User", ordering="user__email")
    def user_display(self, obj):
        return obj.user.email

    @display(description="Job Types")
    def job_types_display(self, obj):
        if not obj.job_types:
            return "-"
        return ", ".join(str(job) for job in obj.job_types)
