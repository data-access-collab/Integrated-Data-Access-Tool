from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from idat.dsa40_wizard.models import WizardInfo

CARD = WizardInfo.Presentation.CARD
ACCORDION = WizardInfo.Presentation.ACCORDION


@pytest.mark.parametrize(
    ("presentation", "tone"),
    [
        (CARD, WizardInfo.Tone.INFO),
        (CARD, WizardInfo.Tone.NEUTRAL),
        (ACCORDION, ""),
    ],
)
def test_clean_accepts_card_with_tone_and_accordion_without(
    presentation: str, tone: str
) -> None:
    WizardInfo(presentation=presentation, tone=tone).clean()


@pytest.mark.parametrize(
    ("presentation", "tone"),
    [
        (CARD, ""),  # a card needs a tone
        (ACCORDION, WizardInfo.Tone.INFO),  # an accordion has none
    ],
)
def test_clean_rejects_card_without_tone_and_accordion_with_tone(
    presentation: str, tone: str
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        WizardInfo(presentation=presentation, tone=tone).clean()

    assert list(excinfo.value.error_dict) == ["tone"]
