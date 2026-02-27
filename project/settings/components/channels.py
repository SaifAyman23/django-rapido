"""
Django Channels configuration for WebSockets.
"""
import os

ASGI_APPLICATION = "project.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://:redis_password@localhost:6379/0")],
        },
    },
}