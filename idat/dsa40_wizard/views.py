from __future__ import annotations

import typing
from enum import StrEnum
from http import HTTPStatus
from typing import Any

from django.core.exceptions import SuspiciousOperation
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBase,
    HttpResponseNotAllowed,
)
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.vary import vary_on_headers
from django.views.generic import TemplateView
from django_htmx.http import push_url, replace_url

from idat.dsa40_form_handler.services.questions import QuestionService
from idat.dsa40_form_handler.validation.mapping import QuestionMapper
from idat.dsa40_wizard.forms import (
    FormQuestion,
    QuestionsForm,
    VlopseSelectionForm,
)
from idat.dsa40_wizard.services.preview import build_application_previews
from idat.dsa40_wizard.state import (
    DRAFT_UNAVAILABLE_HEADER,
    FILE_KEY_HEADER,
    MAX_STATE_AGE,
    MAX_STATE_AGE_HEADER,
    STATE_POST_FIELD,
    STATE_REQUEST_HEADER,
    WIZARD_ID_HEADER,
    WizardState,
    WizardStateExpiredError,
    dump_wizard_state,
    encode_file_encryption_key,
    load_wizard_state,
)
from idat.vlopse.models import Vlopse

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from django import forms
    from django.http.request import HttpRequest

    from idat.dsa40_wizard.services.preview import VlopseApplicationPreview


def is_submit(request: HttpRequest) -> bool:
    """Whether the request came through a step's submit URL (create/<step>/submit/,
    used by the step forms) rather than its plain URL (shows the step)."""
    match = request.resolver_match
    return bool(match and match.view_name == "dsa40_wizard:wizard_submit")


class WizardStep(StrEnum):
    """The wizard steps in order: URL slugs and the sidebar's `current-step`.
    Keep in sync with the steps of templates/cotton/wizard/sidebar.html."""

    CHOOSE_VLOPSES = "choose-vlopses"
    ENTER_DETAILS = "enter-details"
    REVIEW = "review"
    GENERATE = "generate"
    SUBMIT = "submit"


def get_step_url(step: WizardStep) -> str:
    return reverse("dsa40_wizard:wizard_step", args=[step])


def get_wizard_urls() -> dict[str, str]:
    """Links of the sidebar's done steps (wizard.sidebar `hrefs`), keyed by slug with
    underscores (choose_vlopses …): only steps that have a view.

    Note: Underscores are needed because Django templates do not accept hyphenated
    variable names.
    """
    return {step.replace("-", "_"): get_step_url(step) for step in STEP_VIEWS}


def get_mapped_vlopse_questions(vlopse_ids: list[int]) -> list[FormQuestion]:
    """The DSA questions the selected VLOPSEs map to, each required if at least one
    of them requires it.
    """
    vlopses = Vlopse.objects.filter(id__in=vlopse_ids).values_list("name", flat=True)
    mapper = QuestionMapper.from_vlopse_names(list(vlopses), QuestionService())
    return [
        FormQuestion(question, required)
        for required, question in mapper.map_vlopse_to_unified()
    ]


def has_vlopse_configs(state: WizardState) -> bool:
    """Whether at least one VLOPSE is selected and a valid config (question mapping)
    exists for each."""
    return VlopseSelectionForm(data={"vlopses": state["vlopses"]}).is_valid()


def get_shell_context(load_url: str, current_step: WizardStep) -> dict[str, Any]:
    """Context of the wizard shell (dsa40_wizard/base.html). Both WizardFormView and
    the plain page loads of WizardFormStep render the shell: add shell values here.
    """
    return {
        "load_url": load_url,
        "current_step": current_step,
        "wizard_urls": get_wizard_urls(),
        "state_ttl": int(MAX_STATE_AGE / 60 / 60),
    }


def draft_unavailable_response() -> HttpResponse:
    """Tell wizard.js the draft can't be loaded: it discards the draft (token, file key,
    stored files) and goes to the draft unavailable page."""
    response = HttpResponse(status=HTTPStatus.NO_CONTENT)
    response[DRAFT_UNAVAILABLE_HEADER] = reverse("dsa40_wizard:draft_unavailable")
    response[MAX_STATE_AGE_HEADER] = str(MAX_STATE_AGE)
    return response


class WizardFormView(TemplateView):
    """Entry view for DSA 40 application wizard"""

    template_name = "dsa40_wizard/base.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        shell = get_shell_context(
            reverse("dsa40_wizard:wizard_step", args=[WizardStep.CHOOSE_VLOPSES]),
            WizardStep.CHOOSE_VLOPSES,
        )
        return super().get_context_data(**shell, **kwargs)


