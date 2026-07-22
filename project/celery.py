import os
from celery import Celery

# Tell Python which Django settings module to use before the Celery app is created.
# Without this, importing Django models inside tasks will fail.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

# Create the Celery application instance.
# The string "project" is the app name — it appears in task names and log output.
app = Celery("project")

# Pull Celery configuration from Django's settings.py.
# namespace="CELERY" means every setting in settings.py that starts with
# CELERY_ is treated as a Celery config key.
# Example: CELERY_BROKER_URL → broker_url internally.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Scan all apps in INSTALLED_APPS and auto-import their tasks.py files.
# Without this, you'd have to manually import every tasks.py.
app.autodiscover_tasks()