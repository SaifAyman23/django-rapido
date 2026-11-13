"""Serializers for the provider-agnostic social-login endpoint."""

from rest_framework import serializers

from common.serializers import StrictSerializer

from accounts.serializers import RoleField


class SocialLoginRequestSerializer(StrictSerializer):
    """Accepted token and PKCE fields for Google and Facebook login."""

    code = serializers.CharField(required=False, allow_blank=False)
    code_verifier = serializers.CharField(required=False, allow_blank=False)
    redirect_uri = serializers.URLField(required=False, allow_blank=False)
    id_token = serializers.CharField(required=False, allow_blank=False)
    access_token = serializers.CharField(required=False, allow_blank=False)
    role = RoleField(required=False)
    device_uuid = serializers.CharField(required=False, allow_blank=False)


class SocialLoginResponseSerializer(serializers.Serializer):
    """JWT response returned after the provider login is completed."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    onboarding_required = serializers.BooleanField()


class SocialLoginErrorSerializer(serializers.Serializer):
    """Error detail returned by the social-login endpoint."""

    detail = serializers.CharField()
