from modeltranslation.translator import TranslationOptions, translator

from .models import CustomReminder, Notification


class NotificationTranslationOptions(TranslationOptions):
    fields = ("title", "body")


class CustomReminderTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(Notification, NotificationTranslationOptions)
translator.register(CustomReminder, CustomReminderTranslationOptions)
