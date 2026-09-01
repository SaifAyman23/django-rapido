"""Accounts application configuration.

Registers the accounts app which provides email-based authentication,
OTP verification, and password-reset flows.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Django app config for the accounts package."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
