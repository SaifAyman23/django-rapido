"""JWT authentication bound to one Account.

Every access token carries an ``account_id`` claim (see ``services.tokens``).
This class resolves it into ``request.active_account`` and ``user.active_account``
so permissions (``IsClient`` / ``IsCoach`` / ``HasCompletedOnboarding``) never
read a role from the User (QOOT-001 §1.5).
"""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import Account
from common.rls import set_context


class AccountJWTAuthentication(JWTAuthentication):
    """Resolve the token's Account and attach it to the request."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result
        account = self._resolve_account(user, validated_token.get("account_id"))

        user.active_account = account
        request.active_account = account
        set_context(user.pk, account.pk)
        return user, validated_token

    @staticmethod
    def _resolve_account(user, account_id):
        accounts = Account.objects.filter(user=user, is_active=True).select_related(
            "client_profile", "coach_profile"
        )

        if account_id:
            account = accounts.filter(pk=account_id).first()
            if account is None:
                # Never silently fall back to another account: that would switch
                # the data boundary behind the client's back.
                raise AuthenticationFailed("Account for this token no longer exists.")
            return account

        # Tokens issued before multi-account support (no claim) use the first account.
        return accounts.order_by("created_at").first()
