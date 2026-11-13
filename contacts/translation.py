from modeltranslation.translator import TranslationOptions, translator

from .models import ContactInfo, ContactMessage


class ContactInfoTranslationOptions(TranslationOptions):
    fields = ("address", "working_hours")


class ContactMessageTranslationOptions(TranslationOptions):
    fields = ("name", "subject", "message")


translator.register(ContactInfo, ContactInfoTranslationOptions)
translator.register(ContactMessage, ContactMessageTranslationOptions)
