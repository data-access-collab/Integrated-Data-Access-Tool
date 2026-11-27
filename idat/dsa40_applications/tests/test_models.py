from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from idat.dsa40_applications.models import AccessApplication, CaseStatusEvent
from idat.dsa40_applications.tests.factories import AccessCaseFactory

pytestmark = pytest.mark.django_db


class TestAccessCase:
    def test_current_application_is_none_without_application(self):
        case = AccessCaseFactory()

        assert case.current_application is None

    def test_current_application_is_the_cases_application(self):
        case = AccessCaseFactory()
        application = AccessApplication.objects.create(access_case=case)
        AccessApplication.objects.create(access_case=AccessCaseFactory())

        assert case.current_application == application

    def test_current_application_is_the_most_recently_created(self):
        case = AccessCaseFactory()
        now = timezone.now()
        older = AccessApplication.objects.create(access_case=case)
        newer = AccessApplication.objects.create(access_case=case)
        # created_at is auto_now_add, so set it explicitly to make the order unambiguous
        AccessApplication.objects.filter(pk=older.pk).update(created_at=now)
        AccessApplication.objects.filter(pk=newer.pk).update(
            created_at=now + timedelta(days=1)
        )

        assert case.current_application == newer

    def test_saving_an_existing_case_adds_no_state_event(self):
        case = AccessCaseFactory()

        case.save()

        assert case.case_states.count() == 1

    def test_current_state_is_none_without_events(self):
        case = AccessCaseFactory()
        case.case_states.all().delete()

        assert case.current_state is None

    def test_current_state_is_the_most_recently_registered_event(self):
        case = AccessCaseFactory()
        now = timezone.now()
        submitted = CaseStatusEvent.objects.create(
            access_case=case,
            status=CaseStatusEvent.State.SUBMITTED,
            registered_at=now + timedelta(days=1),
        )
        CaseStatusEvent.objects.create(
            access_case=case,
            status=CaseStatusEvent.State.WITHDRAWN,
            registered_at=now - timedelta(days=1),
        )

        assert case.current_state == submitted

    def test_current_state_ignores_events_of_other_cases(self):
        case = AccessCaseFactory()
        CaseStatusEvent.objects.create(
            access_case=AccessCaseFactory(),
            status=CaseStatusEvent.State.GRANTED,
            registered_at=timezone.now() + timedelta(days=1),
        )

        assert case.current_state.status == CaseStatusEvent.State.DRAFT
