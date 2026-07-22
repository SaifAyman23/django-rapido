from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.conf.urls.i18n import i18n_patterns

api_prefix = 'api/v1'

urlpatterns = (
    [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
        path("health/", lambda request: HttpResponse("healthy"), name="health"),
        path(f'{api_prefix}/users/', include('accounts.urls'), name='users'),
    ] + i18n_patterns(
        path('i18n/', include('django.conf.urls.i18n')),
        path('admin/', admin.site.urls),
    )
)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
