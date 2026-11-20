from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BooleanField, CharField, TextField, URLField
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _


def validate_icon_name(name: str) -> None:
    """Reject names without an icon file (idat/templates/icons/<name>.svg): <c-icon>
    raises on unknown names, which would break every page showing the VLOPSE."""
    try:
        get_template(f"icons/{name}.svg")
    except TemplateDoesNotExist as e:
        raise ValidationError(
            _("No icon named %(name)s in idat/templates/icons/."),
            code="unknown_icon",
            params={"name": name},
        ) from e


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
            "Icon shown as the logo, rendered with <c-icon>: name of a file in "
            'idat/templates/icons/ without ".svg", e.g. "logo-tiktok". '
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
