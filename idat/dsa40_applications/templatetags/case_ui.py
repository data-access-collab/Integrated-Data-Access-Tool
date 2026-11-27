"""Display mappings for access cases: {% load case_ui %}.

{% with icon=event.status|status_icon %}
  <c-timeline-event :icon="icon.icon" :tone="icon.color" … />
{% endwith %}
<c-badge :tone="application.state|application_tone" … />
"""

from __future__ import annotations

from typing import Literal, NamedTuple

from django import template

from idat.dsa40_applications.models import AccessApplication, CaseStatusEvent

register = template.Library()

# The tones <c-timeline-event>, <c-lifecycle-step> and <c-badge> map to a colour
Tone = Literal["info", "success", "warning", "danger", "neutral"]


class StatusIcon(NamedTuple):
    icon: str
    color: Tone


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

_APPLICATION_STATE_TONE: dict[AccessApplication.State, Tone] = {
    AccessApplication.State.DRAFT: "warning",
    AccessApplication.State.REQUIRES_RESPONSE: "warning",
    AccessApplication.State.ACCEPTED: "success",
    AccessApplication.State.MODIFICATION_ACCEPTED: "success",
    AccessApplication.State.REJECTED: "danger",
    AccessApplication.State.MODIFICATION_REJECTED: "danger",
}
_FALLBACK_APPLICATION_TONE: Tone = "info"


@register.filter
def status_icon(status: str) -> StatusIcon:
    """Icon and tone of a CaseStatusEvent status."""
    return _STATUS_ICON.get(status, _FALLBACK_ICON)


@register.filter
def application_tone(state: str) -> Tone:
    """<c-badge> tone of an AccessApplication state."""
    return _APPLICATION_STATE_TONE.get(state, _FALLBACK_APPLICATION_TONE)
