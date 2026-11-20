from __future__ import annotations

import time
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.contrib.messages import get_messages
from django.urls import reverse
from pytest_django.asserts import assertRedirects

from idat.users.middleware import (
    LAST_ACTIVITY_KEY,
    MFA_REQUIRED_MESSAGE,
    has_second_factor,
)
from idat.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from django.test import Client

    from idat.users.models import User

pytestmark = pytest.mark.django_db


def add_authenticator(user: User, type_: str) -> None:
    Authenticator.objects.create(user=user, type=type_, data={"secret": "test"})


@pytest.fixture
def staff() -> User:
    return UserFactory.create(is_staff=True)


@pytest.fixture
def staff_with_mfa(staff: User) -> User:
    add_authenticator(staff, Authenticator.Type.TOTP)
    return staff


class TestHasSecondFactor:
    @pytest.mark.parametrize(
        ("types", "expected"),
        [
            ([], False),
            ([Authenticator.Type.RECOVERY_CODES], False),
            ([Authenticator.Type.TOTP], True),
            ([Authenticator.Type.WEBAUTHN], True),
        ],
    )
    def test_counts_totp_and_webauthn_only(
        self,
        user: User,
        types: list[str],
        expected: bool,
    ):
        for type_ in types:
            add_authenticator(user, type_)
        assert has_second_factor(user) is expected


class TestAdminRequiresMfa:
    def test_staff_without_mfa_is_sent_to_mfa_page(self, client: Client, staff: User):
        client.force_login(staff)
        response = client.get(reverse("admin:index"))

        assertRedirects(response, reverse("mfa_index"), fetch_redirect_response=False)
        assert [m.message for m in get_messages(response.wsgi_request)] == [
            MFA_REQUIRED_MESSAGE,
        ]

    def test_staff_with_mfa_can_open_admin(
        self,
        client: Client,
        staff_with_mfa: User,
    ):
        client.force_login(staff_with_mfa)
        response = client.get(reverse("admin:index"))

        assert response.status_code == HTTPStatus.OK

    def test_staff_without_mfa_can_open_other_pages(
        self,
        client: Client,
        staff: User,
    ):
        client.force_login(staff)
        response = client.get(reverse("users:detail"))

        assert response.status_code == HTTPStatus.OK

    def test_regular_user_gets_normal_admin_handling(self, client: Client, user: User):
        client.force_login(user)
        response = client.get(reverse("admin:index"))

        # the admin itself turns non-staff away, not the MFA redirect
        assert response["Location"] != reverse("mfa_index")


def set_last_activity(client: Client, seconds_ago: int) -> None:
    session = client.session
    session[LAST_ACTIVITY_KEY] = int(time.time()) - seconds_ago
    session.save()


class TestStaffIdleTimeout:
    def test_records_last_activity(self, client: Client, staff_with_mfa: User):
        client.force_login(staff_with_mfa)
        client.get(reverse("users:detail"))

        assert time.time() - client.session[LAST_ACTIVITY_KEY] < 5

    def test_logs_out_after_idle_timeout(self, client: Client, staff_with_mfa: User):
        client.force_login(staff_with_mfa)
        set_last_activity(client, settings.STAFF_SESSION_IDLE_TIMEOUT + 1)

        response = client.get(reverse("users:detail"))

        assert response.status_code == HTTPStatus.FOUND  # login_required redirect
        assert "_auth_user_id" not in client.session
        assert [m.message for m in get_messages(response.wsgi_request)] == [
            "You were logged out after inactivity.",
        ]

    def test_activity_within_timeout_renews_it(
        self,
        client: Client,
        staff_with_mfa: User,
    ):
        client.force_login(staff_with_mfa)
        set_last_activity(client, settings.STAFF_SESSION_IDLE_TIMEOUT - 60)

        response = client.get(reverse("users:detail"))

        assert response.status_code == HTTPStatus.OK
        assert time.time() - client.session[LAST_ACTIVITY_KEY] < 5

    def test_keeps_remember_me_choice(self, client: Client, staff_with_mfa: User):
        client.force_login(staff_with_mfa)
        session = client.session
        session.set_expiry(0)  # "Remember me" not ticked
        session.save()

        client.get(reverse("users:detail"))

        assert client.session.get_expire_at_browser_close()

    def test_regular_user_is_not_tracked(self, client: Client, user: User):
        client.force_login(user)
        client.get(reverse("users:detail"))

        assert LAST_ACTIVITY_KEY not in client.session
