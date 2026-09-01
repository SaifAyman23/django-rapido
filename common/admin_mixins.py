"""Admin mixins for rich-text editing.

Provides Markdown widget integration for TextField fields in the admin.
"""

from django.db import models
from markdownx.widgets import AdminMarkdownxWidget

# ===========================
# Markdown Form Mixin
# ===========================


class MarkdownFormMixin:
    """Automatically applies AdminMarkdownxWidget to all TextField fields."""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Use AdminMarkdownxWidget for TextField instances."""
        if isinstance(db_field, models.TextField):
            kwargs["widget"] = AdminMarkdownxWidget(
                attrs={
                    "class": "vLargeTextField",
                    "style": (
                        "background: var(--color-background-secondary-dark);"
                        "color: var(--color-text-primary-dark);"
                        "border: 1px solid var(--color-border-light-dark);"
                        "border-radius: 4px; padding: 8px 12px;"
                    ),
                }
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)


# ===========================
# Combined Mixin
# ===========================


class MarkdownAdminMixin(MarkdownFormMixin):
    """Combined mixin: markdown widgets + rendered previews for all TextFields.

    Usage:
        @admin.register(MyModel)
        class MyModelAdmin(MarkdownAdminMixin, BaseAdmin):
            pass
    """

    pass
