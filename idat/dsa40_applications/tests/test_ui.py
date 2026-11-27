from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from idat.core.icons import get_icon
from idat.dsa40_applications.models import CaseStatusEvent
from idat.dsa40_applications.tests.factories import AccessCaseFactory
from idat.dsa40_applications.ui import (
    _FALLBACK_ICON,
    _STATUS_ICON,
    status_event_context,
    status_timeline,
)

# Tones <c-timeline-event> maps to a marker colour
TIMELINE_TONES = {"info", "success", "warning", "danger", "neutral"}


@pytest.mark.django_db
class TestStatusTimeline:
    def test_orders_events_by_registration_date(self):
        case = AccessCaseFactory()
        now = timezone.now()
        later = CaseStatusEvent.objects.create(
            access_case=case,
            status=CaseStatusEvent.State.GRANTED,
            registered_at=now + timedelta(days=2),
        )
        earlier = CaseStatusEvent.objects.create(
            access_case=case,
            status=CaseStatusEvent.State.SUBMITTED,
            registered_at=now + timedelta(days=1),
        )

        # The case's own draft event (registered on creation) comes first
        dates = [entry.date for entry in status_timeline(case)][1:]
        assert dates == [earlier.registered_at, later.registered_at]

    def test_contains_only_the_cases_events(self):
        case = AccessCaseFactory()
        AccessCaseFactory()  # its own draft event must not show up

        assert len(status_timeline(case)) == case.case_states.count() == 1

    def test_is_empty_without_events(self):
        case = AccessCaseFactory()
        case.case_states.all().delete()

        assert status_timeline(case) == []


class TestStatusEventContext:
    @pytest.mark.parametrize("status", CaseStatusEvent.State)
    def test_every_status_has_its_own_icon(self, status):
        context = status_event_context(CaseStatusEvent(status=status))

        assert status in _STATUS_ICON
        assert context.icon == _STATUS_ICON[status]

    @pytest.mark.parametrize("icon", [*_STATUS_ICON.values(), _FALLBACK_ICON])
    def test_icons_exist_and_tones_are_known(self, icon):
        get_icon(icon.icon)  # raises UnknownIconError, like <c-icon> would

        assert icon.color in TIMELINE_TONES

    def test_unknown_status_falls_back(self):
        context = status_event_context(CaseStatusEvent(status="legacy"))

        assert context.icon == _FALLBACK_ICON
