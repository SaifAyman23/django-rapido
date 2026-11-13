"""Admin for role Accounts and email OTPs."""

from django.contrib import admin
from unfold.decorators import display

from common.unfold_admin_bases import BaseAdmin, ReadOnlyAdmin

from .models import Account, EmailOTP, SocialAccountLink


@admin.register(Account)
class AccountAdmin(BaseAdmin):
    """Role accounts — the authorization and data boundary."""

    list_display = [
        "email",
        "user",
        "role",
        "email_verified_badge",
        "is_active",
        "profile_state",
        "created_at",
    ]
    # Ops can disable/enable an Account inline. No reactivation flow exists in
    # the API, so this switch is the only way back from a disabled state.
    list_editable = ["is_active"]
    list_filter = ["role", "is_active", "is_email_verified"]
    search_fields = ["email", "user__email", "user__username"]
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]

    @display(description="Email verified", ordering="is_email_verified")
    def email_verified_badge(self, obj):
        if obj.is_email_verified:
            return self.badge("Verified", "green")
        return self.badge("Pending", "yellow")

    @display(description="Profile")
    def profile_state(self, obj):
        if obj.has_profile:
            return self.badge("Complete", "green")
        return self.badge("Missing", "yellow")


@admin.register(EmailOTP)
class EmailOTPAdmin(ReadOnlyAdmin):
    """Codes are hashed and single-use: audit only, never editable."""

    list_display = [
        "email",
        "user",
        "purpose",
        "status_badge",
        "attempts",
        "expires_at",
        "created_at",
    ]
    list_filter = ["purpose"]
    search_fields = ["email", "user__email"]
    readonly_fields = [
        "user",
        "email",
        "purpose",
        "code_hash",
        "expires_at",
        "attempts",
        "consumed_at",
        "metadata",
        "created_at",
        "updated_at",
    ]

    @display(description="Status")
    def status_badge(self, obj):
        if obj.consumed_at:
            return self.badge("Consumed", "gray")
        if obj.is_expired:
            return self.badge("Expired", "red")
        if obj.is_locked:
            return self.badge("Locked", "yellow")
        return self.badge("Active", "green")


@admin.register(SocialAccountLink)
class SocialAccountLinkAdmin(ReadOnlyAdmin):
    """Provider identity → Qoot Account binding (Apple later logins rely on it)."""

    list_display = ["social_account", "account", "created_at"]
    list_filter = ["social_account__provider"]
    search_fields = ["social_account__uid", "social_account__user__email", "account__email"]
    readonly_fields = ["social_account", "account", "created_at", "updated_at"]
