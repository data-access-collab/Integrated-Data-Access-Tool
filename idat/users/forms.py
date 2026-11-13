from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.utils.translation import gettext_lazy as _

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
        help_text=_("Format: 0000-0000-0000-0000"),
    )

    field_order = [
        "first_name",
        "last_name",
        "email",
        "orcid",
        "password1",
        "password2",
    ]

    def clean_orcid(self) -> str | None:
        orcid = self.cleaned_data["orcid"] or None
        if orcid and User.objects.filter(orcid=orcid).exists():
            raise forms.ValidationError(_("This ORCID iD is already registered."))
        return orcid


class UserSignupForm(SignupFieldsMixin, SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SignupFieldsMixin, SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """
