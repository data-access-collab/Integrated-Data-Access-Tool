from django.db import models
from django.db.models import BooleanField, CharField, TextField, URLField
from django.utils.translation import gettext_lazy as _


class Vlopse(models.Model):
    """
    Top Level Configuration object for a
    Very Large Online Platforms and Search Engines (VLOPSE)
    """

    class ApplicationModality(models.TextChoices):
        FORM = "form", _("Form")
        EMAIL = "email", _("eMail")

    name = CharField(
        _("Name of the VLOPSE"),
        blank=False,
        max_length=255,
        unique=True,
        db_index=True,
    )
    platform_information = TextField(blank=True)
    account_required = BooleanField(default=False)
    application_link = URLField(blank=True)
    modality = CharField(
        max_length=10,
        choices=ApplicationModality,
        default=ApplicationModality.EMAIL,
    )

    def __str__(self) -> str:
        return self.name
