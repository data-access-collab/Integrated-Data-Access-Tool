from __future__ import annotations

import pytest

from idat.core.icons import get_icon
from idat.dsa40_applications.models import AccessApplication, CaseStatusEvent
from idat.dsa40_applications.templatetags.case_ui import (
    _APPLICATION_STATE_TONE,
    _FALLBACK_APPLICATION_TONE,
    _FALLBACK_ICON,
    _STATUS_ICON,
    application_tone,
    status_icon,
)

# Tones <c-timeline-event>, <c-lifecycle-step> and <c-badge> map to a colour
KNOWN_TONES = {"info", "success", "warning", "danger", "neutral"}


class TestStatusIcon:
    @pytest.mark.parametrize("status", CaseStatusEvent.State)
    def test_every_status_has_its_own_icon(self, status):
        assert status in _STATUS_ICON
        assert status_icon(status) == _STATUS_ICON[status]

    @pytest.mark.parametrize("icon", [*_STATUS_ICON.values(), _FALLBACK_ICON])
    def test_icons_exist_and_tones_are_known(self, icon):
        get_icon(icon.icon)  # raises UnknownIconError, like <c-icon> would

        assert icon.color in KNOWN_TONES

    def test_unknown_status_falls_back(self):
        assert status_icon("legacy") == _FALLBACK_ICON


class TestApplicationTone:
    def test_maps_the_state(self):
        assert application_tone(AccessApplication.State.ACCEPTED) == "success"

    def test_unmapped_state_falls_back(self):
        assert (
            application_tone(AccessApplication.State.PENDING)
            == _FALLBACK_APPLICATION_TONE
        )

    @pytest.mark.parametrize(
        "tone", [*_APPLICATION_STATE_TONE.values(), _FALLBACK_APPLICATION_TONE]
    )
    def test_tones_are_known(self, tone):
        assert tone in KNOWN_TONES
