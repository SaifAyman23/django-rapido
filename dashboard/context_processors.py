"""Dashboard template context processors.

Injects unfold theme colors and recent-activity data into admin templates.
"""

import json
import logging

from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

User = get_user_model()


def unfold_colors(request):
    """Provide unfold colors to templates for dynamic styling."""
    colors = getattr(settings, "UNFOLD", {}).get("COLORS", {})
    return {
        "unfold_colors": colors,
    }


def dashboard_context(request):
    """Provide dashboard data with fallbacks for admin templates.

    Builds recent-activity feed from admin LogEntry and injects safe defaults
    when the request is unauthenticated or the query fails.
    """
    if not request.user.is_staff:
        return {}

    context = {
        "total_users": 0,
        "active_users": 0,
        "verified_users": 0,
        "today_registrations": 0,
        "recent_actions": 0,
        "recent_activities": [],
        "recent_activities_json": "[]",
    }

    try:
        recent_logs = LogEntry.objects.select_related("user", "content_type").order_by(
            "-action_time"
        )[:10]

        activities = []
        action_map = {
            ADDITION: _("Added"),
            CHANGE: _("Changed"),
            DELETION: _("Deleted"),
        }

        for log in recent_logs:
            action_name = action_map.get(log.action_flag, _("Action"))
            user_name = (
                log.user.get_full_name()
                if log.user and log.user.get_full_name()
                else (log.user.username if log.user else _("System"))
            )
            activities.append(
                {
                    "description": f"{user_name} {action_name.lower()} {log.object_repr}",
                    "time": log.action_time.strftime("%Y-%m-%d %H:%M"),
                    "status": action_name,
                }
            )

        context["recent_activities"] = activities
        context["recent_activities_json"] = json.dumps(activities)

    except Exception as e:
        logger.error(f"Error in dashboard context: {e}")

    return context
