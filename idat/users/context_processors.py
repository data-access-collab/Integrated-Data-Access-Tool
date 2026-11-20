from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.account import app_settings as allauth_app_settings
from django.conf import settings

if TYPE_CHECKING:
    from django.http import HttpRequest


def allauth_settings(request: HttpRequest) -> dict:
    """Expose some settings from django-allauth in templates."""
    return {
        "PASSWORD_RESET_TIMEOUT_HOURS": settings.PASSWORD_RESET_TIMEOUT // 3600,
        "EMAIL_CONFIRMATION_EXPIRE_HOURS": (
            allauth_app_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS * 24
        ),
    }
