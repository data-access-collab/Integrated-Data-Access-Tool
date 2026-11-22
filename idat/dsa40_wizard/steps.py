"""The wizard steps: the their order, URL slugs and names are defined here.

Templates get the enum as `WizardStep` (e.g. {{ WizardStep.REVIEW }}) and the current
step as `current_step`.
"""

from __future__ import annotations

from django.db.models import TextChoices
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class WizardStep(TextChoices):
    """The wizard steps in order: URL slugs and step names (sidebar, step row, help
    panel)."""

    CHOOSE_VLOPSES = "vlopses", _("Choose platforms")
    ENTER_DETAILS = "details", _("Enter your details")
    REVIEW = "review", _("Review")
    GENERATE = "generate", _("Generate")
    SUBMIT = "submit", _("Submit")


def get_step_url(step: WizardStep) -> str:
    return reverse("dsa40_wizard:wizard_step", args=[step])
