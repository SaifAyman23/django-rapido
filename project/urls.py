"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)
from django.conf import settings
from django.conf.urls.static import static
from dashboard.views import HomeView
from django.conf.urls.i18n import i18n_patterns

api_prefix = 'api/v1'

urlpatterns = (
    [
        path(f'{api_prefix}/accounts/', include('accounts.urls'), name='accounts'),  # OpenAPI schema
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),  # OpenAPI schema
        path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
        path("", HomeView.as_view(), name="home"),
        path("__debug__/", include("debug_toolbar.urls")),
        path('i18n/', include('django.conf.urls.i18n')),
    ] + i18n_patterns(
        # Your language-specific URLs...
        path('admin/', admin.site.urls),
        # ...
    )
)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),  # 'djdt' namespace is automatically registered
    ]