# responses carry the state token and file key: never cache
@method_decorator(never_cache, name="dispatch")
# same URL, shell or step partial depending on HX-Request: keep caches apart
@method_decorator(vary_on_headers("HX-Request"), name="dispatch")
class WizardFormStep(View):
    """Base view for wizard form steps"""

    step: WizardStep
    next_step: type[WizardFormStep] | None = None
    template_name: str
    form_class: type[forms.Form]
    state: WizardState

    def form_questions(self) -> list[FormQuestion]:
        """The DSA questions of the stored VLOPSE selection."""
        return get_mapped_vlopse_questions(self.state["vlopses"])

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        if not request.htmx or request.htmx.history_restore_request:
            # plain page load (reload, typed URL) or browser back/forward: the
            # server can't see sessionStorage, so return the base view and let
            # htmx re-request. htmx swaps a history restore into <body>, so the
            # step partial would replace the whole page layout.
            return render(
                request,
                "dsa40_wizard/base.html",
                # the plain step URL, so loading the shell never submits
                get_shell_context(get_step_url(self.step), self.step),
            )
        if request.method != "POST":
            # the state token travels in the POST body only
            return HttpResponseNotAllowed(["POST"])

        state = self.load_draft()
        if state is None:
            return draft_unavailable_response()
        self.state = state

        if redirect_to := self.check_prerequisites():
            return redirect_to
        # every step request is a POST (it carries the token): the URL, not the
        # method, tells a form submit from showing the step
        if is_submit(request):
            return self.post(request, *args, **kwargs)
        return self.get(request, *args, **kwargs)

    def load_draft(self) -> WizardState | None:
        """The request's wizard state, or None if the draft can't be loaded: its token
        expired, was tampered with or encrypted with a rotated secret, or there is none
        on a later step (e.g. its URL opened in another tab). Without a token, only the
        first step starts a new draft."""
        if (
            not self.request.POST.get(STATE_POST_FIELD)
            and self.step != WizardStep.CHOOSE_VLOPSES
        ):
            return None
        try:
            state = load_wizard_state(self.request)
        except WizardStateExpiredError, SuspiciousOperation:
            return None
        if state["vlopses"]:
            existing = set(
                Vlopse.objects.filter(id__in=state["vlopses"]).values_list(
                    "id", flat=True
                )
            )
            state["vlopses"] = [i for i in state["vlopses"] if i in existing]
        return state

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
        """Returns the response of the step to show if checks fail via self.go_to(),
        None otherwise.
        """
        return None

    def get_step_context(self) -> dict[str, Any]:
        """Extra template context, applied however the step gets rendered."""
        return {}

    def go_to(self, step_cls: type[WizardFormStep] | None) -> HttpResponse:
        """Render another step with the current state, without its dispatch;
        check_prerequisites still applies.
        """
        # TODO: Handle None (or drop it from possibilities)
        nxt = step_cls()
        nxt.setup(self.request)
        nxt.state = self.state
        return nxt.check_prerequisites() or nxt.render_step(nxt.get_form())

    def render_step(
        self, form: forms.Form, context: dict | None = None
    ) -> HttpResponse:
        context = {**self.get_step_context(), **(context or {})}
        response = render(
            self.request,
            "dsa40_wizard/_step.html",
            {
                "step_template": self.template_name,
                "current_step": self.step,
                "wizard_urls": get_wizard_urls(),
                "form": form,
                **context,
            },
        )

        response = self.add_response_headers(response)
        url = get_step_url(self.step)
        requested_step = self.request.resolver_match.kwargs.get("step")
        if is_submit(self.request) and requested_step != self.step:
            # submitted and moved on to another step: new browser history entry
            push_url(response, url)
        else:
            # load, back/forward, redirect or validation errors: a push would add
            # a duplicate entry and drop the forward history
            replace_url(response, url)
        return response

    def add_response_headers(self, response: HttpResponse) -> HttpResponse:
        """Re-issue the wizard state token (sliding expiry) and send this draft's ID,
        file key and TTL."""
        response[STATE_REQUEST_HEADER] = dump_wizard_state(self.state)
        response[WIZARD_ID_HEADER] = self.state["wizard_id"]
        response[FILE_KEY_HEADER] = encode_file_encryption_key(self.state["wizard_id"])
        response[MAX_STATE_AGE_HEADER] = str(MAX_STATE_AGE)
        return response


