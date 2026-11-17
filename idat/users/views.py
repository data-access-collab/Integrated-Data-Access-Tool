from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.account.decorators import reauthentication_required
from allauth.account.views import ConfirmEmailView, EmailVerificationSentView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

from idat.users.adapters import VERIFICATION_EMAIL_KEY
from idat.users.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest, HttpResponse


class UserDetailView(LoginRequiredMixin, DetailView):
    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["first_name", "last_name", "orcid"]  # e-mail changes go through allauth
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail")


user_redirect_view = UserRedirectView.as_view()


class VerificationSentView(EmailVerificationSentView):
    """
    allauth's "Check your inbox" page, plus the address the link went to (stored
    in the session by AccountAdapter when it sends the e-mail).
    """

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["email"] = self.request.session.get(VERIFICATION_EMAIL_KEY, "")
        return context


verification_sent_view = VerificationSentView.as_view()


class ConfirmEmailChangeView(ConfirmEmailView):
    """
    allauth's confirm page for verification links, stricter for e-mail changes.

    A link proves only control of the mailbox. For a change (the address isn't the
    account's primary one: ACCOUNT_CHANGE_EMAIL adds the new address next to it),
    the switch also needs the account itself:
    - signed in to the account the address belongs to: otherwise sign in first
      (with 2FA) and come back.
    - a recent password or 2FA confirmation (allauth's reauthentication_required,
      ACCOUNT_REAUTHENTICATION_TIMEOUT).
    Signup links (the primary address) are unchanged: no sign-in needed.
    This is what lets MFA_ALLOW_UNVERIFIED_EMAIL lift allauth.mfa's block.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            confirmation = self.get_object()
        except Http404:
            # expired, invalid or used: allauth's view shows that state
            return super().dispatch(request, *args, **kwargs)
        address = confirmation.email_address
        if address.primary:
            return super().dispatch(request, *args, **kwargs)

        if request.user.is_authenticated and request.user.pk != address.user_id:
            self.logout()
        if not request.user.is_authenticated:
            messages.info(request, _("Sign in to confirm your new e-mail address."))
            return redirect_to_login(request.get_full_path())
        view = reauthentication_required(super().dispatch)
        return view(request, *args, **kwargs)


confirm_email_change_view = ConfirmEmailChangeView.as_view()
