"""Contact views — public message submission and singleton business info."""

from rest_framework.permissions import AllowAny

from common.views import BaseViewSet

from .models import ContactInfo, ContactMessage
from .serializers import ContactInfoSerializer, ContactMessageSerializer


class ContactMessageViewSet(BaseViewSet):
    """Public endpoint for submitting contact messages (POST only)."""

    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    http_method_names = ["post", "head", "options"]


class ContactInfoViewSet(BaseViewSet):
    """Singleton business info endpoint returning the first ContactInfo record."""

    serializer_class = ContactInfoSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        """Return at most one row since ContactInfo is a singleton."""
        return ContactInfo.objects.all()[:1]
