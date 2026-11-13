"""OTP engine — issue, hash, and verify 6-digit email codes.

Rules encoded here (never in views):
- Codes are 6 digits generated with ``secrets.randbelow``.
- Only ``HMAC-SHA256(SECRET_KEY, "<purpose>:<code>")`` is stored.
- The newest unconsumed row per ``(user, email, purpose)`` is the only valid code.
- Issuing a new code consumes every earlier unconsumed code of the same target.
- Resend cooldown, TTL, attempt limit, and hourly cap come from settings.
"""

import hmac
import logging
import secrets
from datetime import timedelta
from hashlib import sha256

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import EmailOTP
from common.helpers import generate_otp_code

generate_code = generate_otp_code
from accounts.services.guards import normalize_email
from common.exceptions import (
    CodeExpiredError,
    InvalidCodeError,
    ThrottledError,
    TooManyAttemptsError,
)

logger = logging.getLogger(__name__)


def _target_email(user, email) -> str:
    """Resolve the mailbox a code belongs to (explicit target wins)."""
    return normalize_email(email) or normalize_email(getattr(user, "email", ""))


def _scoped(user, purpose: str, email):
    """Base queryset for one user/purpose, optionally narrowed to one mailbox."""
    queryset = EmailOTP.objects.filter(user=user, purpose=str(purpose))
    target = normalize_email(email)
    if target:
        queryset = queryset.filter(email__iexact=target)
    return queryset


def hash_code(code: str, purpose: str) -> str:
    """Return the HMAC-SHA256 hex digest stored in ``EmailOTP.code_hash``."""
    message = f"{purpose}:{code}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), message, sha256).hexdigest()


def seconds_until_resend(user, purpose: str, *, email=None) -> int:
    """Seconds left before a new code may be requested (0 when allowed)."""
    latest = _scoped(user, purpose, email).order_by("-created_at").first()
    if latest is None:
        return 0
    elapsed = (timezone.now() - latest.created_at).total_seconds()
    remaining = settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed
    return max(0, int(remaining))


def issue_otp(
    user,
    purpose: str,
    *,
    email=None,
    enforce_cooldown: bool = True,
    metadata: dict | None = None,
) -> EmailOTP:
    """Create a new code, invalidate earlier ones, and return the stored row.

    ``email`` is the mailbox that receives the code and the scope that keeps
    concurrent flows (for example two add-account requests) independent.

    The plaintext code is attached to the returned instance as ``plaintext_code``
    so the caller can hand it to the Celery task without ever persisting it.

    Raises ``ThrottledError`` when the resend cooldown or hourly cap is hit.
    """
    now = timezone.now()
    purpose = str(purpose)
    target = _target_email(user, email)

    if enforce_cooldown:
        remaining = seconds_until_resend(user, purpose, email=target)
        if remaining:
            raise ThrottledError(context={"retry_after": remaining})

    last_hour = now - timedelta(hours=1)
    hourly_count = _scoped(user, purpose, target).filter(created_at__gte=last_hour).count()
    if hourly_count >= settings.OTP_MAX_PER_HOUR:
        raise ThrottledError(context={"retry_after": 3600})

    code = generate_otp_code()
    otp = EmailOTP.objects.create(
        user=user,
        email=target,
        purpose=purpose,
        code_hash=hash_code(code, purpose),
        expires_at=now + timedelta(minutes=settings.OTP_TTL_MINUTES),
        metadata=metadata or {},
    )
    # Only the newest code for this user, mailbox, and purpose stays valid.
    _scoped(user, purpose, target).filter(consumed_at__isnull=True).exclude(pk=otp.pk).update(
        consumed_at=now
    )

    otp.plaintext_code = code  # transient, never saved
    return otp


def _record_failed_attempt(otp: EmailOTP) -> int:
    """Increment the attempt counter and return the new value.

    Runs in its own autocommit statement on purpose: the caller raises a
    422 immediately afterwards, so the count must survive that failure
    (``select_for_update`` + rollback would silently reset it).
    """
    EmailOTP.objects.filter(pk=otp.pk).update(attempts=F("attempts") + 1)
    otp.refresh_from_db(fields=["attempts"])
    return otp.attempts


def verify_otp(user, purpose: str, code: str, *, email=None) -> EmailOTP:
    """Validate ``code`` for ``user`` and ``email`` and consume it on success.

    Failure paths must persist the attempt counter, so callers must NOT wrap
    this call in a long-lived ``transaction.atomic()`` block. The success path
    opens its own short transaction and locks the row.
    """
    purpose = str(purpose)
    otp = _scoped(user, purpose, email).order_by("-created_at").first()

    if otp is None or otp.consumed_at is not None:
        raise InvalidCodeError()

    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise TooManyAttemptsError()

    if otp.expires_at <= timezone.now():
        raise CodeExpiredError()

    if not hmac.compare_digest(otp.code_hash, hash_code(code, purpose)):
        attempts = _record_failed_attempt(otp)
        if attempts >= settings.OTP_MAX_ATTEMPTS:
            EmailOTP.objects.filter(pk=otp.pk).update(consumed_at=timezone.now())
            raise TooManyAttemptsError()
        raise InvalidCodeError(context={"attempts_remaining": settings.OTP_MAX_ATTEMPTS - attempts})

    with transaction.atomic():
        locked = EmailOTP.objects.select_for_update().get(pk=otp.pk)
        if locked.consumed_at is not None:
            raise InvalidCodeError()
        if locked.expires_at <= timezone.now():
            raise CodeExpiredError()
        if not hmac.compare_digest(locked.code_hash, hash_code(code, purpose)):
            # A concurrent request already consumed/replaced this row.
            raise InvalidCodeError()
        locked.consumed_at = timezone.now()
        locked.save(update_fields=["consumed_at", "updated_at"])

    return locked


def queue_otp_email(otp: EmailOTP) -> None:
    """Dispatch the code through Celery, retrying delivery separately.

    Delivery problems are logged, never raised: the account already exists by
    the time this runs, so a mail outage must not turn a successful signup into
    a 500.
    """
    from accounts.tasks import send_otp_email

    try:
        send_otp_email.delay(str(otp.pk), otp.plaintext_code)
    except Exception:
        logger.exception("Could not queue the OTP email otp=%s", otp.pk)
