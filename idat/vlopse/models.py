from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BooleanField, CharField, TextField, URLField
from django.utils.translation import gettext_lazy as _

from idat.core.icons import icons


def validate_icon_name(name: str) -> None:
    """Reject names that are not in idat/assets/icons/allowlist.json: <c-icon> raises
    on unknown names, which would break every page showing the VLOPSE."""
    if name not in icons():
        raise ValidationError(
            _("No icon named %(name)s in idat/assets/icons/allowlist.json."),
            code="unknown_icon",
            params={"name": name},
        )


class Vlopse(models.Model):
    """
    Top Level Configuration object for a
    Very Large Online Platforms and Search Engines (VLOPSE)
    """

    class ApplicationModality(models.TextChoices):
        UNKNOWN = "unknown", _("Unknown")
        FORM = "form", _("Web form")
        EMAIL = "email", _("E-mail")
        ICPSR = "icpsr", _("ICPSR portal")

    class PlatformType(models.TextChoices):
        """Groups of the platform picker, in display order."""

        SOCIAL_MEDIA = "social_media", _("Social media & video")
        SEARCH_ENGINE = "search_engine", _("Search engines")
        MARKETPLACE = "marketplace", _("Marketplaces")
        APP_STORE = "app_store", _("App stores")
        MAPS_TRAVEL = "maps_travel", _("Maps & travel")
        KNOWLEDGE = "knowledge", _("Knowledge")
        ADULT = "adult", _("Adult content")
        OTHER = "other", _("Other")

    name = CharField(
        _("Name of the VLOPSE"),
        blank=False,
        max_length=255,
        unique=True,
        db_index=True,
    )
    operator = CharField(
        _("Operator"),
        max_length=255,
        blank=True,
        help_text=_('Legal entity running the service, e.g. "TikTok Technology Ltd."'),
    )
    platform_type = CharField(
        _("Type"),
        max_length=20,
        choices=PlatformType,
        default=PlatformType.OTHER,
        help_text=_("Group in the platform picker."),
    )
    logo = CharField(
        _("Logo"),
        max_length=50,
        blank=True,
        validators=[validate_icon_name],
        help_text=_(
            "Icon shown as the logo, rendered with <c-icon>: a name from "
            'idat/assets/icons/allowlist.json, e.g. "logo-tiktok". '
            "Empty shows the first letter."
        ),
    )
    platform_information = TextField(blank=True)
    account_required = BooleanField(default=False)
    application_link = URLField(blank=True)
    modality = CharField(
        max_length=10,
        choices=ApplicationModality,
        default=ApplicationModality.UNKNOWN,
    )

    class Meta:
        verbose_name = "VLOPSE"
        verbose_name_plural = "VLOPSEs"

    def __str__(self) -> str:
        return self.name
