# settings.py - Updated with Django 6.0 Theme for django-unfold
# Dark Mode Only - Production Ready Configuration

from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

######################################################################
# Unfold
######################################################################
UNFOLD = {
    "STUDIO": {
        # "header_sticky": True,
        # "layout_style": "boxed",
        # "header_variant": "dark",
        # "sidebar_style": "minimal",
        # "sidebar_variant": "dark",
        # "site_banner": "Custom global message",
    },
    "SITE_TITLE": _("Dashboard Admin"),
    "SITE_HEADER": _("Dashboard Admin"),
    "SITE_SUBHEADER": _("Unfold admin demo"),
    "SITE_SYMBOL": "dashboard",
    # "SITE_ICON": lambda request: static("dashboard/images/logo.svg"),
    # "SITE_URL": None,
    # "SITE_DROPDOWN": [
    #     {
    #         "icon": "diamond",
    #         "title": _("Unfold theme repository"),
    #         "link": "https://github.com/unfoldadmin/django-unfold",
    #     },
    #     {
    #         "icon": "rocket_launch",
    #         "title": _("Turbo boilerplate repository"),
    #         "link": "https://github.com/unfoldadmin/turbo",
    #     },
    #     {
    #         "icon": "description",
    #         "title": _("Technical documentation"),
    #         "link": "https://unfoldadmin.com/docs/",
    #     },
    # ],
    # "SHOW_HISTORY": True,
    # "SHOW_LANGUAGES": True,
    "LANGUAGE_FLAGS": {
        "de": "🇩🇪",
        "en": "🇺🇸",
    },
    "ENVIRONMENT": "dashboard.environment_callback",
    "DASHBOARD_CALLBACK": "dashboard.dashboard_callback",
    "LOGIN": {
        "image": lambda request: static("dashboard/images/login-bg.jpg"),
        "form": "dashboard.forms.LoginForm",
    },
    "STYLES": [
        lambda request: static("css/style.css"),
    ],
    "SCRIPTS": [
        # lambda request: static("js/chart.min.js"),
    ],
    "COLORS": {
        "base": {
            "50": "oklch(0.985 0 0)",              # Near white
            "100": "oklch(0.967 0.001 286.375)",   # Secondary/muted (light theme)
            "200": "oklch(0.92 0.004 286.32)",     # Border/input
            "300": "oklch(0.705 0.015 286.067)",   # Muted foreground (dark theme)
            "400": "oklch(0.552 0.016 285.938)",   # Muted foreground (light theme)
            "500": "oklch(0.488 0.243 264.376)",   # Primary purple
            "600": "oklch(0.424 0.199 265.638)",   # Chart-5
            "700": "oklch(0.274 0.006 286.033)",   # Secondary (dark theme)
            "800": "oklch(0.21 0.006 285.885)",    # Card/popover (dark theme)
            "850": "oklch(0.183 0.005 285.85)",    # Interpolated
            "900": "oklch(0.141 0.005 285.823)",   # Background (dark) / Foreground (light)
            "925": "oklch(0.12 0.004 285.8)",      # Interpolated
            "950": "oklch(0.1 0.003 285.78)",      # Deeper dark
            "975": "oklch(0.08 0.002 285.76)"      # Almost black
        },
        "primary": {
            "50": "oklch(0.97 0.014 254.604)",     # Primary foreground
            "100": "oklch(0.809 0.105 251.813)",   # Chart-1
            "200": "oklch(0.708 0 0)",             # Ring (light theme)
            "300": "oklch(0.623 0.214 259.815)",   # Chart-2
            "400": "oklch(0.556 0 0)",             # Ring (dark theme)
            "500": "oklch(0.546 0.245 262.881)",   # Chart-3 / Primary variant
            "600": "oklch(0.488 0.243 264.376)",   # Primary
            "700": "oklch(0.424 0.199 265.638)",   # Chart-5
            "800": "oklch(0.35 0.16 266)",         # Darker primary
            "900": "oklch(0.28 0.13 267)",         # Deep primary
            "950": "oklch(0.21 0.1 268)"           # Almost black primary
        },
        "font": {
            "subtle-light": "oklch(0.552 0.016 285.938)",    # Muted foreground (light)
            "subtle-dark": "oklch(0.705 0.015 286.067)",     # Muted foreground (dark)
            "default-light": "oklch(0.141 0.005 285.823)",   # Foreground (light)
            "default-dark": "oklch(0.985 0 0)",              # Foreground (dark)
            "important-light": "oklch(0.488 0.243 264.376)", # Primary
            "important-dark": "oklch(0.97 0.014 254.604)"    # Primary foreground
        },
        "semantic": {
            "accent": "oklch(0.488 0.243 264.376)",          # Primary purple
            "accent-light": "oklch(0.623 0.214 259.815)",    # Chart-2
            "accent-dark": "oklch(0.424 0.199 265.638)",     # Chart-5
            "accent-bright": "oklch(0.809 0.105 251.813)",   # Chart-1
            "accent-dim": "oklch(0.488 0.243 264.376 / 0.08)",
            "accent-glow": "oklch(0.546 0.245 262.881 / 0.25)",
            
            "blue": "oklch(0.55 0.15 250)",
            "blue-light": "oklch(0.92 0.02 250)",
            "blue-dim": "oklch(0.55 0.15 250 / 0.12)",
            
            "green": "oklch(0.607 0.226 289.4)",             # Purple-secondary from CSS
            "green-light": "oklch(0.85 0.15 289.4)",
            "green-dim": "oklch(0.607 0.226 289.4 / 0.12)",
            
            "amber": "oklch(0.70 0.15 75)",
            "amber-light": "oklch(0.95 0.03 75)",
            "amber-dim": "oklch(0.70 0.15 75 / 0.12)",
            
            "red": "oklch(0.577 0.245 27.325)",              # Destructive
            "red-light": "oklch(0.95 0.02 25)",
            "red-dim": "oklch(0.577 0.245 27.325 / 0.12)",
            
            "purple": "oklch(0.488 0.243 264.376)",          # Primary
            "purple-light": "oklch(0.95 0.02 290)",
            "purple-dim": "oklch(0.488 0.243 264.376 / 0.12)",
            
            "electric": "oklch(0.75 0.15 195)",
            "navy": "oklch(0.21 0.006 285.885)",             # Card/popover dark
            "ink": "oklch(0.141 0.005 285.823)"              # Background dark
        },
        "background": {
            "primary-light": "oklch(1.000 0.000 89.9)",      # Background (light)
            "primary-dark": "oklch(0.141 0.005 285.823)",    # Background (dark)
            "secondary-light": "oklch(0.967 0.001 286.375)", # Secondary (light)
            "secondary-dark": "oklch(0.21 0.006 285.885)",   # Card (dark)
            "tertiary-light": "oklch(0.92 0.004 286.32)",    # Border
            "tertiary-dark": "oklch(0.274 0.006 286.033)",   # Secondary (dark)
            "elevated-light": "oklch(1 0 0)",                # Card (light)
            "elevated-dark": "oklch(0.21 0.006 285.885)"     # Card (dark)
        },
        "border": {
            "light-light": "oklch(0.92 0.004 286.32)",       # Border (light)
            "light-dark": "oklch(1 0 0 / 10%)",              # Border (dark)
            "strong-light": "oklch(0.552 0.016 285.938)",    # Muted foreground
            "strong-dark": "oklch(0.705 0.015 286.067)"      # Muted foreground dark
        },
        "text": {
            "primary-light": "oklch(0.141 0.005 285.823)",   # Foreground (light)
            "primary-dark": "oklch(0.985 0 0)",              # Foreground (dark)
            "secondary-light": "oklch(0.21 0.006 285.885)",  # Secondary foreground
            "secondary-dark": "oklch(0.705 0.015 286.067)",  # Muted foreground dark
            "tertiary-light": "oklch(0.552 0.016 285.938)",  # Muted foreground light
            "tertiary-dark": "oklch(0.705 0.015 286.067)",   # Muted foreground dark
            "inverse-light": "oklch(0.985 0 0)",             # White
            "inverse-dark": "oklch(0.141 0.005 285.823)"     # Dark
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "command_search": True,
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
                "title": _("Users & Groups"),
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
                        "title": _("Clocked"),
                        "icon": "hourglass_bottom",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_clockedschedule_changelist"
                        ),
                    },
                    {
                        "title": _("Crontabs"),
                        "icon": "update",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_crontabschedule_changelist"
                        ),
                    },
                    {
                        "title": _("Intervals"),
                        "icon": "timer",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_intervalschedule_changelist"
                        ),
                    },
                    {
                        "title": _("Periodic tasks"),
                        "icon": "task",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_periodictask_changelist"
                        ),
                    },
                    {
                        "title": _("Solar events"),
                        "icon": "event",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_solarschedule_changelist"
                        ),
                    },
                ],
            },
        ],
    },
}

UNFOLD_STUDIO_ENABLE_CUSTOMIZER = True

UNFOLD_STUDIO_DEFAULT_FRAGMENT = "color-schemes"

UNFOLD_STUDIO_ENABLE_SAVE = False

UNFOLD_STUDIO_ENABLE_FILEUPLOAD = False

UNFOLD_STUDIO_ALWAYS_OPEN = True

UNFOLD_STUDIO_ENABLE_RESET_PASSWORD = True

