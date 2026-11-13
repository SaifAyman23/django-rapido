"""Account profile image writes (QOOT-012 profile and settings)."""

from accounts.models import Account


def set_account_avatar(account: Account, image) -> Account:
    """Replace this account's profile image."""
    account.avatar = image
    account.save(update_fields=["avatar", "updated_at"])
    return account


def clear_account_avatar(account: Account) -> Account:
    """Drop this account's profile image and its stored file."""
    if account.avatar:
        account.avatar.delete(save=False)
        account.avatar = None
        account.save(update_fields=["avatar", "updated_at"])
    return account
