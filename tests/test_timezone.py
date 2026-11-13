"""X-Timezone request handling: the front ends send an IANA zone name per
request, and the API must honor it during view processing only."""

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone

from common.middleware import TimezoneMiddleware


class _Anonymous:
    is_authenticated = False
    timezone = None


class _WithZone:
    is_authenticated = True
    pk = None
    timezone = "Asia/Tokyo"


factory = RequestFactory()
middleware = TimezoneMiddleware(lambda request: HttpResponse("ok"))


def _activate(request):
    middleware.process_request(request)
    return timezone.get_current_timezone_name()


def teardown_function(function):
    timezone.deactivate()


def test_iana_header_activates_zone():
    request = factory.get("/health/", HTTP_X_TIMEZONE="Africa/Cairo")
    request.user = _Anonymous()
    assert _activate(request) == "Africa/Cairo"


def test_unknown_header_is_ignored_and_falls_back_to_default():
    request = factory.get("/health/", HTTP_X_TIMEZONE="Not/AZone")
    request.user = _Anonymous()
    assert _activate(request) == settings_time_zone()


def test_header_wins_over_user_attribute():
    request = factory.get("/health/", HTTP_X_TIMEZONE="Europe/Berlin")
    request.user = _WithZone()
    assert _activate(request) == "Europe/Berlin"


def test_user_timezone_is_used_when_header_is_missing():
    request = factory.get("/health/")
    request.user = _WithZone()
    assert _activate(request) == "Asia/Tokyo"


def test_no_header_and_anonymous_stays_on_default_zone():
    request = factory.get("/health/")
    request.user = _Anonymous()
    assert _activate(request) == settings_time_zone()


def test_process_response_deactivates_zone():
    request = factory.get("/health/", HTTP_X_TIMEZONE="Africa/Cairo")
    request.user = _Anonymous()
    middleware.process_request(request)
    assert timezone.get_current_timezone_name() == "Africa/Cairo"
    middleware.process_response(request, HttpResponse("ok"))
    assert timezone.get_current_timezone_name() == settings_time_zone()


def settings_time_zone():
    return settings.TIME_ZONE
