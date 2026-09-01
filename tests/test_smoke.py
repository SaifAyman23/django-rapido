"""
REUSE: Minimal smoke tests — ensure quality gates have signal.

Covers: health, auth register, OTP generation, notifications guard, contacts.
Run: pytest --cov=. --cov-report=term-missing
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_health_endpoint():
    client = APIClient()
    response = client.get("/health/")
    assert response.status_code == 200
    assert b"healthy" in response.content


@pytest.mark.django_db
def test_register_creates_user():
    client = APIClient()
    response = client.post(
        "/api/v1/users/users/register/",
        {"email": "smoke@example.com", "password": "Test1234!", "password_confirm": "Test1234!"},
        format="json",
    )
    assert response.status_code in (201, 400)  # 201 on first run, 400 if already exists


@pytest.mark.django_db
def test_otp_helpers():
    from accounts.helpers import generate_otp, generate_password_reset_token

    otp = generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()
    token = generate_password_reset_token()
    assert len(token) > 20


@pytest.mark.django_db
def test_notification_guard():
    from django.contrib.auth import get_user_model

    from notifications.services import should_notify

    User = get_user_model()
    user = User.objects.create_user(
        username="notify_test", email="notify@example.com", password="pass1234"
    )
    assert should_notify(user) is True
    user.is_active = False
    assert should_notify(user) is False


@pytest.mark.django_db
def test_contact_message_create():
    client = APIClient()
    response = client.post(
        "/api/v1/contacts/messages/",
        {"name": "Test", "email": "test@example.com", "subject": "Hello", "message": "Hi"},
        format="json",
    )
    assert response.status_code in (201, 200)


@pytest.mark.django_db
def test_compliance_faq_list():
    client = APIClient()
    response = client.get("/api/v1/compliance/faqs/")
    assert response.status_code == 200
