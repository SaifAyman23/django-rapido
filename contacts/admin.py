"""REUSE: Contact admin."""

from django.contrib import admin

from common.unfold_admin_bases import BaseAdmin

from .models import ContactInfo, ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(BaseAdmin):
    list_display = ["name", "email", "subject", "created_at"]
    search_fields = ["name", "email", "subject", "message"]


@admin.register(ContactInfo)
class ContactInfoAdmin(BaseAdmin):
    list_display = ["address", "phone", "email", "start_hours", "end_hours"]
