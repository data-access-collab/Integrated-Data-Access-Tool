from django.db import models
from django.db.models import BooleanField, CharField, JSONField, TextField, URLField
from django.utils.translation import gettext_lazy as _

from idat.dsa40.lib.schemas import ConstraintConfig, config_adapter


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


class InputType(models.TextChoices):
    TEXT = "text"
    FILE_UPLOAD = "file_upload"
    DATE_SELECT = "date_select"
    SELECTION = "selection"
    MULTI_SELECT = "multi_select"
    ISO_3166_1 = "iso-3166-1"


class VLOPSEQuestion(models.Model):
    """
    Top Level Configuration object for a
    Very Large Online Platforms and Search Engines (VLOPSE)
    """

    key = CharField(max_length=16, unique=True, db_index=True)
    text = TextField()
    vlopse = models.ForeignKey(Vlopse, on_delete=models.CASCADE)
    required = BooleanField(default=True)
    input_type = CharField(
        max_length=16,
        choices=InputType,
        default=InputType.TEXT,
    )
    details = TextField(blank=True)
    config = JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.vlopse.name}Q[{self.id}]('{self.text}')"


class DSAQuestion(models.Model):
    key = CharField(max_length=256, unique=True, db_index=True)
    text = TextField()
    help_text = TextField(blank=True)
    input_type = CharField(
        max_length=16,
        choices=InputType,
        default=InputType.TEXT,
    )
    config = JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Q[{self.id}]('{self.text}')"

    @property
    def parsed_config(self) -> ConstraintConfig | None:
        if self.config is None:
            return None
        c = self.config
        return config_adapter.validate_python(c)
