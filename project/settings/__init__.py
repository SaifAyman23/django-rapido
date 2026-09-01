"""Settings package entry point.

Loads base settings then overlays environment-specific overrides.
"""

# Import base settings first
import os

from .base import *

# Log active environment on boot for DX visibility.
if DEBUG:
    print(f"[settings] Loading environment: {ENVIRONMENT} (DEBUG={DEBUG}, TESTING={TESTING})")

# Load environment-specific settings LAST (after all components)
if ENVIRONMENT == "production":
    from .production import *  # noqa: F403,F401
else:
    from .local import *  # noqa: F403,F401
