"""
REUSE: Generic SocialAccountAdapter for django-allauth.

Fixes two production bugs:
1. Duplicate SocialApp (DB + settings.APP) → MultipleObjectsReturned on get_app()
   → list_apps() dedupes, DB-backed apps win.
2. Existing local account + social login with same email → UNIQUE violation
   → pre_social_login() auto-links via EmailAddress or CustomUser.email.

From ras-elbar-go/backend/accounts/auth/adapters.py — project-agnostic.
Wire via: SOCIALACCOUNT_ADAPTER = "accounts.auth.adapters.SocialAccountAdapter"
"""

from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def list_apps(self, request, provider=None, client_id=None):
        """Dedupe provider apps between DB and settings.SOCIALACCOUNT_PROVIDERS."""
        apps = super().list_apps(request, provider=provider, client_id=client_id)
        seen_client_ids = set()
        deduped = []
        for app in apps:
            is_db_backed = app.pk is not None
            key = (app.provider, app.client_id)
            if is_db_backed:
                if key in seen_client_ids:
                    continue
                seen_client_ids.add(key)
                deduped.append(app)
            else:
                if key not in seen_client_ids:
                    seen_client_ids.add(key)
                    deduped.append(app)
        return deduped

    def pre_social_login(self, request, sociallogin):
        """Auto-link social login to existing local account by email."""
        if sociallogin.is_existing:
            return

        existing_account = SocialAccount.objects.filter(
            provider=sociallogin.account.provider,
            uid=sociallogin.account.uid,
        ).first()
        if existing_account:
            return

        email = (sociallogin.account.extra_data or {}).get("email") or ""
        email = email.lower()
        if not email:
            return

        email_address = EmailAddress.objects.filter(email__iexact=email).first()
        if email_address and email_address.user_id:
            self._link(request, sociallogin, email_address.user, email_address)
            return

        user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
        if user:
            self._link(request, sociallogin, user)

    def _link(self, request, sociallogin, user, email_address=None):
        sociallogin.connect(request, user)
        if email_address and not email_address.verified:
            email_address.verified = True
            email_address.save()
        if not user.is_active:
            user.is_active = True
            user.save()
