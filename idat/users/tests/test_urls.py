from __future__ import annotations

from django.urls import resolve, reverse


def test_detail():
    assert reverse("users:detail") == "/users/my-account/"
    assert resolve("/users/my-account/").view_name == "users:detail"
