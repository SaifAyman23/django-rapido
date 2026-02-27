"""
Database configuration.
PostgreSQL setup with connection pooling.
"""
import os

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DB_NAME", "project_db"),
        "USER": os.getenv("DB_USER", "project_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password123"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
        }
    }
}

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }


# Testing configuration
TESTING = os.getenv("TESTING", "False") == "True"
if TESTING:
    DATABASES["default"]["NAME"] = os.getenv("TEST_DATABASE_NAME", "project_test_db")

