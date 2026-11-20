from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from idat.users.models import User as UserModel

if TYPE_CHECKING:
    from idat.users.models import User


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == "/users/my-account/"


@pytest.mark.parametrize(
    ("first_name", "last_name", "email", "expected"),
    [
        ("ada", "Lovelace", "ada@example.com", "AL"),
        ("Beda", "", "ada@example.com", "B"),
        ("", "", "ada@example.com", "A"),
    ],
)
def test_user_initials(first_name: str, last_name: str, email: str, expected: str):
    user = UserModel(first_name=first_name, last_name=last_name, email=email)
    assert user.initials == expected


@pytest.mark.parametrize(
    ("first_name", "last_name", "expected"),
    [
        ("Jana", "Doe", "Jana D."),
        ("Jana", "", "Jana"),
        ("", "Doe", "jana@example.com"),
    ],
)
def test_user_display_name(first_name: str, last_name: str, expected: str):
    user = UserModel(
        first_name=first_name, last_name=last_name, email="jana@example.com"
    )
    assert user.display_name == expected
