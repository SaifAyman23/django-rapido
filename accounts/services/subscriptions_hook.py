"""Subscriptions hook — QOOT-011 trial assignment boundary.

The subscriptions app is not part of the auth/onboarding pass. Keeping this
single call site means the future ``assign_plan(account, Pro, source=TRIAL,
ends_at=now+7d)`` hook (with trial-history check across ``account.user.accounts``)
lands in one place instead of being scattered through registration.
"""

import logging

logger = logging.getLogger(__name__)


def on_account_created(account) -> None:
    """Called inside the Account-creation transaction. No-op until QOOT-011."""
    logger.debug(
        "subscriptions_hook: account=%s role=%s (trial assignment deferred to QOOT-011)",
        account.pk,
        account.role,
    )


def on_account_deleted(account) -> None:
    """Called before an Account is removed. No-op until QOOT-011."""
    logger.debug("subscriptions_hook: account=%s deleted", account.pk)
