"""REUSE: Contact routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ContactInfoViewSet, ContactMessageViewSet

router = DefaultRouter()
router.register(r"messages", ContactMessageViewSet, basename="contact-message")
router.register(r"info", ContactInfoViewSet, basename="contact-info")

urlpatterns = [path("", include(router.urls))]
