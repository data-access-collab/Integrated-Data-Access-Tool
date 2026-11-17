from allauth.account.forms import (
    AddEmailForm,
    LoginForm,
    ReauthenticateForm,
    ResetPasswordForm,
    ResetPasswordKeyForm,
    SignupForm,
)
from allauth.mfa.base.forms import AuthenticateForm
from allauth.mfa.base.forms import ReauthenticateForm as MFAReauthenticateForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.contrib.auth.password_validation import (
    MinimumLengthValidator,
    get_default_password_validators,
)
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from idat.users.models import User
from idat.users.validators import validate_orcid


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("email",)
        error_messages = {
            "email": {"unique": _("This e-mail address is already registered.")},
        }


class SignupFieldsMixin(forms.Form):
    """
    Profile fields asked for at signup, shared by both signup forms.
    allauth's AccountAdapter.save_user stores first_name and last_name;
    our AccountAdapter adds orcid.
    """

    first_name = forms.CharField(label=_("First name"), max_length=150)
    last_name = forms.CharField(label=_("Last name"), max_length=150)
    orcid = forms.CharField(
        label=_("ORCID iD"),
        max_length=19,
        required=False,
        validators=[validate_orcid],
        help_text=_("Optional · speeds up verification with most platforms."),
    )
    terms = forms.BooleanField(
        label=_("I accept the Terms of Use"),
    )

    field_order = [
        "first_name",
        "last_name",
        "email",
        "orcid",
        "password1",
        "password2",
        "terms",
    ]

    def clean_orcid(self) -> str | None:
        orcid = self.cleaned_data["orcid"] or None
        if orcid and User.objects.filter(orcid=orcid).exists():
            raise forms.ValidationError(_("This ORCID iD is already registered."))
        return orcid


def min_password_length() -> int | None:
    """min_length of the MinimumLengthValidator setting, if there is one."""
    for validator in get_default_password_validators():
        if isinstance(validator, MinimumLengthValidator):
            return validator.min_length
    return None


def password_length_help() -> str:
    """'At least n characters.' from the MinimumLengthValidator setting."""
    n = min_password_length()
    if n is None:
        return ""
    return ngettext(
        "At least %(n)d character.",
        "At least %(n)d characters.",
        n,
    ) % {"n": n}


class UserSignupForm(SignupFieldsMixin, SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].label = _("Institutional e-mail")
        self.fields["email"].help_text = _(
            "Platforms use this to verify your affiliation.",
        )
        self.fields["password1"].help_text = password_length_help()


class UserLoginForm(LoginForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["login"].label = _("E-mail")
        # the page has its own "Forgot password?" link; allauth adds one as help text
        self.fields["password"].help_text = ""
        if "remember" in self.fields:
            self.fields["remember"].label = _("Remember me")


class UserAddEmailForm(AddEmailForm):
    """The "change e-mail" form on /accounts/email/ (ACCOUNT_CHANGE_EMAIL)."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].label = _("New e-mail address")
        self.fields["email"].help_text = _(
            "We send a link to the new address. Until you open it, you keep "
            "signing in with the current one.",
        )
        self.fields["email"].widget.attrs.pop("placeholder", None)


class UserResetPasswordForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].label = _("E-mail")
        self.fields["email"].widget.attrs.pop("placeholder", None)


class UserResetPasswordKeyForm(ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = _("New password")
        self.fields["password1"].help_text = _(
            "%(length)s A passphrase works well.",
        ) % {"length": password_length_help()}
        # the page's requirements box reads it; the browser checks it on submit too
        if n := min_password_length():
            self.fields["password1"].widget.attrs["minlength"] = n
        self.fields["password2"].label = _("Repeat new password")
        for field in ("password1", "password2"):
            self.fields[field].widget.attrs.pop("placeholder", None)


class UserReauthenticateForm(ReauthenticateForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # the page has its own "Forgot password?" link; allauth adds one as help text
        self.fields["password"].help_text = ""


class MFACodeFieldMixin(forms.Form):
    """Label and help for the code field of the 2FA sign-in and confirm-access steps."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        code = self.fields["code"]
        code.label = _("Authentication code")
        code.help_text = _(
            "From your authenticator app, or one of your recovery codes."
        )
        code.widget.attrs.pop("placeholder", None)


class UserMFAAuthenticateForm(MFACodeFieldMixin, AuthenticateForm):
    pass


class UserMFAReauthenticateForm(MFACodeFieldMixin, MFAReauthenticateForm):
    pass


class UserSocialSignupForm(SignupFieldsMixin, SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """
