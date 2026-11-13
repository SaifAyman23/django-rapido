"""In-app password change (QOOT-012) — signed-in flow, not the reset flow."""

import logging

from accounts.services.tokens import blacklist_other_refresh_tokens
from common.exceptions import InvalidCurrentPasswordError, PasswordNotSetError

logger = logging.getLogger(__name__)


def change_password(user, *, current_password, new_password, keep_refresh=""):
    """Verify the current password, set the new one, end other sessions."""
    if not user.has_usable_password():
        raise PasswordNotSetError()
    if not user.check_password(current_password):
        raise InvalidCurrentPasswordError()

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    blacklist_other_refresh_tokens(user, keep_raw_token=keep_refresh)
    logger.info("Password changed user=%s", user.pk)
