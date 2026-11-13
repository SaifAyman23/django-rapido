"""Accounts Celery tasks — OTP delivery, welcome email, session cleanup.

``send_otp_email(otp_id, code)`` receives the plaintext code as an argument
because only the HMAC hash is persisted. Retries use exponential backoff
(3 attempts), so a transient mail failure does not lose the code (QOOT-001 §2.5).
"""

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
User = get_user_model()

OTP_SUBJECTS = {
    "verify_email": _("Your Qoot verification code"),
    "reset_password": _("Your Qoot password reset code"),
    "change_email": _("Confirm your new Qoot email"),
    "add_account": _("Confirm your new Qoot account email"),
}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def send_otp_email(self, otp_id: str, code: str) -> dict:
    """Send one 6-digit code. Idempotent: skips consumed or expired rows."""
    from accounts.models import EmailOTP

    otp = EmailOTP.objects.select_related("user").filter(pk=otp_id).first()
    if otp is None:
        logger.warning("OTP %s not found; nothing to send", otp_id)
        return {"status": "missing"}
    if otp.consumed_at is not None or otp.expires_at <= timezone.now():
        logger.info("OTP %s is no longer valid; skipping send", otp_id)
        return {"status": "stale"}

    user = otp.user
    subject = OTP_SUBJECTS.get(otp.purpose, _("Your Qoot code"))
    minutes = settings.OTP_TTL_MINUTES
    expiry_note = _("Use this code to continue. It expires in %(minutes)s minutes.") % {
        "minutes": minutes
    }
    html_content = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f8fafc;">
          <div style="max-width:480px;margin:32px auto;padding:24px;
                      background:#fff;border-radius:12px;">
            <h2 style="margin:0 0 12px;color:#14532d;">{_("Qoot")}</h2>
            <p style="font-size:16px;color:#1f2937;">
              {expiry_note}
            </p>
            <p style="font-size:32px;letter-spacing:8px;font-weight:700;
                      color:#166534;text-align:center;margin:24px 0;">{code}</p>
            <p style="font-size:13px;color:#6b7280;">
              {_("If you did not request this code, you can ignore this email.")}
            </p>
          </div>
        </body>
        </html>
    """
    message = EmailMultiAlternatives(
        subject=str(subject),
        body=f"{code}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[otp.email or user.email],
    )
    message.attach_alternative(html_content, "text/html")
    message.send()

    logger.info("OTP email sent otp=%s user=%s purpose=%s", otp_id, user.pk, otp.purpose)
    return {"status": "sent"}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_welcome_email(self, user_id: str) -> None:
    """Welcome email after verification — guarded by notification preferences."""
    try:
        user = User.objects.get(id=user_id, is_active=True)
        try:
            from accounts.notifications import should_notify

            if not should_notify(user):
                logger.info("Skipping welcome email for user %s (notifications disabled)", user_id)
                return
        except ImportError:
            pass

        from common.helpers import send_template_email

        success = send_template_email(
            subject="Welcome!",
            template_name="emails/welcome.html",
            context={"user": user},
            recipient_list=[user.email],
        )
        if success:
            logger.info("Welcome email sent to user %s", user_id)
    except User.DoesNotExist:
        logger.warning("User %s not found for welcome email", user_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def cleanup_expired_sessions() -> int:
    """Beat task — purge expired sessions."""
    from django.contrib.sessions.models import Session

    expired = Session.objects.filter(expire_date__lt=timezone.now())
    count, _ = expired.delete()
    if count:
        logger.info("Cleaned up %d expired sessions", count)
    return count
