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
    "SITE_TITLE": _("Ras El Bar"),
    "SITE_HEADER": _("Ras El Bar Dashboard"),
    "SITE_SUBHEADER": _("Multi-Store Delivery Platform"),
    "SITE_SYMBOL": "dashboard",
    "SITE_ICON": lambda request: static("images/Icon-AI.svg"),
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
            "50": "oklch(98.5% 0.015 145)",  # #f2ffe7 - Obsidian white */
            "100": "oklch(96.5% 0.028 148)",  # #e0ffd0 - Obsidian light */
            "200": "oklch(92.5% 0.042 151)",  # #c5ffb1 - Obsidian soft */
            "300": "oklch(85.5% 0.055 154)",  # #a1f58a - Obsidian medium */
            "400": "oklch(72.5% 0.06 157)",  # #72d458 - Obsidian green */
            "500": "oklch(55.5% 0.065 160)",  # #46a735 - Obsidian forest */
            "600": "oklch(38.5% 0.07 163)",  # #247b1f - Obsidian deep */
            "700": "oklch(28.5% 0.075 166)",  # #115a16 - Obsidian dark */
            "800": "oklch(20.5% 0.08 169)",  # #074110 - Obsidian deeper */
            "850": "oklch(16.5% 0.085 172)",  # #03320b - Obsidian almost black */
            "900": "oklch(13.5% 0.08 175)",  # #012308 - Obsidian black-green */
            "925": "oklch(11.5% 0.07 178)",  # #001b06 - Dark obsidian */
            "950": "oklch(9.5% 0.06 181)",  # #001304 - True obsidian black */
            "975": "oklch(7.5% 0.05 184)",  # #000c02 - Pure obsidian */
        },
        "primary": {
            "50": "oklch(97% 0.025 145)",  # #f0faea - Obsidian mint */
            "100": "oklch(92% 0.045 148)",  # #d3f0ce - Obsidian seafoam */
            "200": "oklch(85% 0.065 151)",  # #ade0a4 - Obsidian sage */
            "300": "oklch(75% 0.085 154)",  # #80c77a - Obsidian medium */
            "400": "oklch(65% 0.095 157)",  # #56aa53 - Obsidian forest */
            "500": "oklch(45% 0.09 160)",  # #2a822b - Obsidian deep green */
            "600": "oklch(38% 0.085 163)",  # #1b691f - Obsidian pine */
            "700": "oklch(31% 0.08 166)",  # #0f5117 - Obsidian dark forest */
            "800": "oklch(24% 0.075 169)",  # #073c11 - Obsidian deeper */
            "900": "oklch(18% 0.07 172)",  # #022b0b - Obsidian almost black */
            "950": "oklch(13% 0.06 175)",  # #011d07 - Obsidian black-green */
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
            "subtle-light": "var(--color-base-500)",  # #46a735 - Obsidian forest */
            "subtle-dark": "var(--color-base-400)",  # #72d458 - Obsidian green */
            "default-light": "var(--color-base-700)",  # #115a16 - Obsidian dark */
            "default-dark": "var(--color-base-300)",  # #a1f58a - Obsidian medium */
            "important-light": "var(--color-base-900)",  # #012308 - Obsidian black-green */
            "important-dark": "var(--color-base-100)",  # #e0ffd0 - Obsidian light */
        },
        "semantic": {
            "accent": "var(--color-primary-500)",  # #2a822b - Obsidian deep green */
            "accent-light": "var(--color-primary-300)",  # #80c77a - Obsidian medium */
            "accent-dark": "var(--color-primary-700)",  # #0f5117 - Obsidian dark forest */
            "accent-bright": "oklch(75% 0.18 145)",  # #8fe080 - Bright obsidian */
            "accent-dim": "oklch(45% 0.09 160 / 0.08)",  # #2a822b with 8% opacity */
            "accent-glow": "oklch(65% 0.095 157 / 0.25)",  # #56aa53 with 25% opacity */
            "blue": "oklch(55% 0.15 250)",  # #3a7eb0 - Muted tech blue */
            "blue-light": "oklch(92% 0.02 250)",  # #e1ecf9 - Pale blue */
            "blue-dim": "oklch(55% 0.15 250 / 0.12)",  # #3a7eb0 with 12% opacity */
            "green": "var(--color-primary-500)",  # #2a822b - Obsidian deep green */
            "green-light": "var(--color-primary-100)",  # #d3f0ce - Obsidian seafoam */
            "green-dim": "var(--color-primary-500 / 0.12)",  # #2a822b with 12% opacity */
            "amber": "oklch(70% 0.15 75)",  # #c98a2b - Warm amber */
            "amber-light": "oklch(95% 0.03 75)",  # #fff1d6 - Pale amber */
            "amber-dim": "oklch(70% 0.15 75 / 0.12)",  # #c98a2b with 12% opacity */
            "red": "oklch(55% 0.18 25)",  # #c43a4b - Muted crimson */
            "red-light": "oklch(95% 0.02 25)",  # #ffe6e8 - Pale pink */
            "red-dim": "oklch(55% 0.18 25 / 0.12)",  # #c43a4b with 12% opacity */
            "purple": "oklch(55% 0.15 290)",  # #7a5fb0 - Muted purple */
            "purple-light": "oklch(95% 0.02 290)",  # #f0e8ff - Lavender */
            "purple-dim": "oklch(55% 0.15 290 / 0.12)",  # #7a5fb0 with 12% opacity */
            "electric": "oklch(75% 0.15 195)",  # #4dc9c9 - Electric teal */
            "navy": "var(--color-base-850)",  # #03320b - Obsidian almost black */
            "ink": "var(--color-base-950)",  # #001304 - True obsidian black */
        },
        "background": {
            "primary-light": "var(--color-base-50)",  # #f2ffe7 - Obsidian white */
            "primary-dark": "var(--color-base-950)",  # #001304 - True obsidian black */
            "secondary-light": "var(--color-base-100)",  # #e0ffd0 - Obsidian light */
            "secondary-dark": "var(--color-base-900)",  # #012308 - Obsidian black-green */
            "tertiary-light": "var(--color-base-200)",  # #c5ffb1 - Obsidian soft */
            "tertiary-dark": "var(--color-base-850)",  # #03320b - Obsidian almost black */
            "elevated-light": "oklch(100% 0 0)",  # #ffffff - Pure white */
            "elevated-dark": "var(--color-base-800)",  # #074110 - Obsidian deeper */
        },
        "border": {
            "light-light": "var(--color-base-200)",  # #c5ffb1 - Obsidian soft */
            "light-dark": "var(--color-base-700)",  # #115a16 - Obsidian dark */
            "strong-light": "var(--color-base-400)",  # #72d458 - Obsidian green */
            "strong-dark": "var(--color-base-600)",  # #247b1f - Obsidian deep */
        },
        "text": {
            "primary-light": "var(--color-base-900)",  # #012308 - Obsidian black-green */
            "primary-dark": "var(--color-base-100)",  # #e0ffd0 - Obsidian light */
            "secondary-light": "var(--color-base-700)",  # #115a16 - Obsidian dark */
            "secondary-dark": "var(--color-base-300)",  # #a1f58a - Obsidian medium */
            "tertiary-light": "var(--color-base-500)",  # #46a735 - Obsidian forest */
            "tertiary-dark": "var(--color-base-400)",  # #72d458 - Obsidian green */
            "inverse-light": "var(--color-base-950)",  # #001304 - True obsidian black */
            "inverse-dark": "var(--color-base-50)",  # #f2ffe7 - Obsidian white */
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
                "title": _("Operations"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Deliverymen"),
                        "icon": "local_shipping",
                        "link": reverse_lazy("admin:ops_deliveryman_changelist"),
                    },
                ],
            },
            {
                "title": _("Addresses"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Locations"),
                        "icon": "location_on",
                        "link": reverse_lazy("admin:addresses_location_changelist"),
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
                "title": _("Marketing"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Email Campaigns"),
                        "icon": "campaign",
                        "link": reverse_lazy("admin:email_marketing_emailcampaign_changelist"),
                    },
                ],
            },
            {
                "title": _("Stores"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Stores"),
                        "icon": "store",
                        "link": reverse_lazy("admin:stores_store_changelist"),
                    },
                ],
            },
            {
                "title": _("Catalog"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Categories"),
                        "icon": "category",
                        "link": reverse_lazy("admin:catalog_category_changelist"),
                    },
                    {
                        "title": _("Pills"),
                        "icon": "medication",
                        "link": reverse_lazy("admin:catalog_pills_changelist"),
                    },
                    {
                        "title": _("Products"),
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:catalog_product_changelist"),
                    },
                    {
                        "title": _("Favorites"),
                        "icon": "favorite",
                        "link": reverse_lazy("admin:catalog_productfavorite_changelist"),
                    },
                ],
            },
            {
                "title": _("Ratings"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Ratings"),
                        "icon": "star",
                        "link": reverse_lazy("admin:orders_rating_changelist"),
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
            {
                "title": _("Orders"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Orders"),
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:orders_order_changelist"),
                    },
                    {
                        "title": _("Order Items"),
                        "icon": "list_alt",
                        "link": reverse_lazy("admin:orders_orderitem_changelist"),
                    },
                    {
                        "title": _("Cart"),
                        "icon": "shopping_cart",
                        "link": reverse_lazy("admin:orders_cart_changelist"),
                    },
                    {
                        "title": _("Coupons"),
                        "icon": "confirmation_number",
                        "link": reverse_lazy("admin:orders_coupon_changelist"),
                    },
                    {
                        "title": _("Discounts"),
                        "icon": "percent",
                        "link": reverse_lazy("admin:orders_discount_changelist"),
                    },
                    {
                        "title": _("Delivery Snapshots"),
                        "icon": "location_on",
                        "link": reverse_lazy("admin:orders_orderdeliverysnapshot_changelist"),
                    },
                    {
                        "title": _("Preparation Photos"),
                        "icon": "camera_alt",
                        "link": reverse_lazy("admin:orders_orderpreparationphoto_changelist"),
                    },
                    {
                        "title": _("Status Events"),
                        "icon": "timeline",
                        "link": reverse_lazy("admin:orders_orderstatusevent_changelist"),
                    },
                    {
                        "title": _("Assignment Logs"),
                        "icon": "swap_horiz",
                        "link": reverse_lazy("admin:orders_driverassignmentlog_changelist"),
                    },
                    {
                        "title": _("Pricing Config"),
                        "icon": "price_change",
                        "link": reverse_lazy("admin:orders_pricingconfig_changelist"),
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
