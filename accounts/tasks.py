"""Celery tasks for accounts app"""
from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email(self, user_id: str, email: str):
    """Send verification email with retry logic"""
    try:
        user = User.objects.get(id=user_id)
        subject = "Verify your email"
        message = f"Please verify your email: http://localhost:8000/verify/{user_id}/"
        
        send_mail(
            subject,
            message,
            "noreply@example.com",
            [email],
            fail_silently=False,
        )
        logger.info(f"Verification email sent to {email}")
        return {"status": "success"}
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {"status": "error"}
    except Exception as exc:
        logger.error(f"Error sending email: {str(exc)}")
        raise self.retry(exc=exc)