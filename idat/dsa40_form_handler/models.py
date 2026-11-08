from django.db import models
from django.db.models import BooleanField, CharField, JSONField, TextField

from idat.dsa40_form_handler.form_field_types import ConstraintConfig, config_adapter
from idat.vlopse.models import Vlopse


class InputType(models.TextChoices):
    TEXT = "text"
    FILE_UPLOAD = "file_upload"
    DATE_SELECT = "date_select"
    SELECTION = "selection"
    MULTI_SELECT = "multi_select"
    ISO_3166_1 = "iso-3166-1"


class QuestionCategory(models.TextChoices):
    GENERAL = "general", "General"  # Fallback category
    CONTACT = "contact_details", "Contact details"
    COLLABORATION = "collaboration", "Collaboration"
    QUALIFICATIONS = "qualifications", "Qualifications"
    AFFILIATION = "affiliation", "Affiliation"
    FUNDING = "funding_commercial_interests", "Funding"
    RESEARCH_PROJECT = "research_project", "Research project"
    TECHNICAL = "technical", "Technical"
    REQUESTED_DATA = "requested_data", "Requested data"
    EXPERIENCE = "previous_experience", "Previous experience"
    DATA_SECURITY = "data_security", "Data security"
    LEGAL = "legal", "Legal"


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
    category = CharField(
        max_length=32,
        choices=QuestionCategory,
        default=QuestionCategory.GENERAL,
    )

    class Meta:
        verbose_name = "VLOPSE Question"

    def __str__(self) -> str:
        max_length = 50
        truncated_text = (
            self.text[:max_length] + "..." if len(self.text) > max_length else self.text
        )
        return f"{self.vlopse.name} [{self.key}] - {truncated_text}"


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
    category = CharField(
        max_length=32,
        choices=QuestionCategory,
        default=QuestionCategory.GENERAL,
    )

    class Meta:
        verbose_name = "DSA Question"

    def __str__(self) -> str:
        return f"Q[{self.key}]('{self.text}')"

    @property
    def parsed_config(self) -> ConstraintConfig | None:
        if self.config is None:
            return None
        c = self.config
        return config_adapter.validate_python(c)
