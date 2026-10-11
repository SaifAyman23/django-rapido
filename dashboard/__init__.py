"""Dashboard package — admin theme, callbacks, and live-log streaming."""

# Re-exported so dotted paths like "dashboard.dashboard_callback" (used in
# UNFOLD settings) resolve on the package itself, not just dashboard.callbacks.
from .callbacks import (
    badge_callback,
    dashboard_callback,
    environment_callback,
    permission_callback,
)

__all__ = [
    "badge_callback",
    "dashboard_callback",
    "environment_callback",
    "permission_callback",
]
