"""
Ultimate reusable helper functions
Provides production-grade utilities with:
- Data validation
- Format conversion
- Caching decorators
- Logging utilities
- Common operations
"""

from typing import Any, Dict, List, Optional, Tuple, TypeVar, Callable
from datetime import datetime, timedelta
import json
import logging
import hashlib
import uuid
import re
from django.db import models, transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils.text import slugify
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from .models import AudotLog

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ===========================
# Validation Helpers
# ===========================

def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def is_valid_phone(phone: str) -> bool:
    """Validate phone number"""
    pattern = r"^[\d\s\-\+\(\)]{10,}$"
    return re.match(pattern, phone) is not None


def is_valid_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return re.match(pattern, url) is not None


def is_valid_ipv4(ip: str) -> bool:
    """Validate IPv4 address"""
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"

    if not re.match(pattern, ip):
        return False

    parts = ip.split(".")
    return all(0 <= int(part) <= 255 for part in parts)


def is_strong_password(password: str) -> Tuple[bool, List[str]]:
    """Validate password strength"""
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain lowercase letters")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain uppercase letters")

    if not re.search(r"\d", password):
        errors.append("Password must contain numbers")

    if not re.search(r"[!@#$%^&*()_+-=\[\]{};:',.<>?/`~]", password):
        errors.append("Password must contain special characters")

    return len(errors) == 0, errors


# ===========================
# String Helpers
# ===========================

def truncate_string(text: str, length: int = 100, suffix: str = "...") -> str:
    """Truncate string to length"""
    if len(text) <= length:
        return text

    return text[: length - len(suffix)] + suffix


def camelcase_to_snakecase(name: str) -> str:
    """Convert camelCase to snake_case"""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snakecase_to_camelcase(name: str) -> str:
    """Convert snake_case to camelCase"""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def generate_slug(text: str, unique_id: Optional[str] = None) -> str:
    """Generate URL-friendly slug"""
    slug = slugify(text)

    if unique_id:
        slug = f"{slug}-{unique_id[:8]}"

    return slug


def mask_email(email: str) -> str:
    """Mask email for privacy"""
    local, domain = email.split("@")

    if len(local) <= 2:
        masked_local = local[0] + "*" * (len(local) - 1)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]

    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone number for privacy"""
    digits = re.sub(r"\D", "", phone)

    if len(digits) >= 4:
        return "*" * (len(digits) - 4) + digits[-4:]

    return "*" * len(digits)


# ===========================
# JSON Helpers
# ===========================

def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """Safely parse JSON with default fallback"""
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON: {str(e)}")
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """Safely serialize to JSON"""
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize JSON: {str(e)}")
        return default


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """Recursively merge two dictionaries"""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


# ===========================
# Date/Time Helpers
# ===========================

def get_date_range(days: int = 7) -> Tuple[datetime, datetime]:
    """Get date range for last N days"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    return start_date, end_date


def is_within_timeframe(timestamp: datetime, hours: int = 24) -> bool:
    """Check if timestamp is within N hours"""
    cutoff = timezone.now() - timedelta(hours=hours)
    return timestamp >= cutoff


def humanize_timedelta(td: timedelta) -> str:
    """Convert timedelta to human-readable string"""
    total_seconds = int(td.total_seconds())

    periods = [
        ("year", 60 * 60 * 24 * 365),
        ("month", 60 * 60 * 24 * 30),
        ("week", 60 * 60 * 24 * 7),
        ("day", 60 * 60 * 24),
        ("hour", 60 * 60),
        ("minute", 60),
        ("second", 1),
    ]

    for period_name, period_seconds in periods:
        if total_seconds >= period_seconds:
            period_value, remainder = divmod(total_seconds, period_seconds)
            result = f"{period_value} {period_name}"
            if period_value > 1:
                result += "s"
            return result

    return "just now"


# ===========================
# Email Helpers
# ===========================

