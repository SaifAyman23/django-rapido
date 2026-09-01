"""Dashboard callbacks for django-unfold.

Supplies metrics and environment badges rendered on the admin index page.
"""

from typing import Any, Dict, Tuple

from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _


def dashboard_callback(request: HttpRequest, context: Dict[str, Any]) -> Dict[str, Any]:
    """Provide dashboard context for the admin index page.

    Aggregates user counts and today's activity for the dashboard template.
    """
    from django.contrib.admin.models import LogEntry
    from django.db.models import Count

    from common.models import CustomUser

    today = timezone.now().date()

    total_users = CustomUser.objects.count()
    active_users = CustomUser.objects.filter(is_active=True).count()
    verified_users = CustomUser.objects.filter(is_verified=True).count()
    today_registrations = CustomUser.objects.filter(created_at__date=today).count()
    recent_actions = LogEntry.objects.filter(action_time__date=today).count()

    context["total_users"] = total_users
    context["active_users"] = active_users
    context["verified_users"] = verified_users
    context["today_registrations"] = today_registrations
    context["recent_actions"] = recent_actions

    return context


def environment_callback(request: HttpRequest) -> Tuple[str, str]:
    """Return the environment badge label and color for the admin header."""
    return ("All OK!", "success")


def badge_callback(request: HttpRequest) -> int:
    """Return the numeric badge shown in the sidebar (0 hides it)."""
    return 0


def permission_callback(request: HttpRequest) -> bool:
    """Check whether the user may view the dashboard stats."""
    return request.user.has_perm("common.change_customuser")
