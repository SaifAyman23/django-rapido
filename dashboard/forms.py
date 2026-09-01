"""Dashboard authentication forms.

Provides a custom login form that pre-fills credentials from settings for
development convenience.
"""

from django import forms
from django.conf import settings
from unfold.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    """Admin login form with optional credential pre-fill for development."""

    password = forms.CharField(widget=forms.PasswordInput())

    def __init__(self, request=None, *args, **kwargs):
        """Initialize the form and pre-fill credentials when configured."""
        super().__init__(request, *args, **kwargs)

        # Pre-fill from settings only for local/dev convenience.
        if settings.LOGIN_USERNAME and settings.LOGIN_PASSWORD:
            self.fields["username"].initial = settings.LOGIN_USERNAME
            self.fields["password"].initial = settings.LOGIN_PASSWORD
