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
    "ENVIRONMENT": "common.environment_callback",
    "DASHBOARD_CALLBACK": "common.dashboard_callback",
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
    "TABS": [
        {
            "models": [
                # "dashboard.race",
            ],
            "items": [
                # {
                #     "title": _("Races"),
                #     "link": reverse_lazy("admin:dashboard_race_changelist"),
                # },
            ],
        },
        # {
        #     "page": "drivers",
        #     "models": ["dashboard.driver"],
        #     "items": [
        #         {
        #             "title": _("Drivers"),
        #             "link": reverse_lazy("admin:dashboard_driver_changelist"),
        #             "active": lambda request: request.path
        #             == reverse_lazy("admin:dashboard_driver_changelist")
        #             and "status__exact" not in request.GET,
        #         },
        #         {
        #             "title": _("Active drivers"),
        #             "link": lambda request: f"{
        #                 reverse_lazy('admin:dashboard_driver_changelist')
        #             }?status__exact=ACTIVE",
        #         },
        #         {
        #             "title": _("Crispy Form"),
        #             "link": reverse_lazy("admin:crispy_form"),
        #         },
        #         {
        #             "title": _("Crispy Formset"),
        #             "link": reverse_lazy("admin:crispy_formset"),
        #         },
        #     ],
        # },
    ],
    "COLORS": {
        "base": {
            "50": "oklch(98.5% 0.015 145)",        # #f2ffe7 - Obsidian white */
            "100": "oklch(96.5% 0.028 148)",       # #e0ffd0 - Obsidian light */
            "200": "oklch(92.5% 0.042 151)",       # #c5ffb1 - Obsidian soft */
            "300": "oklch(85.5% 0.055 154)",       # #a1f58a - Obsidian medium */
            "400": "oklch(72.5% 0.06 157)",        # #72d458 - Obsidian green */
            "500": "oklch(55.5% 0.065 160)",       # #46a735 - Obsidian forest */
            "600": "oklch(38.5% 0.07 163)",        # #247b1f - Obsidian deep */
            "700": "oklch(28.5% 0.075 166)",       # #115a16 - Obsidian dark */
            "800": "oklch(20.5% 0.08 169)",        # #074110 - Obsidian deeper */
            "850": "oklch(16.5% 0.085 172)",       # #03320b - Obsidian almost black */
            "900": "oklch(13.5% 0.08 175)",        # #012308 - Obsidian black-green */
            "925": "oklch(11.5% 0.07 178)",        # #001b06 - Dark obsidian */
            "950": "oklch(9.5% 0.06 181)",         # #001304 - True obsidian black */
            "975": "oklch(7.5% 0.05 184)"          # #000c02 - Pure obsidian */
        },
        "primary": {
            "50": "oklch(97% 0.025 145)",          # #f0faea - Obsidian mint */
            "100": "oklch(92% 0.045 148)",         # #d3f0ce - Obsidian seafoam */
            "200": "oklch(85% 0.065 151)",         # #ade0a4 - Obsidian sage */
            "300": "oklch(75% 0.085 154)",         # #80c77a - Obsidian medium */
            "400": "oklch(65% 0.095 157)",         # #56aa53 - Obsidian forest */
            "500": "oklch(45% 0.09 160)",          # #2a822b - Obsidian deep green */
            "600": "oklch(38% 0.085 163)",         # #1b691f - Obsidian pine */
            "700": "oklch(31% 0.08 166)",          # #0f5117 - Obsidian dark forest */
            "800": "oklch(24% 0.075 169)",         # #073c11 - Obsidian deeper */
            "900": "oklch(18% 0.07 172)",          # #022b0b - Obsidian almost black */
            "950": "oklch(13% 0.06 175)"           # #011d07 - Obsidian black-green */
        },
        "font": {
            "subtle-light": "var(--color-base-500)",   # #46a735 - Obsidian forest */
            "subtle-dark": "var(--color-base-400)",    # #72d458 - Obsidian green */
            "default-light": "var(--color-base-700)",  # #115a16 - Obsidian dark */
            "default-dark": "var(--color-base-300)",   # #a1f58a - Obsidian medium */
            "important-light": "var(--color-base-900)", # #012308 - Obsidian black-green */
            "important-dark": "var(--color-base-100)"   # #e0ffd0 - Obsidian light */
        },
        "semantic": {
            "accent": "var(--color-primary-500)",         # #2a822b - Obsidian deep green */
            "accent-light": "var(--color-primary-300)",   # #80c77a - Obsidian medium */
            "accent-dark": "var(--color-primary-700)",    # #0f5117 - Obsidian dark forest */
            "accent-bright": "oklch(75% 0.18 145)",       # #8fe080 - Bright obsidian */
            "accent-dim": "oklch(45% 0.09 160 / 0.08)",   # #2a822b with 8% opacity */
            "accent-glow": "oklch(65% 0.095 157 / 0.25)", # #56aa53 with 25% opacity */
            
            "blue": "oklch(55% 0.15 250)",                 # #3a7eb0 - Muted tech blue */
            "blue-light": "oklch(92% 0.02 250)",           # #e1ecf9 - Pale blue */
            "blue-dim": "oklch(55% 0.15 250 / 0.12)",      # #3a7eb0 with 12% opacity */
            
            "green": "var(--color-primary-500)",           # #2a822b - Obsidian deep green */
            "green-light": "var(--color-primary-100)",     # #d3f0ce - Obsidian seafoam */
            "green-dim": "var(--color-primary-500 / 0.12)", # #2a822b with 12% opacity */
            
            "amber": "oklch(70% 0.15 75)",                  # #c98a2b - Warm amber */
            "amber-light": "oklch(95% 0.03 75)",            # #fff1d6 - Pale amber */
            "amber-dim": "oklch(70% 0.15 75 / 0.12)",       # #c98a2b with 12% opacity */
            
            "red": "oklch(55% 0.18 25)",                     # #c43a4b - Muted crimson */
            "red-light": "oklch(95% 0.02 25)",               # #ffe6e8 - Pale pink */
            "red-dim": "oklch(55% 0.18 25 / 0.12)",          # #c43a4b with 12% opacity */
            
            "purple": "oklch(55% 0.15 290)",                  # #7a5fb0 - Muted purple */
            "purple-light": "oklch(95% 0.02 290)",            # #f0e8ff - Lavender */
            "purple-dim": "oklch(55% 0.15 290 / 0.12)",       # #7a5fb0 with 12% opacity */
            
            "electric": "oklch(75% 0.15 195)",                # #4dc9c9 - Electric teal */
            "navy": "var(--color-base-850)",                  # #03320b - Obsidian almost black */
            "ink": "var(--color-base-950)"                    # #001304 - True obsidian black */
        },
        "background": {
            "primary-light": "var(--color-base-50)",          # #f2ffe7 - Obsidian white */
            "primary-dark": "var(--color-base-950)",          # #001304 - True obsidian black */
            "secondary-light": "var(--color-base-100)",       # #e0ffd0 - Obsidian light */
            "secondary-dark": "var(--color-base-900)",        # #012308 - Obsidian black-green */
            "tertiary-light": "var(--color-base-200)",        # #c5ffb1 - Obsidian soft */
            "tertiary-dark": "var(--color-base-850)",         # #03320b - Obsidian almost black */
            "elevated-light": "oklch(100% 0 0)",              # #ffffff - Pure white */
            "elevated-dark": "var(--color-base-800)"          # #074110 - Obsidian deeper */
        },
        "border": {
            "light-light": "var(--color-base-200)",           # #c5ffb1 - Obsidian soft */
            "light-dark": "var(--color-base-700)",            # #115a16 - Obsidian dark */
            "strong-light": "var(--color-base-400)",          # #72d458 - Obsidian green */
            "strong-dark": "var(--color-base-600)"            # #247b1f - Obsidian deep */
        },
        "text": {
            "primary-light": "var(--color-base-900)",         # #012308 - Obsidian black-green */
            "primary-dark": "var(--color-base-100)",          # #e0ffd0 - Obsidian light */
            "secondary-light": "var(--color-base-700)",       # #115a16 - Obsidian dark */
            "secondary-dark": "var(--color-base-300)",        # #a1f58a - Obsidian medium */
            "tertiary-light": "var(--color-base-500)",        # #46a735 - Obsidian forest */
            "tertiary-dark": "var(--color-base-400)",         # #72d458 - Obsidian green */
            "inverse-light": "var(--color-base-950)",         # #001304 - True obsidian black */
            "inverse-dark": "var(--color-base-50)"            # #f2ffe7 - Obsidian white */
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
                    # {
                    #     "title": _("Drivers"),
                    #     "icon": "sports_motorsports",
                    #     "active": "dashboard.utils.driver_list_link_callback",
                    #     ###########################################################
                    #     # Works only with Studio: https://unfoldadmin.com/studio/
                    #     ###########################################################
                    #     "items": [
                    #         {
                    #             "title": _("List drivers"),
                    #             "link": reverse_lazy("admin:dashboard_driver_changelist"),
                    #             "active": "dashboard.utils.driver_list_sublink_callback",
                    #         },
                    #         {
                    #             "title": _("Advanced filters"),
                    #             "link": reverse_lazy(
                    #                 "admin:dashboard_driverwithfilters_changelist"
                    #             ),
                    #         },
                    #         {
                    #             "title": _("Crispy form"),
                    #             "link": reverse_lazy("admin:crispy_form"),
                    #         },
                    #         {
                    #             "title": _("Crispy formset"),
                    #             "link": reverse_lazy("admin:crispy_formset"),
                    #         },
                    #     ],
                    # },
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