class VlopseSelectionStep(WizardFormStep):
    step = WizardStep.CHOOSE_VLOPSES
    template_name = "dsa40_wizard/_vlopse_selection_form.html"
    form_class = VlopseSelectionForm

    def get_form_kwargs(self) -> dict[str, Any]:
        return {"initial": {"vlopses": self.state["vlopses"]}}

    def get_form(self, data: dict | None = None) -> forms.Form:
        if data is None and self.state["vlopses"]:
            # bound to the stored selection, so the step shows why it is invalid
            data = {"vlopses": self.state["vlopses"]}
        return super().get_form(data)

    def update_state(self, form: forms.Form) -> None:
        """Update state in place and drop answers for deselected Vlopses."""
        vlopse_ids = [v.id for v in form.cleaned_data["vlopses"]]
        active_qs = {
            str(fq.question.key) for fq in get_mapped_vlopse_questions(vlopse_ids)
        }
        self.state["vlopses"] = vlopse_ids
        self.state["answers"] = {
            k: v for k, v in self.state["answers"].items() if k in active_qs
        }


class QuestionsStep(WizardFormStep):
    step = WizardStep.ENTER_DETAILS
    template_name = "dsa40_wizard/_questions_form.html"
    form_class = QuestionsForm

    def check_prerequisites(self) -> HttpResponse | None:
        """Checks that at least one VLOPSE is selected and each has a config."""
        if not has_vlopse_configs(self.state):
            return self.go_to(VlopseSelectionStep)
        return None

    def get_form_kwargs(self) -> dict[str, Any]:
        return {
            "form_questions": self.form_questions(),
            "initial": self.state["answers"],
        }

    def update_state(self, form: forms.Form) -> None:
        self.state["answers"] = dict(form.cleaned_data)


class ReviewStep(WizardFormStep):
    """Renders the DSAQuestion answers read-only to review."""

    step = WizardStep.REVIEW
    template_name = "dsa40_wizard/_review.html"
    form_class = QuestionsForm
    # the same questions and answers as the questions step, read-only
    get_form_kwargs = QuestionsStep.get_form_kwargs

    def get_answers_form(self) -> QuestionsForm:
        """The stored answers, bound and validated."""
        form = self.form_class(data=self.state["answers"], **self.get_form_kwargs())
        form.is_valid()
        return form

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        form = self.get_answers_form()
        if form.errors:
            return self.go_to(QuestionsStep)
        return self.render_step(form)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        # the page submits no answers: confirm the stored ones and move on
        if self.get_answers_form().errors:
            return self.go_to(QuestionsStep)
        return self.go_to(self.next_step)

    def get_form(self, data: dict | None = None) -> forms.Form:
        # reached via go_to: show the stored answers, not an empty form
        return self.get_answers_form()

    def check_prerequisites(self) -> HttpResponse | None:
        """Checks that at least one VLOPSE is selected and each has a config, and that
        the questions step stored an answer for every mapped question."""
        if not has_vlopse_configs(self.state):
            return self.go_to(VlopseSelectionStep)
        answers = self.state["answers"]
        if any(fq.question.key not in answers for fq in self.form_questions()):
            return self.go_to(QuestionsStep)
        return None


class GenerateStep(ReviewStep):
    """Renders one read-only application preview per selected VLOPSE: the stored
    answers mapped to the VLOPSE's questions."""

    step = WizardStep.GENERATE
    template_name = "dsa40_wizard/_generate.html"

    def get_step_context(self) -> dict[str, list[VlopseApplicationPreview]]:
        input_types = {
            fq.question.key: fq.question.input_type for fq in self.form_questions()
        }
        return {
            "application_previews": build_application_previews(
                self.state["vlopses"], self.state["answers"], input_types
            )
        }

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        # TODO: Allow application creation if logged in
        # TODO: Validate uploaded files against their content (type, size, SHA-256)
        #  before storing;
        raise NotImplementedError


class WizardDraftUnavailableView(TemplateView):
    template_name = "dsa40_wizard/draft_unavailable.html"
    extra_context = {"state_ttl": int(MAX_STATE_AGE / 60 / 60)}


VlopseSelectionStep.next_step = QuestionsStep
QuestionsStep.next_step = ReviewStep
ReviewStep.next_step = GenerateStep


STEP_VIEWS: dict[WizardStep, Callable[..., HttpResponseBase]] = {
    view.step: view.as_view()
    for view in (VlopseSelectionStep, QuestionsStep, ReviewStep, GenerateStep)
}


def route_wizard_step(request: HttpRequest, step: WizardStep) -> HttpResponseBase:
    """Route create/<step>/ (show) and create/<step>/submit/ (submit, see is_submit) to
    the view of that WizardStep slug: one URL pattern each for all steps, so links are
    built by slug. 404 for unknown steps and steps without a view yet (submit)."""
    view = STEP_VIEWS.get(step)
    if view is None:
        raise Http404
    return view(request)
