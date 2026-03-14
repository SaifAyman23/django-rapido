from django.db import models
from common.models import TimestampedModel, UUIDModel
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
# from django.contrib.postgres.fields import ArrayField 

User = get_user_model()

# Create your models here.
class OTPRecord(TimestampedModel):

    class OTPType(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", _("Email Verification")
        PASSWORD_RESET = "password_reset", _("Password Reset")

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    type = models.CharField(max_length=20, choices=OTPType.choices)
    attempts = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.otp}"


class PasswordResetToken(TimestampedModel, UUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.id}"

    
class UserPreferences(TimestampedModel):

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", _("Full Time")
        PART_TIME = "part_time", _("Part Time")
        CONTRACT = "contract", _("Contract")
        TEMPORARY = "temporary", _("Temporary")
        INTERNSHIP = "internship", _("Internship")
        OTHER = "other", _("Other")
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    job_titles = models.JSONField(default=list)
    # job_titles = ArrayField(CharField(max_length=100)) # for future
    job_types = models.JSONField(default=list, choices=JobType.choices)
    locations = models.JSONField(default=list)
    
    