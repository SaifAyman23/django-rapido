"""Dashboard top-level views.

Provides the public landing redirect that sends ``/`` to the admin index.
"""

from django.views.generic import RedirectView


class HomeView(RedirectView):
    """Redirect the site root to the Django admin dashboard."""

    pattern_name = "admin:index"
