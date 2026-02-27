from django.http import HttpRequest
from typing import Dict, Any, Union, Tuple

def dashboard_callback(request: HttpRequest, context: Dict[str, Any]) -> Dict[str, Any]:
    """Inject custom data into dashboard template"""
    context["sample"] = "Your Custom Dashboard Text"
    return context

def environment_callback(request: HttpRequest) -> Tuple[str, str]:
    """Environment badge in header"""
    return ("Oh WOW", "danger")

def badge_callback(request: HttpRequest) -> int:
    """Badge count for dashboard nav item"""
    return 3

def permission_callback(request: HttpRequest) -> bool:
    """Custom permission check"""
    return request.user.has_perm("common.change_customuser")