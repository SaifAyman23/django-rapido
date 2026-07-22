import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_welcome_email(self, user_id: str) -> None:
    try:
        user = User.objects.get(id=user_id, is_active=True)
        from accounts.notifications import send_template_email, should_notify

        if not should_notify(user):
            logger.info("Skipping welcome email for user %s (notifications disabled)", user_id)
            return

        success = send_template_email(
            subject="Welcome!",
            template_name="emails/welcome.html",
            context={
                "user": user,
                "site_name": getattr(user, "site_name", "Our Platform"),
            },
            recipient_list=[user.email],
        )
        if success:
            logger.info("Welcome email sent to user %s", user_id)
        else:
            logger.error("Welcome email failed for user %s", user_id)
    except User.DoesNotExist:
        logger.warning("User %s not found for welcome email", user_id)
    except Exception as exc:
        logger.exception("Error sending welcome email to user %s", user_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_password_reset(self, user_id: str, base_url: str) -> None:
    try:
        user = User.objects.get(id=user_id, is_active=True)
        from accounts.notifications import send_password_reset_email, should_notify

        if not should_notify(user):
            logger.info("Skipping password reset email for user %s (notifications disabled)", user_id)
            return

        success = send_password_reset_email(user, base_url)
        if success:
            logger.info("Password reset email sent to user %s", user_id)
        else:
            logger.error("Password reset email failed for user %s", user_id)
    except User.DoesNotExist:
        logger.warning("User %s not found for password reset", user_id)
    except Exception as exc:
        logger.exception("Error sending password reset email to user %s", user_id)
        raise self.retry(exc=exc)


@shared_task
def cleanup_expired_sessions() -> int:
    from django.contrib.sessions.models import Session

    expired = Session.objects.filter(expire_date__lt=timezone.now())
    count, _ = expired.delete()
    if count:
        logger.info("Cleaned up %d expired sessions", count)
    return count
