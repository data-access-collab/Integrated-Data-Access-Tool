from __future__ import annotations

import typing
from typing import Any

import css_inline
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailAlternative, EmailMessage, EmailMultiAlternatives
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from idat.users.middleware import MFA_REQUIRED_MESSAGE, has_second_factor

if typing.TYPE_CHECKING:
    from allauth.account.models import EmailConfirmation
    from django.forms import BaseForm
    from django.http import HttpRequest, HttpResponse

    from idat.users.models import User

# Session key: the address the last verification e-mail went to, for the
# "Check your inbox" page (VerificationSentView).
VERIFICATION_EMAIL_KEY = "verification_email"

# Copies the e-mail CSS into style="" attributes; the style block stays for @media.
CSS_INLINER = css_inline.CSSInliner(keep_style_tags=True)


def is_email_change(address: EmailAddress) -> bool:
    """Whether the address is a requested e-mail change rather than an activation.

    Considered a change when a different primary address exists. If no primary
    address exists, it's considered an activation.

    Note: Not `not address.primary`: allauth adds non-primary addresses for users made
    outside it (createsuperuser, the admin) when they sign in, also after their
    e-mail was edited in the admin, so a user can have several and none primary.
    """
    return (
        EmailAddress.objects.filter(user_id=address.user_id, primary=True)
        .exclude(pk=address.pk)
        .exists()
    )


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
        """
        E-mails with only a text template (allauth default) get an HTML version too.
        """
        # Greet by name only on a verified address: anyone can sign up (or change
        # their address) with someone else's address and a "name" of their choice.
        user = context.get("user")
        if (
            isinstance(email, str)
            and user
            and EmailAddress.objects.filter(
                user=user, email__iexact=email, verified=True
            ).exists()
        ):
            context = {**context, "greeting_name": user.first_name}

        msg = super().render_mail(template_prefix, email, context, headers)
        if not isinstance(msg, EmailMultiAlternatives):
            return msg

        # allauth attaches at most one alternative: the _message.html version
        if msg.alternatives:
            html = msg.alternatives[0].content
        else:
            # render text without its signature bc. the HTML layout has a footer
            body = render_to_string(
                f"{template_prefix}_message.txt",
                {**context, "without_signature": True},
                context.get("request"),
            )
            html = render_to_string(
                "account/email/base.html",
                {**context, "title": msg.subject, "body": body},
                context.get("request"),
            )

        # HTML's CSS is copied into style-attributes bc. some clients drop <style>.
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
        address = emailconfirmation.email_address
        request.session[VERIFICATION_EMAIL_KEY] = address.email
        signup = not is_email_change(address)
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
        """allauth stores email, names and the password; adds the ORCID iD."""
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
