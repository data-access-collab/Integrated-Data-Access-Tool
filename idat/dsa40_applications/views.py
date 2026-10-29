from __future__ import annotations

import typing
from typing import Any

from django.http import Http404, HttpResponse, HttpResponseBase
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView
from django_htmx.http import push_url

from idat.dsa40.api.views import form_service
from idat.dsa40.models import DSAQuestion, Vlopse
from idat.dsa40_applications.forms import QuestionsForm, VlopseSelectionForm
from idat.dsa40_applications.state import (
    FILE_KEY_HEADER,
    MAX_AGE,
    MAX_AGE_HEADER,
    STATE_HEADER,
    WIZARD_ID_HEADER,
    WizardState,
    dump_wizard_state,
    encode_file_encryption_key,
    load_wizard_state,
)

if typing.TYPE_CHECKING:
    from django import forms
    from django.http.request import HttpRequest

STEPS = [(1, "Select VLOPSEs"), (2, "Answer Questions"), (3, "Review")]


# TODO: Delete once form_handler has a service layer
def _temp_get_question_service(vlopse_ids: list[int]) -> list[tuple[bool, DSAQuestion]]:
    vlopses = Vlopse.objects.filter(id__in=vlopse_ids).values_list("name", flat=True)
    # TODO/NOTE: bit weird format (required, Question)
    return form_service.get_mapped_questions_for(vlopses)


class ApplicationFormView(TemplateView):
    """Entry view for DSA 40 application creation"""

    template_name = "dsa40_applications/base.html"
    extra_context = {
        "load_url": reverse_lazy("dsa40_applications:wizard_step", args=[1])
    }


@method_decorator(never_cache, name="dispatch")
class ApplicationFormStep(View):
    """Base view for application form steps"""

    step: int
    next_step: type[ApplicationFormStep] | None = None
    template_name: str
    form_class: type[forms.Form]
    state: WizardState

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        if not request.htmx:
            # plain page load (reload, typed URL): the server can't see
            # sessionStorage, so return the base view and let htmx re-request
            return render(
                request, "dsa40_applications/base.html", {"load_url": request.path}
            )

        self.state = load_wizard_state(request)
        if redirect_to := self.check_prerequisites():
            return redirect_to
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return self.render_step(self.get_form())

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        form = self.get_form(data=request.POST)
        if not form.is_valid():
            return self.render_step(form)
        self.update_state(form)
        return self.go_to(self.next_step)

    def get_form_kwargs(self) -> dict[str, Any]:
        return {}

    def get_form(self, data: dict | None = None) -> forms.Form:
        return self.form_class(data=data, **self.get_form_kwargs())

    def update_state(self, form: forms.Form) -> None:
        """Update self.state in place."""
        raise NotImplementedError

    def check_prerequisites(self) -> HttpResponse | None:
        """Returns redirect target if checks fail, None otherwise."""
        return None

    def go_to(self, step_cls: type[ApplicationFormStep] | None) -> HttpResponse:
        """Render another step unbound, carrying the current state."""
        # TODO: Handle None (or drop it from possibilities)
        nxt = step_cls()
        nxt.setup(self.request)
        nxt.state = self.state
        return nxt.check_prerequisites() or nxt.render_step(nxt.get_form())

    def render_step(
        self, form: forms.Form, context: dict | None = None
    ) -> HttpResponse:
        context = context or {}
        response = render(
            self.request,
            "dsa40_applications/_step.html",
            {
                "step_template": self.template_name,
                "steps": STEPS,
                "step": self.step,
                "form": form,
                **context,
            },
        )

        response = self.add_response_headers(response)
        push_url(response, reverse("dsa40_applications:wizard_step", args=[self.step]))
        return response

    def add_response_headers(self, response: HttpResponse) -> HttpResponse:
        response[STATE_HEADER] = dump_wizard_state(self.state)
        # lets the browser encrypt/decrypt this draft's files (kept in memory)
        response[WIZARD_ID_HEADER] = self.state["wizard_id"]
        response[FILE_KEY_HEADER] = encode_file_encryption_key(self.state["wizard_id"])
        # lets the browser expire stored files
        response[MAX_AGE_HEADER] = str(MAX_AGE)
        return response


class VlopseSelectionStep(ApplicationFormStep):
    step = 1
    template_name = "dsa40_applications/_vlopse_selection_form.html"
    form_class = VlopseSelectionForm

    def get_form_kwargs(self) -> dict[str, Any]:
        return {"initial": {"vlopses": self.state["vlopses"]}}

    def update_state(self, form: forms.Form) -> None:
        """Update state in place and drop answers for deselected Vlopses."""
        vlopse_ids = [v.id for v in form.cleaned_data["vlopses"]]
        active_qs = {str(q.key) for _, q in _temp_get_question_service(vlopse_ids)}
        self.state["vlopses"] = vlopse_ids
        self.state["answers"] = {
            k: v for k, v in self.state["answers"].items() if k in active_qs
        }


class QuestionsStep(ApplicationFormStep):
    step = 2
    template_name = "dsa40_applications/_questions_form.html"
    form_class = QuestionsForm

    def check_prerequisites(self) -> HttpResponse | None:
        if not self.state["vlopses"]:
            return self.go_to(VlopseSelectionStep)
        return None

    def get_form_kwargs(self) -> dict[str, Any]:
        return {
            "question_config": _temp_get_question_service(self.state["vlopses"]),
            "answers": self.state["answers"],
        }

    def update_state(self, form: forms.Form) -> None:
        self.state["answers"] = dict(form.cleaned_data)


class ReviewStep(ApplicationFormStep):
    step = 3
    template_name = "dsa40_applications/_review.html"
    form_class = QuestionsForm

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        # bind to the stored answers so the review shows validated values
        form = self.form_class(data=self.state["answers"], **self.get_form_kwargs())
        if not form.is_valid():
            return self.go_to(QuestionsStep)
        vlopse_form = VlopseSelectionForm(initial={"vlopses": self.state["vlopses"]})
        return self.render_step(form, context={"vlopses_form": vlopse_form})

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        # TODO: Allow application creation if logged in
        #  -> may be handled by a different view.
        raise NotImplementedError

    def get_form_kwargs(self) -> dict[str, Any]:
        return {
            "question_config": _temp_get_question_service(self.state["vlopses"]),
            "answers": self.state["answers"],
        }

    def check_prerequisites(self) -> HttpResponse | None:
        if not self.state["vlopses"]:
            return self.go_to(VlopseSelectionStep)
        if not self.state["answers"]:
            return self.go_to(QuestionsStep)
        return None


VlopseSelectionStep.next_step = QuestionsStep
QuestionsStep.next_step = ReviewStep


STEP_VIEWS = {
    1: VlopseSelectionStep.as_view(),
    2: QuestionsStep.as_view(),
    3: ReviewStep.as_view(),
}


def wizard_step(request: HttpRequest, step: int) -> HttpResponseBase:
    view = STEP_VIEWS.get(step)
    if view is None:
        raise Http404
    return view(request)
