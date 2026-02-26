from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

def dashboard_callback(request, context):
    """Inject custom data into dashboard template"""
    context.update({
        "sample": "Your Custom Dashboard Text",  # Changed from "example"
    })
    return context

def environment_callback(request):
    """Environment badge in header"""
    return ["Oh WOW", "danger"]  # [text, color]

def badge_callback(request):
    """Badge count for dashboard nav item"""
    return 3  # Returns integer for badge

def permission_callback(request):
    """Custom permission check"""
    return request.user.has_perm("common.change_customuser")