def send_template_email(
    subject: str,
    template_name: str,
    context: Dict[str, Any],
    recipient_list: List[str],
    from_email: Optional[str] = None,
) -> bool:
    """Send email using template"""
    try:
        html_message = render_to_string(template_name, context)

        send_mail(
            subject=subject,
            message="",
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Email sent to {recipient_list} with subject '{subject}'")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}", exc_info=True)
        return False


def send_verification_email(user, token: str, base_url: str) -> bool:
    """Send email verification link"""
    verification_url = f"{base_url}/verify-email/{token}/"

    return send_template_email(
        subject="Verify your email",
        template_name="emails/verification.html",
        context={
            "user": user,
            "verification_url": verification_url,
            "token": token,
        },
        recipient_list=[user.email],
    )


def send_password_reset_email(user, base_url: str) -> bool:
    """Send password reset link"""
    token = default_token_generator.make_token(user)
    reset_url = f"{base_url}/reset-password/{user.pk}/{token}/"

    return send_template_email(
        subject="Reset your password",
        template_name="emails/password_reset.html",
        context={
            "user": user,
            "reset_url": reset_url,
        },
        recipient_list=[user.email],
    )


# ===========================
# UUID/ID Helpers
# ===========================

def generate_token(length: int = 32) -> str:
    """Generate random token"""
    return uuid.uuid4().hex[:length]


def generate_code(prefix: str = "", length: int = 6) -> str:
    """Generate random code"""
    code = uuid.uuid4().hex[:length].upper()
    if prefix:
        code = f"{prefix}-{code}"
    return code


# ===========================
# List/Dict Helpers
# ===========================

def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """Split list into chunks"""
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def flatten_list(nested_list: List[List[T]]) -> List[T]:
    """Flatten nested list"""
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def dict_to_querystring(data: Dict[str, Any]) -> str:
    """Convert dict to query string"""
    pairs = [f"{k}={v}" for k, v in data.items() if v is not None]
    return "&".join(pairs)


def extract_dict_keys(data: Dict, keys: List[str]) -> Dict:
    """Extract specific keys from dict"""
    return {k: data.get(k) for k in keys if k in data}


# ===========================
# File Helpers
# ===========================

def get_file_extension(filename: str) -> str:
    """Get file extension"""
    return filename.split(".")[-1].lower()


def is_allowed_file_type(filename: str, allowed_types: List[str]) -> bool:
    """Check if file type is allowed"""
    extension = get_file_extension(filename)
    return extension in allowed_types


def format_file_size(size_bytes: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

    return f"{size_bytes:.2f} PB"



# ===========================
# Utility Functions
# ===========================

@transaction.atomic
def bulk_soft_delete(queryset: QuerySet) -> Tuple[int, Dict[str, int]]:
    """Soft delete multiple records in a transaction"""
    count = queryset.update(deleted_at=timezone.now())
    logger.info(f"Soft deleted {count} records")
    return count, {queryset.model._meta.label: count}


@transaction.atomic
def bulk_restore(queryset: QuerySet) -> int:
    """Restore multiple soft-deleted records in a transaction"""
    count = queryset.update(deleted_at=None)
    logger.info(f"Restored {count} records")
    return count


def log_audit(
    action: str,
    instance: models.Model,
    user: Optional[CustomUser] = None,
    changes: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """
    Create audit log entry for any model instance.
    
    Args:
        action: Action performed (create, update, delete, restore, publish)
        instance: The model instance being audited
        user: User who performed the action (optional)
        changes: Dictionary of changes made (optional)
        ip_address: IP address of the request (optional)
        user_agent: User agent string (optional)
    
    Returns:
        The created AuditLog instance
    """
    audit = AuditLog.objects.create(
        action=action,
        content_object=instance,  # Pass the instance directly, not _meta.label
        object_id=str(instance.pk),  # Convert PK to string for CharField
        object_repr=str(instance),
        changes=changes or {},
        user=user,
        ip_address=ip_address,
        user_agent=user_agent or "",
    )
    logger.debug(f"Audit log created: {audit.id} for {action} on {instance}")
    return audit