from __future__ import annotations

from typing import TYPE_CHECKING

from allauth.account import app_settings as allauth_settings
from allauth.account.views import EmailVerificationSentView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

from idat.users.adapters import VERIFICATION_EMAIL_KEY
from idat.users.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet


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
    in the session by AccountAdapter when it sends the e-mail) and how long the
    link is valid.
    """

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["email"] = self.request.session.get(VERIFICATION_EMAIL_KEY, "")
        context["expire_hours"] = allauth_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS * 24
        return context


verification_sent_view = VerificationSentView.as_view()
