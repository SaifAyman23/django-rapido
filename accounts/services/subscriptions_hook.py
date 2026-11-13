"""Subscriptions hook — trial assignment boundary.

The subscriptions app is not part of the auth/onboarding pass. Keeping this
single call site means the future ``assign_plan(account, Pro, source=TRIAL,
ends_at=now+7d)`` hook (with trial-history check across ``account.user.accounts``)
lands in one place instead of being scattered through registration.
"""

import logging

logger = logging.getLogger(__name__)


def on_account_created(account) -> None:
    """Called inside the Account-creation transaction. No-op for now."""
    logger.debug(
        "subscriptions_hook: account=%s role=%s (trial assignment deferred)",
        account.pk,
        account.role,
    )


def on_account_deleted(account) -> None:
    """Called before an Account is removed. No-op for now."""
    logger.debug("subscriptions_hook: account=%s deleted", account.pk)


def on_account_verified(account, user) -> None:
    """Called once an Account's email is verified. No-op for now.

    Wire plan/trial assignment here when a billing app is added, so the auth
    services never import a concrete subscriptions implementation.
    """
    logger.debug("subscriptions_hook: account=%s verified user=%s", account.pk, user.pk)
