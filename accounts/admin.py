"""REUSE: Admin for OTP models — optional, register if using verification flow."""

from django.contrib import admin

from common.unfold_admin_bases import BaseAdmin

from .models import OTPRecord, PasswordResetToken


@admin.register(OTPRecord)
class OTPRecordAdmin(BaseAdmin):
    """REUSE: Generic OTP admin — no role logic."""

    list_display = ["user", "otp", "type", "is_used", "attempts", "expires_at", "created_at"]
    list_filter = ["type", "is_used"]
    search_fields = ["user__email", "otp"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(BaseAdmin):
    list_display = ["user", "is_used", "attempts", "expires_at", "created_at"]
    list_filter = ["is_used"]
    search_fields = ["user__email", "token"]
    readonly_fields = ["created_at", "updated_at"]
