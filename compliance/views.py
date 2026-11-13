"""Compliance views providing public FAQ and legal document endpoints."""

from django.http import HttpResponse, HttpResponseBadRequest
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from common.views import BaseViewSet

from .models import FAQ, ComplianceDocument, PolicyDocument
from .serializers import (
    ComplianceDocumentSerializer,
    FAQSerializer,
    PolicyAcceptanceSerializer,
    PolicyDetailSerializer,
    PolicyListSerializer,
    PolicyListWithStatusSerializer,
)


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


class PolicyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Reads are markdown-first: `?type=markdown` returns the raw markdown the
    document is stored as, with the caller's language (`content_en` /
    `content_ar`) selected by LocaleMiddleware. `?type=json` (the
    default) keeps the JSON shapes used elsewhere.
    """

    def _type_param(self):
        requested = self.request.query_params.get("type")
        if requested is None:
            return "json"
        return requested.lower()

    def list(self, request, *args, **kwargs):
        wanted = self._type_param()
        if wanted == "markdown":
            body = self._combined_markdown(self.get_queryset())
            return HttpResponse(body, content_type="text/markdown; charset=utf-8")
        if wanted != "json":
            return HttpResponseBadRequest('Query parameter "type" must be one of: json, markdown')
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        wanted = self._type_param()
        if wanted == "markdown":
            policy = self.get_object()
            return HttpResponse(policy.content, content_type="text/markdown; charset=utf-8")
        if wanted != "json":
            return HttpResponseBadRequest('Query parameter "type" must be one of: json, markdown')
        return super().retrieve(request, *args, **kwargs)

    def _combined_markdown(self, documents):
        sections = []
        for policy in documents:
            sections.append(
                f"# {policy.title}\n\n" f"*Version {policy.version}*\n\n" f"{policy.content}\n"
            )
        return "\n---\n\n".join(sections)

    queryset = PolicyDocument.objects.filter(is_published=True).order_by("sort_order", "slug")
    serializer_class = PolicyDetailSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    lookup_field = "slug"

    def get_serializer_class(self):
        user = getattr(self.request, "user", None)
        if self.action == "list" and user and user.is_authenticated:
            return PolicyListWithStatusSerializer
        if self.action == "list":
            return PolicyListSerializer
        return PolicyDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = getattr(self.request, "user", None)
        if self.action == "list" and user and user.is_authenticated:
            rows = (
                PolicyAcceptance.objects.filter(user=user)
                .order_by("-created_at")
                .values("policy_slug", "version", "created_at")
            )
            context["acceptances"] = {row["policy_slug"]: row for row in rows}
        return context

    @extend_schema(
        summary="Record consent for the current policy version",
        responses={201: PolicyAcceptanceSerializer},
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def accept(self, request, slug=None) -> Response:
        policy = self.get_object()
        acceptance, _created = PolicyAcceptance.objects.get_or_create(
            user=request.user,
            policy_slug=policy.slug,
            version=policy.version,
            defaults={
                "ip": request.META.get("REMOTE_ADDR") or None,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            },
        )
        return Response(
            PolicyAcceptanceSerializer(acceptance).data,
            status=status.HTTP_201_CREATED,
        )
