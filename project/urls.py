"""Root URL configuration.

Wires API, admin, schema docs, health check, and live-log SSE endpoints.
"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from dashboard.live_logs import live_logs_page, live_logs_stream
from dashboard.views import HomeView


class SchemaView(SpectacularAPIView):
    """OpenAPI schema view excluded from the generated docs."""

    @extend_schema(exclude=True)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


api_prefix = "api/v1"

urlpatterns = [
    path("api/schema/", SchemaView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("health/", lambda request: HttpResponse("healthy"), name="health"),
    path("", HomeView.as_view(), name="home"),  # REUSE: Dashboard landing → admin redirect
    path(f"{api_prefix}/users/", include("accounts.urls"), name="users"),
    path(
        f"{api_prefix}/notifications/", include("notifications.urls"), name="notifications"
    ),  # REUSE: FCM inbox + devices
    path(
        f"{api_prefix}/contacts/", include("contacts.urls"), name="contacts"
    ),  # REUSE: public contact form
    path(
        f"{api_prefix}/compliance/", include("compliance.urls"), name="compliance"
    ),  # REUSE: FAQ + legal docs
    # REUSE: Add your app routes here:
    # path(f'{api_prefix}/catalog/', include('catalog.urls'), name='catalog'),
    # path(f'{api_prefix}/orders/', include('orders.urls'), name='orders'),
] + i18n_patterns(
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/live-logs/", live_logs_page, name="admin-live-logs"),
    path("admin/live-logs/stream/", live_logs_stream, name="admin-live-logs-stream"),
    path("admin/", admin.site.urls),
)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Fallback non-i18n SSE route so EventSource works even if JS uses /admin/... without /en/ prefix
# (live page is under i18n_patterns at /en/admin/live-logs/, but JS may request without prefix)
# Fix 4aab2ae: correct i18n URL + no-buffer nginx
urlpatterns += [
    path("admin/live-logs/", live_logs_page, name="admin-live-logs-nolang"),
    path("admin/live-logs/stream/", live_logs_stream, name="admin-live-logs-stream-nolang"),
]

# REUSE: Markdown admin widgets
urlpatterns += [path("markdownx/", include("markdownx.urls"))]

# REUSE: allauth HTML signup stub — prevents 500 when auto-signup blocked
urlpatterns += [
    path(
        "accounts/social/signup/",
        lambda request: HttpResponse(
            "Social signup via HTML not supported. Use POST /api/v1/users/auth/social/<provider>/",
            status=404,
        ),
        name="socialaccount_signup",
    ),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
