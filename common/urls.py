"""Account URLs"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import 

app_name = 'common'

router = DefaultRouter()
# router.register(r"logs", UserViewSet, basename="logs")

urlpatterns = [
    path("", include(router.urls)),
]