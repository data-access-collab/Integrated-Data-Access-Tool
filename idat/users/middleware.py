from __future__ import annotations

import time
from typing import TYPE_CHECKING

from allauth.mfa.models import Authenticator
from allauth.mfa.utils import is_mfa_enabled
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from django.http import HttpRequest, HttpResponse

MFA_REQUIRED_MESSAGE = _(
    "Staff accounts need two-factor authentication. Set it up to use the admin.",
)
LAST_ACTIVITY_KEY = "staff_last_activity"


def has_second_factor(user: AbstractBaseUser | AnonymousUser) -> bool:
    """TOTP or a security key/passkey; recovery codes alone don't count."""
    types = [Authenticator.Type.TOTP, Authenticator.Type.WEBAUTHN]
    return is_mfa_enabled(user, types=types)


class StaffSecurityMiddleware:
    """
    For logged-in staff:
    - they are logged out after STAFF_SESSION_IDLE_TIMEOUT seconds without a
      request. Tracked in the session, so the cookie lifetime stays as allauth's
      "Remember me" set it (browser close, or SESSION_COOKIE_AGE),
    - the admin is only reachable with a second factor; without one they are
      sent to the MFA page.
    Goes after AuthenticationMiddleware and MessageMiddleware.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        if user.is_authenticated and user.is_staff:
            last_activity = request.session.get(LAST_ACTIVITY_KEY)
            idle = time.time() - last_activity if last_activity else 0
            if idle > settings.STAFF_SESSION_IDLE_TIMEOUT:
                logout(request)
                messages.info(request, _("You were logged out after inactivity."))
            elif request.path.startswith(
                reverse("admin:index"),
            ) and not has_second_factor(user):
                messages.warning(request, MFA_REQUIRED_MESSAGE)
                return redirect("mfa_index")

        response = self.get_response(request)

        # request.user is re-read: a login or logout in this request changes it
        if request.user.is_authenticated and request.user.is_staff:
            request.session[LAST_ACTIVITY_KEY] = int(time.time())
        return response
