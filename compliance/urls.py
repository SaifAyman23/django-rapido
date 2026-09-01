"""REUSE: Compliance routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ComplianceDocumentViewSet, FAQViewSet

router = DefaultRouter()
router.register(r"faqs", FAQViewSet, basename="faq")
router.register(r"documents", ComplianceDocumentViewSet, basename="compliance-document")

urlpatterns = [path("", include(router.urls))]
