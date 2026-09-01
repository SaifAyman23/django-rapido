"""
REUSE: Register translatable fields for compliance.

Requires: modeltranslation in INSTALLED_APPS before admin.
From ras-elbar-go/backend/compliance/translation.py
"""

from modeltranslation.translator import TranslationOptions, translator

from .models import FAQ, ComplianceDocument


class FAQTranslationOptions(TranslationOptions):
    fields = ("question", "answer")


class ComplianceDocumentTranslationOptions(TranslationOptions):
    fields = ("title", "content")


translator.register(FAQ, FAQTranslationOptions)
translator.register(ComplianceDocument, ComplianceDocumentTranslationOptions)
