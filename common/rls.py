"""PostgreSQL row-level security context for the active request.

SQLite development and test databases intentionally skip the PostgreSQL
session-setting calls. Django views and services still enforce account
ownership through their normal queryset filters on those databases.
"""

from __future__ import annotations

from typing import Optional

from django.db import connection


def set_context(user_id: object, account_id: object) -> None:
    """Bind the authenticated user and active account to this DB connection."""
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_user_id', %s, false), "
            "set_config('app.current_account_id', %s, false)",
            [str(user_id), str(account_id)],
        )


def set_system_context() -> None:
    """Allow trusted staff/admin requests to access all account-owned rows."""
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.rls_bypass', 'on', false)")


def clear_context() -> None:
    """Clear request context before a persistent connection is reused."""
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_user_id', '', false), "
            "set_config('app.current_account_id', '', false), "
            "set_config('app.rls_bypass', 'off', false)"
        )


def current_setting(name: str) -> Optional[str]:
    """Return a context value, primarily for diagnostics and tests."""
    if connection.vendor != "postgresql":
        return None
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting(%s, true)", [name])
        return cursor.fetchone()[0]
