from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.account.decorators import reauthentication_required
from allauth.account.views import ConfirmEmailView, EmailVerificationSentView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, UpdateView

from idat.users.adapters import VERIFICATION_EMAIL_KEY, is_email_change
from idat.users.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest, HttpResponse


class UserDetailView(LoginRequiredMixin, DetailView):
    """My account: one URL per tab (profile, affiliations, account)."""

    tab = "profile"

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user

    def get_context_data(self, **kwargs) -> dict:
        return super().get_context_data(tab=self.tab, **kwargs)


user_detail_view = UserDetailView.as_view()
user_affiliations_view = UserDetailView.as_view(tab="affiliations")
user_account_view = UserDetailView.as_view(tab="account")


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Edit name and ORCID iD.

    TODO: Not routed yet: the Profile tab isn't designed yet, and
     users/user_form.html is unstyled.
    """

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

    A link proves only control of the mailbox. For a change (is_email_change:
    ACCOUNT_CHANGE_EMAIL adds the new address next to the current one), the switch
    also needs the account itself:
    - signed in to the account the address belongs to: otherwise sign in first
      (with 2FA) and come back.
    - a recent password or 2FA confirmation (allauth's reauthentication_required,
      ACCOUNT_REAUTHENTICATION_TIMEOUT).
    Activation links (the account's only address) are unchanged: no sign-in needed.
    This is what lets MFA_ALLOW_UNVERIFIED_EMAIL lift allauth.mfa's block.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            confirmation = self.get_object()
        except Http404:
            # expired, invalid or used: allauth's view shows that state
            return super().dispatch(request, *args, **kwargs)
        address = confirmation.email_address
        if not is_email_change(address):
            return super().dispatch(request, *args, **kwargs)

        if request.user.is_authenticated and request.user.pk != address.user_id:
            self.logout()
        if not request.user.is_authenticated:
            messages.info(request, _("Sign in to confirm your new e-mail address."))
            return redirect_to_login(request.get_full_path())
        view = reauthentication_required(super().dispatch)
        return view(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        confirmation = context.get("confirmation")
        context["is_email_change"] = bool(
            confirmation and is_email_change(confirmation.email_address)
        )
        return context


confirm_email_change_view = ConfirmEmailChangeView.as_view()
