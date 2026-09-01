"""Celery tasks for accounts app — REUSE: generic OTP email.

From ras-elbar-go/backend/accounts/tasks.py — made project-agnostic.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email(self, user_id: str, email: str, otp: str):
    """Send OTP verification email with retry.

    REUSE: Call via send_verification_email.delay(user.id, user.email, otp)
    or directly for eager mode. HTML is generic — replace branding as needed.
    """
    try:
        user = User.objects.get(id=user_id)
        to_email = user.email
        fullname = f"{user.username}"
        if user.first_name and user.last_name:
            fullname = f"{user.first_name} {user.last_name}"

        html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
            <p style="font-size: 18px; text-align: center;">{_("Dear %(fullname)s,") % {"fullname": fullname}}</p>
            <p style="font-size: 16px; text-align: center;">{_("You are receiving this email because you requested to verify your account.")}</p>
            <center>
                <p style="font-size: 16px; text-align: center;">{_("Your OTP is: %(otp)s") % {"otp": otp}}</p>
            </center>
            </body>
            </html>
            """
        subject = _("Verify Your Account")
        msg = EmailMultiAlternatives(
            subject, html_content, settings.EMAIL_HOST_USER, [to_email], [to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Verification email sent to {email}")
        return {"status": "success"}
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {"status": "error"}
    except Exception as exc:
        logger.error(f"Error sending email: {str(exc)}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_welcome_email(self, user_id: str) -> None:
    """REUSE: Welcome email after verification — uses should_notify guard if available."""
    try:
        user = User.objects.get(id=user_id, is_active=True)
        # REUSE: optional guard — skip if notifications app exists
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
    """REUSE: Beat task — purge expired sessions."""
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    expired = Session.objects.filter(expire_date__lt=timezone.now())
    count, _ = expired.delete()
    if count:
        logger.info("Cleaned up %d expired sessions", count)
    return count
