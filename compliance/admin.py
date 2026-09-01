"""REUSE: Compliance admin — translatable + Markdown."""

from django.contrib import admin
from django.utils.html import format_html
from unfold.decorators import display

from common.admin_mixins import MarkdownAdminMixin
from common.unfold_admin_bases import TranslationBaseAdmin

from .models import FAQ, ComplianceDocument


@admin.register(FAQ)
class FAQAdmin(TranslationBaseAdmin):
    list_display = ["question_preview", "is_published_badge", "sort_order"]
    list_filter = ["is_published"]
    search_fields = ["question", "answer"]
    list_editable = ["sort_order"]

    @display(description="Question")
    def question_preview(self, obj):
        return obj.question[:80] + "..." if len(obj.question) > 80 else obj.question

    @display(description="Published", ordering="is_published")
    def is_published_badge(self, obj):
        return self.badge("Published", "green") if obj.is_published else self.badge("Draft", "gray")


@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(MarkdownAdminMixin, TranslationBaseAdmin):
    """REUSE: MarkdownAdminMixin auto-applies MarkdownxWidget to content TextField."""

    list_display = ["type", "title", "is_published_badge"]
    list_filter = ["type", "is_published"]
    search_fields = ["title", "content"]
