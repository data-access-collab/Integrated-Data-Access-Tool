from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from idat.users.forms import UserAdminChangeForm
from idat.users.tests.factories import UserFactory
from idat.users.views import UserRedirectView, UserUpdateView, user_detail_view

if TYPE_CHECKING:
    from django.test import Client, RequestFactory

    from idat.users.models import User

pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    """
    TODO:
        extracting view initialization code as class-scoped fixture
        would be great if only pytest-django supported non-function-scoped
        fixture db access -- this is a work-in-progress for now:
        https://github.com/pytest-dev/pytest-django/pull/258
    """

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request
        assert view.get_success_url() == "/users/my-account/"

    def test_get_object(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_object() == user

    def test_form_valid(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        request.user = user

        view.request = request

        # Initialize the form
        form = UserAdminChangeForm()
        form.cleaned_data = {}
        form.instance = user
        view.form_valid(form)

        messages_sent = [m.message for m in messages.get_messages(request)]
        assert messages_sent == [_("Information successfully updated")]


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user

        view.request = request
        assert view.get_redirect_url() == "/users/my-account/"


class TestUserDetailView:
    def test_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = user
        response = user_detail_view(request)

        assert response.status_code == HTTPStatus.OK

    def test_not_authenticated(self, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = user_detail_view(request)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == f"{login_url}?next=/fake-url/"


PASSWORD = "a-long-test-passphrase-for-views"


@pytest.fixture
def _clear_rate_limits() -> None:
    # allauth keeps its rate limits in the cache
    cache.clear()


@pytest.fixture
def owner() -> User:
    owner = UserFactory.create(email="owner@example.com", password=PASSWORD)
    EmailAddress.objects.create(
        user=owner,
        email=owner.email,
        verified=True,
        primary=True,
    )
    return owner


def sign_in(client: Client, user: User) -> Client:
    """A real sign-in: allauth records it, so it counts as a recent authentication."""
    response = client.post(
        reverse("account_login"),
        {"login": user.email, "password": PASSWORD},
    )
    assert response.status_code == HTTPStatus.FOUND
    return client


@pytest.mark.usefixtures("_clear_rate_limits")
class TestEmailChange:
    """Requesting an e-mail change on /accounts/email/ (allauth, change mode)."""

    def test_change_needs_recent_authentication(self, client: Client, owner: User):
        client.force_login(owner)  # not recorded by allauth: not "recent"
        response = client.post(
            reverse("account_email"),
            {"email": "new@example.com", "action_add": ""},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url.startswith(reverse("account_reauthenticate"))
        assert not EmailAddress.objects.filter(email="new@example.com").exists()

    def test_mfa_user_can_request_change(self, client: Client, owner: User):
        """allauth.mfa's block is lifted (MFA_ALLOW_UNVERIFIED_EMAIL)."""
        sign_in(client, owner)
        Authenticator.objects.create(
            user=owner,
            type=Authenticator.Type.TOTP,
            data={"secret": "x"},
        )
        client.post(
            reverse("account_email"),
            {"email": "new@example.com", "action_add": ""},
        )
        assert EmailAddress.objects.filter(
            user=owner,
            email="new@example.com",
            verified=False,
        ).exists()


@pytest.mark.usefixtures("_clear_rate_limits")
class TestConfirmEmailChangeView:
    """The link of an e-mail change only works signed in, with a recent confirmation."""

    @pytest.fixture
    def change_url(self, owner: User) -> str:
        address = EmailAddress.objects.create(
            user=owner,
            email="new@example.com",
            verified=False,
            primary=False,
        )
        key = EmailConfirmationHMAC(address).key
        return reverse("account_confirm_email", args=[key])

    def test_signed_out_is_sent_to_sign_in(self, client: Client, change_url: str):
        response = client.get(change_url)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url.startswith(reverse("account_login"))
        assert "next=" in response.url
        response = client.post(change_url)
        assert not EmailAddress.objects.get(email="new@example.com").verified

    def test_other_account_is_signed_out(
        self,
        client: Client,
        change_url: str,
    ):
        other = UserFactory.create(password=PASSWORD)
        client.force_login(other)
        response = client.post(change_url)
        assert response.url.startswith(reverse("account_login"))
        assert "_auth_user_id" not in client.session
        assert not EmailAddress.objects.get(email="new@example.com").verified

    def test_owner_without_recent_authentication_reauthenticates(
        self,
        client: Client,
        owner: User,
        change_url: str,
    ):
        client.force_login(owner)
        response = client.post(change_url)
        assert response.url.startswith(reverse("account_reauthenticate"))
        assert not EmailAddress.objects.get(email="new@example.com").verified

    def test_owner_signed_in_recently_switches(
        self,
        client: Client,
        owner: User,
        change_url: str,
    ):
        sign_in(client, owner).post(change_url)
        owner.refresh_from_db()
        assert owner.email == "new@example.com"
        assert EmailAddress.objects.get(email="new@example.com").primary

    def test_signup_link_needs_no_sign_in(self, client: Client):
        user = UserFactory.create(email="signup@example.com", password=PASSWORD)
        address = EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=False,
            primary=True,
        )
        url = reverse(
            "account_confirm_email", args=[EmailConfirmationHMAC(address).key]
        )
        client.post(url)
        address.refresh_from_db()
        assert address.verified


def test_mfa_allow_unverified_email_needs_mandatory_verification():
    """
    MFA_ALLOW_UNVERIFIED_EMAIL also lets 2FA be turned on while an address is
    unverified; only safe while unverified accounts can't sign in.
    """
    assert settings.MFA_ALLOW_UNVERIFIED_EMAIL
    assert settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory"
