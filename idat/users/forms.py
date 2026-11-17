from allauth.account.forms import LoginForm, SignupForm
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


def password_length_help() -> str:
    """'At least n characters.' from the MinimumLengthValidator setting."""
    for validator in get_default_password_validators():
        if isinstance(validator, MinimumLengthValidator):
            n = validator.min_length
            return ngettext(
                "At least %(n)d character.",
                "At least %(n)d characters.",
                n,
            ) % {"n": n}
    return ""


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


class UserSocialSignupForm(SignupFieldsMixin, SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """
