# This forces the Celery app to be loaded whenever Django starts.
# Without this, @shared_task decorators on tasks may not register correctly
# because the Celery app hasn't been initialized before the worker
# starts consuming tasks.
from .celery import app as celery_app

__all__ = ("celery_app",)