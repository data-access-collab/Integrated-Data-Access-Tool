from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CharField, PositiveIntegerField, Q, TextField

from idat.dsa40_form_handler.models import DSAQuestion, QuestionCategory, VLOPSEQuestion
from idat.dsa40_wizard.steps import WizardStep


class WizardInfo(models.Model):
    """A tip in the wizard's help panel, shown wherever one of its targets is shown.
    Targets can be wizard steps, sections (in enter details), and questions."""

    class Presentation(models.TextChoices):
        CARD = "card", "Card"  # <c-help.insight-card>
        ACCORDION = "accordion", "Accordion"  # <c-help.accordion>

    class Tone(models.TextChoices):
        """Card colors (Figma Help / Insight Card)."""

        INFO = "info", "Info (blue)"
        INSIGHT = "insight", "Insight (yellow)"
        DANGER = "danger", "Danger (red)"
        NEUTRAL = "neutral", "Neutral (grey)"

    presentation = CharField(
        "Presentation",
        max_length=16,
        choices=Presentation,
        default=Presentation.CARD,
    )
    tone = CharField(
        "Tone",
        max_length=16,
        choices=Tone,
        blank=True,
        help_text="Card colour; cards only.",
    )
    order = PositiveIntegerField(
        "Order",
        default=0,
        help_text="Lower first, among the tips of the same target.",
    )
    title = CharField("Title", max_length=255)
    body = TextField("Body")

    # Targets
    steps = ArrayField(
        CharField(max_length=16, choices=WizardStep),
        verbose_name="Steps",
        default=list,
        blank=True,
    )
    sections = ArrayField(
        CharField(max_length=32, choices=QuestionCategory),
        verbose_name="Sections",
        default=list,
        blank=True,
    )
    dsa_questions = models.ManyToManyField(
        DSAQuestion,
        verbose_name="DSA Questions",
        blank=True,
        related_name="wizard_infos",
    )
    vlopse_questions = models.ManyToManyField(
        VLOPSEQuestion,
        verbose_name="VLOPSE Questions",
        blank=True,
        related_name="wizard_infos",
    )

    class Meta:
        verbose_name = "Wizard info"
        verbose_name_plural = "Wizard infos"
        ordering = ["order", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(presentation="card") & ~Q(tone=""))
                    | (Q(presentation="accordion") & Q(tone=""))
                ),
                name="wizard_info_tone_only_for_cards",
                violation_error_message="Cards need a tone; accordions have none.",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        """Field-level message for the tone constraint, so the admin marks the field."""
        super().clean()
        if self.presentation == self.Presentation.CARD and not self.tone:
            raise ValidationError({"tone": "Cards need a tone."})
        if self.presentation == self.Presentation.ACCORDION and self.tone:
            raise ValidationError({"tone": "Accordions have no tone."})
