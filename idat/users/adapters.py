from __future__ import annotations

import typing

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings

if typing.TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from django.forms import BaseForm
    from django.http import HttpRequest

    from idat.users.models import User


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def save_user(
        self,
        request: HttpRequest,
        user: User,
        form: BaseForm,
        commit: bool = True,  # noqa: FBT002
    ) -> User:
        """
        allauth stores email, first_name, last_name and the password; adds the ORCID iD.
        Also used by the social signup form (SocialAccountAdapter.save_user calls it).
        """
        user = super().save_user(request, user, form, commit=False)
        user.orcid = form.cleaned_data.get("orcid") or None
        if commit:
            user.save()
        return user


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
