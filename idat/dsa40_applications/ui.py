from __future__ import annotations

import typing
from typing import Literal, NamedTuple

from idat.dsa40_applications.models import (
    AccessCase,
    CaseStatusEvent,
)

if typing.TYPE_CHECKING:
    import datetime

# The tones <c-timeline-event> maps to a marker colour
Tone = Literal["info", "success", "warning", "danger", "neutral"]


class StatusIcon(NamedTuple):
    icon: str
    color: Tone


class StatusEventContext(NamedTuple):
    title: str
    subtitle: str | None
    date: datetime.datetime
    icon: StatusIcon


_STATUS_ICON: dict[CaseStatusEvent.State, StatusIcon] = {
    CaseStatusEvent.State.DRAFT: StatusIcon("pencil", "info"),
    CaseStatusEvent.State.SUBMITTED: StatusIcon("arrow-right", "info"),
    CaseStatusEvent.State.INFOS_REQUESTED: StatusIcon("alert-triangle", "warning"),
    # CaseStatusEvent.State.REQUEST_ANSWERED: StatusIcon("mail", "info"),
    CaseStatusEvent.State.REJECTED: StatusIcon("x", "danger"),
    CaseStatusEvent.State.GRANTED: StatusIcon("check", "success"),
    CaseStatusEvent.State.WITHDRAWN: StatusIcon("circle", "neutral"),
}
_FALLBACK_ICON = StatusIcon("info", "neutral")


def _get_subtitle(status: CaseStatusEvent) -> str | None:
    if status.access_application:
        return f"Belongs to application {status.access_application}"
    return None


def status_event_context(event: CaseStatusEvent) -> StatusEventContext:
    title = event.get_status_display()
    subtitle = _get_subtitle(event)
    date = event.registered_at
    icon = _STATUS_ICON.get(event.status, _FALLBACK_ICON)
    return StatusEventContext(title, subtitle, date, icon)


def status_timeline(case: AccessCase) -> list[StatusEventContext]:
    return [status_event_context(e) for e in case.case_states.order_by("registered_at")]
