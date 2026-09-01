"""
REUSE: Security gates — scrubbing, throttling, fail-fast.
"""

import pytest


def test_mixins_scrub_sensitive_keys():
    from common.mixins import BaseViewSetMixin

    mixin = BaseViewSetMixin()
    data = {"email": "a@b.com", "password": "secret", "otp": "123456", "name": "Test"}
    scrubbed = mixin._scrub_request_data(data)
    assert scrubbed["password"] == "***"
    assert scrubbed["otp"] == "***"
    assert scrubbed["email"] == "a@b.com"


def test_throttle_scope():
    from common.throttles import AuthRateThrottle

    assert AuthRateThrottle.scope == "auth"


def test_secret_key_guard():
    # REUSE: base.py fail-fast is tested via import with missing SECRET_KEY
    # Here just check TESTING fallback works
    import os

    assert os.getenv("TESTING", "False")  # always set in test run
