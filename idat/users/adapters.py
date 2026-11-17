from __future__ import annotations

import re
import typing
from typing import Any

import css_inline
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailAlternative, EmailMessage, EmailMultiAlternatives
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from idat.users.middleware import MFA_REQUIRED_MESSAGE, has_second_factor

if typing.TYPE_CHECKING:
    from allauth.account.models import EmailAddress, EmailConfirmation
    from allauth.socialaccount.models import SocialLogin
    from django.forms import BaseForm
    from django.http import HttpRequest, HttpResponse

    from idat.users.models import User

# Session key: the address the last verification e-mail went to, for the
# "Check your inbox" page (VerificationSentView).
VERIFICATION_EMAIL_KEY = "verification_email"

# The "-- " line before the signature of the text e-mails
# (account/email/base_message.txt).
SIGNATURE_RE = re.compile(r"\n--[ \t]*\n")

# Copies the e-mail CSS into style="" attributes; the style block stays for @media.
CSS_INLINER = css_inline.CSSInliner(keep_style_tags=True)


class AccountAdapter(DefaultAccountAdapter):
    error_messages = {
        **DefaultAccountAdapter.error_messages,
        "email_password_mismatch": _("E-mail or password is not correct."),
    }

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def render_mail(
        self,
        template_prefix: str,
        email: str | list[str],
        context: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> EmailMessage:
        """E-mails with only a text template (allauth defaults) get an HTML version too:
        the text (minus its "-- " signature, the layout has a footer) inside
        account/email/base.html.
        The HTML's CSS is copied into style="" attributes because some clients
        drop <style>.
        """
        msg = super().render_mail(template_prefix, email, context, headers)
        if not isinstance(msg, EmailMultiAlternatives):
            return msg

        # allauth attaches at most one alternative: the _message.html version
        if msg.alternatives:
            html = msg.alternatives[0].content
        else:
            body = SIGNATURE_RE.split(msg.body, maxsplit=1)[0]
            html = render_to_string(
                "account/email/base.html",
                {**context, "title": msg.subject, "body": body},
                context.get("request"),
            )
        msg.alternatives = [EmailAlternative(CSS_INLINER.inline(html), "text/html")]
        return msg

    def send_notification_mail(
        self,
        template_prefix: str,
        user: User,
        context: dict[str, Any] | None = None,
        email: str | None = None,
    ) -> None:
        """allauth leaves the user out of the context; the greeting needs the name."""
        context = {"user": user, **(context or {})}
        super().send_notification_mail(template_prefix, user, context, email)

    def send_confirmation_mail(
        self,
        request: HttpRequest,
        emailconfirmation: EmailConfirmation,
        signup: bool,
    ) -> None:
        request.session[VERIFICATION_EMAIL_KEY] = emailconfirmation.email_address.email
        super().send_confirmation_mail(request, emailconfirmation, signup)

    def send_account_already_exists_mail(self, email: str) -> None:
        # Sign-up with a taken address: show the address too to not disclose the
        # information that it already exists.
        self.request.session[VERIFICATION_EMAIL_KEY] = email
        super().send_account_already_exists_mail(email)

    def confirm_email(self, request: HttpRequest, email_address: EmailAddress) -> bool:
        request.session.pop(VERIFICATION_EMAIL_KEY, None)
        return super().confirm_email(request, email_address)

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

    def add_message(  # noqa: PLR0913, PLR0917 (allauth's signature)
        self,
        request: HttpRequest,
        level: int,
        message_template: str | None = None,
        message_context: dict[str, typing.Any] | None = None,
        extra_tags: str = "",
        message: str | None = None,
    ) -> None:
        # Signed out (sign-up, or sign-in while unverified), allauth redirects to the
        # "Check your inbox" page, which names the address and the message is thus
        # unnecessary. When signed in, adding or re-verifying an address on
        # /accounts/email/, the message is the only feedback so it's kept.
        if (
            message_template == "account/messages/email_confirmation_sent.txt"
            and not request.user.is_authenticated
        ):
            return
        # After a password reset (signed out), the "Password changed" page says it
        # already. A password change while signed in keeps the message.
        if (
            message_template == "account/messages/password_changed.txt"
            and not request.user.is_authenticated
        ):
            return
        super().add_message(
            request,
            level,
            message_template,
            message_context,
            extra_tags,
            message,
        )

    def post_login(  # noqa: PLR0913
        self,
        request: HttpRequest,
        user: User,
        *,
        email_verification: str,
        signal_kwargs: dict[str, typing.Any] | None,
        email: str | None,
        signup: bool,
        redirect_url: str | None,
    ) -> HttpResponse:
        """
        Send staff without a second factor to the MFA page instead of where they
        were going (this overrides `next`, e.g. /admin/). StaffSecurityMiddleware
        keeps them out of the admin until they set one up.
        """
        response = super().post_login(
            request,
            user,
            email_verification=email_verification,
            signal_kwargs=signal_kwargs,
            email=email,
            signup=signup,
            redirect_url=redirect_url,
        )
        if user.is_staff and not has_second_factor(user):
            messages.warning(request, MFA_REQUIRED_MESSAGE)
            return redirect("mfa_index")
        return response


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
