"""
Settings loader for different environments.
Loads environment variables first, then imports all components.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Determine which environment we're in
ENVIRONMENT = os.getenv('DJANGO_ENVIRONMENT', 'local')

# Load files in order of precedence
load_dotenv('.env')  # Base defaults (always loaded)

if ENVIRONMENT == 'production':
    load_dotenv('.env.production', override=True)  # Production overrides
else:
    load_dotenv('.env.local', override=True)  # Local overrides

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

# Import all settings components
from .base import *
from .components.apps import *
from .components.database import *
from .components.cache import *
from .components.celery import *
from .components.jwt import *
from .components.email import *
from .components.api import *
from .components.security import *
from .components.logging import *
from .components.channels import *
from .components.third_party import *
from .unfold_config import *

# Load environment-specific settings last (they can override anything)
if ENVIRONMENT == 'production':
    from .production import *
else:
    from .local import *