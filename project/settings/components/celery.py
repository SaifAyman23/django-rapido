"""
Celery configuration for async task processing.
Redis as message broker and result backend.
"""
import os

# Celery Configuration (5.6.2)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://:redis_password@localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://:redis_password@localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE", "UTC")
CELERY_TASK_TRACK_STARTED = os.getenv("CELERY_TASK_TRACK_STARTED", "True") == "True"
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "1800"))  # 30 minutes
CELERY_RESULT_EXPIRES = 3600  # 1 hour
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_HEARTBEAT = 0

# Flower (Celery Monitoring)
FLOWER_USER = os.getenv("FLOWER_USER", "admin")
FLOWER_PASSWORD = os.getenv("FLOWER_PASSWORD", "admin123")