"""Compliance translations — FAQ copy and policy text are user-facing."""

from modeltranslation.translator import TranslationOptions, translator

from .models import ComplianceDocument, FAQ, PolicyDocument


class FAQTranslationOptions(TranslationOptions):
    fields = ("question", "answer")


class ComplianceDocumentTranslationOptions(TranslationOptions):
    fields = ("title", "content")


class PolicyDocumentTranslationOptions(TranslationOptions):
    fields = ("title", "content")


translator.register(FAQ, FAQTranslationOptions)
translator.register(ComplianceDocument, ComplianceDocumentTranslationOptions)
translator.register(PolicyDocument, PolicyDocumentTranslationOptions)
