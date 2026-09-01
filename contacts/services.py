"""
REUSE: Business-hours check — gated by BUSINESS_TIME_ZONE + ContactInfo hours.

From ras-elbar-go/backend/contacts/services.py
Use in checkout/order gating: if not is_ordering_open()[0]: block
"""

import pytz
from django.conf import settings
from django.utils import timezone

from .models import ContactInfo


def is_ordering_open():
    """Return (is_open: bool, reason: str).

    REUSE: Checks ContactInfo.start_hours/end_hours against BUSINESS_TIME_ZONE.
    If no ContactInfo or no hours, assumes always open.
    """
    info = ContactInfo.objects.first()
    if not info or not info.start_hours or not info.end_hours:
        return True, "No hours configured — always open"

    tz_name = getattr(settings, "BUSINESS_TIME_ZONE", "UTC")
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC

    now_local = timezone.now().astimezone(tz)
    now_time = now_local.time()

    start = info.start_hours
    end = info.end_hours

    # Overnight window (e.g. 22:00-04:00)
    if start <= end:
        is_open = start <= now_time <= end
    else:
        is_open = now_time >= start or now_time <= end

    if is_open:
        return True, "Open"
    return False, f"Closed — hours {start} to {end} ({tz_name})"
