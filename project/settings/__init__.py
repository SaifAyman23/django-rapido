"""Settings loader for different environments"""
import os
from django.conf import settings

ENVIRONMENT = os.getenv("DJANGO_ENVIRONMENT", "local")

if ENVIRONMENT == "production":
    from .production import *  # noqa
else:
    from .local import *  # noqa