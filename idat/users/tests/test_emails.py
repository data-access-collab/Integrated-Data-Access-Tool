from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

from idat.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from django.core.mail import EmailMultiAlternatives
    from django.test import Client

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-test-passphrase-for-emails"


@pytest.fixture(autouse=True)
def _clear_rate_limits() -> None:
    cache.clear()


def html_of(msg: EmailMultiAlternatives) -> str:
    [(html, mimetype)] = msg.alternatives
    assert mimetype == "text/html"
    return html


def test_signup_verification_email(client: Client):
    client.post(
        reverse("account_signup"),
        {
            "first_name": "Jana",
            "last_name": "Doe",
            "email": "jana@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "terms": "on",
        },
    )
    [msg] = mail.outbox
    assert msg.subject == "Confirm your e-mail address"
    # unverified address: the name came from whoever signed up, so it's left out
    assert msg.body.startswith("Hi,")
    html = html_of(msg)
    assert "Jana" not in html
    assert "Confirm e-mail address</a>" in html  # the button
    assert "/accounts/confirm-email/" in html


@pytest.mark.parametrize(("verified", "greeting"), [(True, "Hi Ada,"), (False, "Hi,")])
def test_password_reset_email(client: Client, verified: bool, greeting: str):
    user = UserFactory.create(email="ada@example.com", first_name="Ada")
    EmailAddress.objects.create(
        user=user, email=user.email, verified=verified, primary=True
    )
    client.post(reverse("account_reset_password"), {"email": user.email})
    [msg] = mail.outbox
    assert msg.subject == "Reset your password"
    assert msg.body.startswith(greeting)
    assert greeting in html_of(msg)
    assert "Choose a new password</a>" in html_of(msg)


def test_text_only_email_is_wrapped_in_the_layout(client: Client):
    """allauth's notices have no HTML template: the text goes into the layout."""
    user = UserFactory.create(first_name="Ada", password=PASSWORD)
    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )
    client.post(
        reverse("account_login"),
        {"login": user.email, "password": PASSWORD},
    )
    client.post(
        reverse("account_change_password"),
        {
            "oldpassword": PASSWORD,
            "password1": PASSWORD + "-new",
            "password2": PASSWORD + "-new",
        },
    )
    [msg] = mail.outbox
    assert msg.body.startswith("Hi Ada,")
    assert "The change was made on" in msg.body
    signature = "\n--\nIDAT (Integrated Data Access Tool)"
    assert signature in msg.body  # the text version keeps its signature
    html = html_of(msg)
    assert "Hi Ada," in html
    assert "Your password has been changed." in html
    # the layout's footer replaces the signature (its last line is text-only)
    assert "Collaboratory · dsa40collaboratory.eu" not in html
