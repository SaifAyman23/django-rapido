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
    "SITE_TITLE": _("Django Rapido"),
    "SITE_HEADER": _("Django Rapido Dashboard"),
    "SITE_SUBHEADER": _("Django Rapido V2.0 — Production Starter"),
    "SITE_SYMBOL": "dashboard",
    "SITE_ICON": lambda request: static("logo.svg"),
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
    "SHOW_LANGUAGES": True,
    "LANGUAGE_FLAGS": {
        "ar": "🇪🇬",
        "en": "🇺🇸",
    },
    "ENVIRONMENT": "dashboard.environment_callback",
    "DASHBOARD_CALLBACK": "dashboard.dashboard_callback",
    "LOGIN": {
        "image": lambda request: static("images/login-bg.jpg"),
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
            "50": "oklch(0.985 0 0)",  # #fafafa - zinc-50 / card light */
            "100": "oklch(0.967 0.001 286.375)",  # #f4f4f5 - secondary light token */
            "200": "oklch(0.92 0.004 286.32)",  # #e4e4e7 - border light token */
            "300": "oklch(0.87 0.006 286.32)",  # #d4d4d8 - zinc-300 */
            "400": "oklch(0.705 0.015 286.067)",  # #a1a1aa - muted-fg dark token */
            "500": "oklch(0.552 0.016 285.938)",  # #71717a - muted-fg light token */
            "600": "oklch(0.442 0.017 285.786)",  # #52525b - zinc-600 */
            "700": "oklch(0.37 0.013 285.805)",  # #3f3f46 - zinc-700 */
            "800": "oklch(0.274 0.006 286.033)",  # #27272a - secondary dark token */
            "850": "oklch(0.24 0.006 286)",  # #1f1f22 - between zinc-800/900 */
            "900": "oklch(0.21 0.006 285.885)",  # #18181b - popover/sidebar dark token */
            "925": "oklch(0.174 0.004 286)",  # #101012 - card dark token */
            "950": "oklch(0.141 0.005 285.823)",  # #09090b - background dark token */
            "975": "oklch(0.1 0.005 286)",  # #030304 - border dark token */
        },
        "primary": {
            "50": "oklch(0.977 0.014 308.299)",  # #f5f3ff - violet-50 */
            "100": "oklch(0.946 0.033 307.174)",  # #ede9fe - violet-100 */
            "200": "oklch(0.894 0.057 293.283)",  # #ddd6fe - violet-200 */
            "300": "oklch(0.812 0.101 294.588)",  # #c4b5fd - violet-300 */
            "400": "oklch(0.714 0.143 293.571)",  # #a78bfa - violet-400 */
            "500": "oklch(0.606 0.25 292.717)",  # #8b5cf6 - BRAND VIOLET */
            "600": "oklch(0.542 0.281 293.009)",  # #7c3aed - violet-600 */
            "700": "oklch(0.496 0.265 301.924)",  # #6d28d9 - violet-700 */
            "800": "oklch(0.438 0.218 303.089)",  # #5b21b6 - violet-800 */
            "900": "oklch(0.381 0.176 304.987)",  # #4c1d95 - violet-900 */
            "950": "oklch(0.291 0.149 302.717)",  # #2e1065 - violet-950 */
        },
        "blue": {
            "50": "oklch(97% 0.014 254.604)",
            "100": "oklch(93.2% 0.032 255.585)",
            "200": "oklch(88.2% 0.059 254.128)",
            "300": "oklch(80.9% 0.105 251.813)",
            "400": "oklch(70.7% 0.165 254.624)",
            "500": "oklch(62.3% 0.214 259.815)",
            "600": "oklch(54.6% 0.245 262.881)",
            "700": "oklch(48.8% 0.243 264.376)",
            "800": "oklch(42.4% 0.199 265.638)",
            "900": "oklch(37.9% 0.146 265.522)",
            "950": "oklch(28.2% 0.091 267.935)",
        },
        "red": {
            "50": "oklch(97.1% 0.013 17.38)",
            "100": "oklch(93.6% 0.032 17.717)",
            "200": "oklch(88.5% 0.062 18.334)",
            "300": "oklch(80.8% 0.114 19.571)",
            "400": "oklch(70.4% 0.191 22.216)",
            "500": "oklch(63.7% 0.237 25.331)",
            "600": "oklch(57.7% 0.245 27.325)",
            "700": "oklch(50.5% 0.213 27.518)",
            "800": "oklch(44.4% 0.177 26.899)",
            "900": "oklch(39.6% 0.141 25.723)",
            "950": "oklch(26.4% 0.09 26.042)",
        },
        "amber": {
            "50": "oklch(98.7% 0.022 95.277)",
            "100": "oklch(96.2% 0.059 95.617)",
            "200": "oklch(92.4% 0.12 95.746)",
            "300": "oklch(87.9% 0.169 91.605)",
            "400": "oklch(82.8% 0.189 84.429)",
            "500": "oklch(76.9% 0.188 70.08)",
            "600": "oklch(66.6% 0.179 58.318)",
            "700": "oklch(55.5% 0.163 48.998)",
            "800": "oklch(47.3% 0.137 46.201)",
            "900": "oklch(41.4% 0.112 45.904)",
            "950": "oklch(27.9% 0.077 45.635)",
        },
        "green": {
            "50": "oklch(98.2% 0.018 155.826)",
            "100": "oklch(96.2% 0.044 156.743)",
            "200": "oklch(92.5% 0.084 155.995)",
            "300": "oklch(87.1% 0.15 154.449)",
            "400": "oklch(79.2% 0.209 151.711)",
            "500": "oklch(72.3% 0.219 149.579)",
            "600": "oklch(62.7% 0.194 149.214)",
            "700": "oklch(52.7% 0.154 150.069)",
            "800": "oklch(44.8% 0.119 151.328)",
            "900": "oklch(39.3% 0.095 152.535)",
            "950": "oklch(26.6% 0.065 152.934)",
        },
        "purple": {
            "50": "oklch(97.7% 0.014 308.299)",
            "100": "oklch(94.6% 0.033 307.174)",
            "200": "oklch(89.4% 0.057 293.283)",
            "300": "oklch(81.2% 0.101 294.588)",
            "400": "oklch(71.4% 0.143 293.571)",
            "500": "oklch(60.6% 0.25 292.717)",
            "600": "oklch(54.2% 0.281 293.009)",
            "700": "oklch(49.6% 0.265 301.924)",
            "800": "oklch(43.8% 0.218 303.089)",
            "900": "oklch(38.1% 0.176 304.987)",
            "950": "oklch(29.1% 0.149 302.717)",
        },
        "sky": {
            "50": "oklch(98.4% 0.019 200.873)",
            "100": "oklch(95.4% 0.038 200.321)",
            "200": "oklch(90.1% 0.058 230.902)",
            "300": "oklch(82.8% 0.111 230.318)",
            "400": "oklch(74.6% 0.16 232.661)",
            "500": "oklch(68.5% 0.169 237.323)",
            "600": "oklch(58.8% 0.158 241.966)",
            "700": "oklch(50% 0.134 242.749)",
            "800": "oklch(44.3% 0.11 240.79)",
            "900": "oklch(39.1% 0.09 240.876)",
            "950": "oklch(30.2% 0.056 238.565)",
        },
        "indigo": {
            "50": "oklch(96.2% 0.018 272.314)",
            "100": "oklch(92.9% 0.033 272.788)",
            "200": "oklch(87% 0.065 274.039)",
            "300": "oklch(78.5% 0.115 274.713)",
            "400": "oklch(68.3% 0.18 277.366)",
            "500": "oklch(58.5% 0.233 277.117)",
            "600": "oklch(51.1% 0.262 276.966)",
            "700": "oklch(45.7% 0.24 277.023)",
            "800": "oklch(39.8% 0.195 277.366)",
            "900": "oklch(35.9% 0.144 278.697)",
            "950": "oklch(25.7% 0.09 281.288)",
        },
        "lime": {
            "50": "oklch(98.6% 0.031 120.757)",
            "100": "oklch(96.7% 0.067 122.328)",
            "200": "oklch(93.8% 0.127 124.321)",
            "300": "oklch(89.7% 0.196 126.665)",
            "400": "oklch(84.1% 0.238 128.85)",
            "500": "oklch(76.8% 0.233 130.85)",
            "600": "oklch(64.8% 0.2 131.684)",
            "700": "oklch(53.2% 0.157 131.589)",
            "800": "oklch(45.3% 0.124 130.933)",
            "900": "oklch(39.8% 0.095 131.2)",
            "950": "oklch(27.4% 0.072 132.109)",
        },
        "font": {
            "subtle-light": "var(--color-base-500)",  # #71717a - muted-fg light token */
            "subtle-dark": "var(--color-base-400)",  # #a1a1aa - muted-fg dark token */
            "default-light": "var(--color-base-950)",  # #09090b - foreground light token */
            "default-dark": "var(--color-base-50)",  # #fafafa - foreground dark token */
            "important-light": "var(--color-base-950)",  # #09090b - foreground light token */
            "important-dark": "var(--color-base-50)",  # #fafafa - foreground dark token */
        },
        "semantic": {
            "accent": "var(--color-primary-700)",  # #6d28d9 - violet-700 */
            "accent-light": "var(--color-primary-300)",  # #c4b5fd - violet-300 */
            "accent-dark": "var(--color-primary-800)",  # #5b21b6 - violet-800 */
            "accent-bright": "oklch(0.714 0.143 293.571)",  # #a78bfa - violet-400 */
            "accent-dim": "oklch(0.606 0.25 292.717 / 0.08)",  # brand violet with 8% opacity */
            "accent-glow": "oklch(0.606 0.25 292.717 / 0.25)",  # brand violet with 25% opacity */
            "blue": "var(--color-blue-500)",  # chart-2 token */
            "blue-light": "var(--color-blue-100)",  # #eff6ff-ish pale blue */
            "blue-dim": "oklch(0.623 0.214 259.815 / 0.12)",  # chart-2 with 12% opacity */
            "green": "var(--color-green-600)",  # standard green */
            "green-light": "var(--color-green-100)",  # pale green */
            "green-dim": "oklch(0.627 0.194 149.214 / 0.12)",  # green-600 with 12% opacity */
            "amber": "var(--color-amber-500)",  # standard amber */
            "amber-light": "var(--color-amber-100)",  # pale amber */
            "amber-dim": "oklch(0.769 0.188 70.08 / 0.12)",  # amber-500 with 12% opacity */
            "red": "var(--color-red-600)",  # #e7000b - destructive light token */
            "red-light": "var(--color-red-100)",  # pale red */
            "red-dim": "oklch(0.577 0.245 27.325 / 0.12)",  # destructive with 12% opacity */
            "purple": "var(--color-primary-600)",  # #7c3aed - violet-600 */
            "purple-light": "var(--color-primary-100)",  # #ede9fe - violet-100 */
            "purple-dim": "oklch(0.542 0.281 293.009 / 0.12)",  # violet-600 with 12% opacity */
            "electric": "oklch(0.766 0.112 238)",  # #68bdf2 - accent-sky token */
            "navy": "var(--color-base-900)",  # #18181b - popover dark token */
            "ink": "var(--color-base-950)",  # #09090b - background dark token */
        },
        "background": {
            "primary-light": "var(--color-base-50)",  # #fafafa - card light */
            "primary-dark": "var(--color-base-950)",  # #09090b - background dark token */
            "secondary-light": "var(--color-base-100)",  # #f4f4f5 - secondary light token */
            "secondary-dark": "var(--color-base-900)",  # #18181b - popover dark token */
            "tertiary-light": "var(--color-base-200)",  # #e4e4e7 - border light token */
            "tertiary-dark": "var(--color-base-800)",  # #27272a - secondary dark token */
            "elevated-light": "oklch(1 0 0)",  # #ffffff - card light token */
            "elevated-dark": "var(--color-base-925)",  # #101012 - card dark token */
        },
        "border": {
            "light-light": "var(--color-base-200)",  # #e4e4e7 - border light token */
            "light-dark": "var(--color-base-800)",  # #27272a - subtle dark border */
            "strong-light": "var(--color-base-300)",  # #d4d4d8 - zinc-300 */
            "strong-dark": "var(--color-base-700)",  # #3f3f46 - zinc-700 */
        },
        "text": {
            "primary-light": "var(--color-base-950)",  # #09090b - foreground light token */
            "primary-dark": "var(--color-base-50)",  # #fafafa - foreground dark token */
            "secondary-light": "var(--color-base-500)",  # #71717a - muted-fg light token */
            "secondary-dark": "var(--color-base-400)",  # #a1a1aa - muted-fg dark token */
            "tertiary-light": "var(--color-base-500)",  # #71717a - muted-fg light token */
            "tertiary-dark": "var(--color-base-400)",  # #a1a1aa - muted-fg dark token */
            "inverse-light": "var(--color-base-50)",  # #fafafa - light text for dark surfaces */
            "inverse-dark": "var(--color-base-950)",  # #09090b - dark text for light surfaces */
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
                    {
                        "title": _("Live Logs"),
                        "icon": "terminal",
                        "link": reverse_lazy("admin-live-logs"),
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
                    {
                        "title": _("Social Apps"),
                        "icon": "key",
                        "link": reverse_lazy("admin:socialaccount_socialapp_changelist"),
                    },
                    {
                        "title": _("Social Accounts"),
                        "icon": "link",
                        "link": reverse_lazy("admin:socialaccount_socialaccount_changelist"),
                    },
                    {
                        "title": _("Social Tokens"),
                        "icon": "token",
                        "link": reverse_lazy("admin:socialaccount_socialtoken_changelist"),
                    },
                    {
                        "title": _("OTP Tokens"),
                        "icon": "timer",
                        "link": reverse_lazy("admin:accounts_otprecord_changelist"),
                    },
                    {
                        "title": _("Password Reset Tokens"),
                        "icon": "lock",
                        "link": reverse_lazy("admin:accounts_passwordresettoken_changelist"),
                    },
                ],
            },
            {
                "title": _("Contacts"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Contact Info"),
                        "icon": "contact_phone",
                        "link": reverse_lazy("admin:contacts_contactinfo_changelist"),
                    },
                    {
                        "title": _("Contact Messages"),
                        "icon": "mail",
                        "link": reverse_lazy("admin:contacts_contactmessage_changelist"),
                    },
                ],
            },
            {
                "title": _("Notifications"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("User Notifications"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:notifications_notification_changelist"),
                    },
                    {
                        "title": _("Devices"),
                        "icon": "devices",
                        "link": reverse_lazy("admin:notifications_device_changelist"),
                    },
                ],
            },
            {
                "title": _("Compliance"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("FAQs"),
                        "icon": "help",
                        "link": reverse_lazy("admin:compliance_faq_changelist"),
                    },
                    {
                        "title": _("Policies"),
                        "icon": "description",
                        "link": reverse_lazy("admin:compliance_compliancedocument_changelist"),
                    },
                ],
            },
            # ── Project sections go here (template rule: only reference
            #    installed apps with registered ModelAdmins, or /admin/ 500s
            #    on NoReverseMatch). Example:
            #    {
            #        "title": _("Shop"),
            #        "collapsible": True,
            #        "items": [
            #            {
            #                "title": _("Products"),
            #                "icon": "inventory_2",
            #                "link": reverse_lazy("admin:shop_product_changelist"),
            #            },
            #        ],
            #    },
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
                        "link": reverse_lazy(
                            "admin:django_celery_beat_intervalschedule_changelist"
                        ),
                    },
                    {
                        "title": _("Clocked"),
                        "icon": "hourglass_bottom",
                        "link": reverse_lazy("admin:django_celery_beat_clockedschedule_changelist"),
                    },
                    {
                        "title": _("Solar Events"),
                        "icon": "event",
                        "link": reverse_lazy("admin:django_celery_beat_solarschedule_changelist"),
                    },
                ],
            },
        ],
    },
}

UNFOLD_STUDIO_ENABLE_CUSTOMIZER = False

UNFOLD_STUDIO_ENABLE_SAVE = False

UNFOLD_STUDIO_ENABLE_FILEUPLOAD = False

UNFOLD_STUDIO_ALWAYS_OPEN = True

UNFOLD_STUDIO_ENABLE_RESET_PASSWORD = True
