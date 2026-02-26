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
    "SITE_SUBHEADER": _("Unfold demo project"),
    "SITE_SYMBOL": "dashboard",
    "SITE_ICON": lambda request: static("dashboard/images/logo.svg"),
    # "SITE_URL": None,
    "SITE_DROPDOWN": [
        {
            "icon": "diamond",
            "title": _("Unfold theme repository"),
            "link": "https://github.com/unfoldadmin/django-unfold",
        },
        {
            "icon": "rocket_launch",
            "title": _("Turbo boilerplate repository"),
            "link": "https://github.com/unfoldadmin/turbo",
        },
        {
            "icon": "description",
            "title": _("Technical documentation"),
            "link": "https://unfoldadmin.com/docs/",
        },
    ],
    # "SHOW_HISTORY": True,
    "SHOW_LANGUAGES": True,
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
        # lambda request: static("css/styles.css"),
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


# =====================================================================
# CALLBACK FUNCTIONS - Implement these in your app
# =====================================================================

def dashboard_callback(request, context):
    """
    Prepare custom variables for the dashboard/index template.
    
    You can override templates/admin/index.html with your custom dashboard.
    
    Args:
        request: HttpRequest object
        context: Context dict from admin index view
        
    Returns:
        Modified context dict
    """
    context.update(
        {
            "app_list": context.get("app_list", []),
            # Add your custom variables here
            # "recent_items": get_recent_items(),
        }
    )
    return context


def environment_callback(request):
    """
    Return environment label and color for the top-right corner badge.
    
    This helps distinguish between development, staging, and production.
    
    Returns:
        [label_text: str, color_type: str]
        
    Color types: "info", "warning", "danger", "success"
    """
    import os
    env = os.getenv("DJANGO_ENVIRONMENT", "development")
    
    if env == "production":
        return ["Production", "danger"]
    elif env == "staging":
        return ["Staging", "warning"]
    else:
        return ["Development", "info"]


def environment_title_prefix_callback(request):
    """
    Return prefix text for the browser title tag.
    
    Example: "[Production] Django Admin"
    
    Returns:
        Prefix string or empty string
    """
    import os
    env = os.getenv("DJANGO_ENVIRONMENT", "development")
    
    if env != "production":
        return f"[{env.upper()}]"
    return ""


def dashboard_badge_callback(request):
    """
    Return badge count for dashboard navigation item.
    
    Returns:
        Integer count or None to hide badge
    """
    # Example: Return count of pending tasks
    # from myapp.models import Task
    # return Task.objects.filter(status="pending").count()
    return None


def permission_callback(request):
    """
    Example permission callback for sidebar items.
    
    Returns:
        Boolean indicating if item should be visible
    """
    return request.user.is_superuser