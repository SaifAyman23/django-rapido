from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


UNFOLD = {
    "SITE_TITLE": _("Django Rapido"),
    "SITE_HEADER": _("Django Rapido V2.0"),
    "SITE_SUBHEADER": _("Modern Django Starter"),
    "SITE_SYMBOL": "speed",
    "SHOW_LANGUAGES": True,
    "ENVIRONMENT": "dashboard.callbacks.environment_callback",
    "DASHBOARD_CALLBACK": "dashboard.callbacks.dashboard_callback",
    "LOGIN": {},
    "COLORS": {
        "primary": {
            "50": "oklch(97% 0.025 260)",
            "100": "oklch(92% 0.045 260)",
            "200": "oklch(85% 0.065 260)",
            "300": "oklch(75% 0.085 260)",
            "400": "oklch(65% 0.095 260)",
            "500": "oklch(45% 0.09 260)",
            "600": "oklch(38% 0.085 260)",
            "700": "oklch(31% 0.08 260)",
            "800": "oklch(24% 0.075 260)",
            "900": "oklch(18% 0.07 260)",
            "950": "oklch(13% 0.06 260)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Navigation"),
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Users & Accounts"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "account_circle",
                        "link": reverse_lazy("admin:common_customuser_changelist"),
                    },
                    {
                        "title": _("Admin Logs"),
                        "icon": "hourglass_bottom",
                        "link": reverse_lazy("admin:admin_logentry_changelist"),
                    },
                    {
                        "title": _("Audit Logs"),
                        "icon": "history",
                        "link": reverse_lazy("admin:common_auditlog_changelist"),
                    },
                    {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
            {
                "title": _("Celery Tasks"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Periodic Tasks"),
                        "icon": "task",
                        "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist"),
                    },
                    {
                        "title": _("Crontabs"),
                        "icon": "update",
                        "link": reverse_lazy("admin:django_celery_beat_crontabschedule_changelist"),
                    },
                    {
                        "title": _("Intervals"),
                        "icon": "timer",
                        "link": reverse_lazy("admin:django_celery_beat_intervalschedule_changelist"),
                    },
                    {
                        "title": _("Clocked"),
                        "icon": "hourglass_bottom",
                        "link": reverse_lazy("admin:django_celery_beat_clockedschedule_changelist"),
                    },
                ],
            },
        ],
    },
}
