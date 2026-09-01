"""Compliance views providing public FAQ and legal document endpoints."""

from rest_framework.permissions import AllowAny, IsAdminUser

from common.views import BaseViewSet

from .models import FAQ, ComplianceDocument
from .serializers import ComplianceDocumentSerializer, FAQSerializer


class FAQViewSet(BaseViewSet):
    """ViewSet for FAQs — public read, admin write."""

    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    permission_classes = [AllowAny]
    search_fields = ["question", "answer"]

    def get_queryset(self):
        """Hide unpublished FAQs from non-staff users."""
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            return qs.filter(is_published=True)
        return qs

    def get_permissions(self):
        """Restrict writes to admin users."""
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminUser()]
        return super().get_permissions()


class ComplianceDocumentViewSet(BaseViewSet):
    """ViewSet for compliance documents — public read, admin write."""

    queryset = ComplianceDocument.objects.all()
    serializer_class = ComplianceDocumentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Hide unpublished documents from non-staff users."""
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            return qs.filter(is_published=True)
        return qs

    def get_permissions(self):
        """Restrict writes to admin users."""
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminUser()]
        return super().get_permissions()
