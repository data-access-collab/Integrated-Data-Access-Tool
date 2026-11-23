"""Create access applications from a wizard draft"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.forms import ValidationError
from django.utils import timezone

from idat.dsa40_applications.models import (
    AccessApplication,
    AccessCase,
    ApplicationState,
    PlatformSpecificAnswer,
    ResearchProject,
)
from idat.dsa40_form_handler.models import DSAQuestion
from idat.dsa40_wizard.forms import is_unanswered
from idat.vlopse.models import Vlopse

if TYPE_CHECKING:
    from idat.dsa40_wizard.state import WizardState
    from idat.users.models import User


@transaction.atomic
def update_answers(
    application: AccessApplication,
    answers: dict[str, object],  # Will this from wizard state as well?
) -> AccessApplication:
    """
    Apply answers {question_key: value}.
    Returns the application that was actually edited. For a submitted
    application this is a NEW draft copy, so callers must use the return value.
    """
    if not application.is_editable_in_place:
        application = application.copy_as_draft()
    elif application.state == ApplicationState.READY:
        _validate(application)

    # TODO: Use form_handler here and map questions

    questions = {
        q.key: q for q in PlatformSpecificAnswer.objects.filter(key__in=answers)
    }
    for key, value in answers.items():
        PlatformSpecificAnswer.objects.update_or_create(
            application=application, question=questions[key], defaults={"value": value}
        )
    return application


@transaction.atomic
def mark_ready(application: AccessApplication) -> AccessApplication:
    _require_state(application, ApplicationState.DRAFT)
    _validate(application)
    # TODO: create a CaseStatusEvent here
    case = application.access_case
    case.state = ApplicationState.READY
    case.save(update_fields=["state"])
    return application


@transaction.atomic
def submit(application: AccessApplication) -> AccessApplication:
    _require_state(application, ApplicationState.READY)
    _validate(application)
    # TODO: create a CaseStatusEvent here
    case = application.access_case
    case.state = ApplicationState.READY
    case.save(update_fields=["state"])

    application.submitted_at = timezone.now()
    application.save(update_fields=["submitted_at"])
    return application


def _require_state(application: AccessApplication, state: ApplicationState) -> None:
    if application.state != state:
        msg = f"Application must be {state}, is {application.state}."
        raise ValidationError(msg)


def _validate(application: AccessApplication) -> bool:
    # TODO
    return True


@transaction.atomic
def create_research_project(
    owner: User,
    state: WizardState,
) -> ResearchProject:
    """Persist a draft: one Application per selected VLOPSE, an Answer per
    answered question + the platforms' overrides.
    Creates an intermediate AccessCase object as a link.
    """
    # TODO: validate file uploads
    # TODO: use questionaire to separate platform specific from non platform specific
    keys = set(state["answers"])
    questions = DSAQuestion.objects.in_bulk(keys, field_name="key")

    project = ResearchProject.objects.create(owner=owner)
    vlopses = Vlopse.objects.in_bulk(state["vlopses"])
    cases = {
        vlopse_id: AccessCase.objects.create(project=project, vlopse=vlopses[vlopse_id])
        for vlopse_id in state["vlopses"]
        if vlopse_id in vlopses
    }
    for case in cases.values():
        application_draft = AccessApplication.objects.create(
            access_case=case, state=ApplicationState.DRAFT
        )
        for key, value in state["answers"].items():
            if key not in questions or is_unanswered(value):
                continue
            answer = PlatformSpecificAnswer.objects.create(  # noqa: F841
                application=application_draft, key=key, value=value
            )

    return project
