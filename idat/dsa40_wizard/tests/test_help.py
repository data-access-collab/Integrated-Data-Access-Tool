from __future__ import annotations

import pytest

from idat.dsa40_form_handler.models import QuestionCategory
from idat.dsa40_form_handler.tests.factories import DsaQuestionFactory
from idat.dsa40_wizard.forms import FormQuestion, QuestionsForm
from idat.dsa40_wizard.help import clear_help_index, find_help_tips, get_help_index
from idat.dsa40_wizard.models import WizardInfo
from idat.dsa40_wizard.steps import WizardStep

pytestmark = pytest.mark.django_db

CONTACT = QuestionCategory.CONTACT
LEGAL = QuestionCategory.LEGAL
DETAILS = WizardStep.ENTER_DETAILS


@pytest.fixture(autouse=True)
def _clear_help_index():
    """The index is cached across tests; signals clear it only after a commit."""
    clear_help_index()


@pytest.fixture
def form() -> QuestionsForm:
    """Questions t-email and t-name (contact details), t-licence (legal)."""
    questions = [
        DsaQuestionFactory(key=key, category=category, input_type="text")
        for key, category in [
            ("t-email", CONTACT),
            ("t-name", CONTACT),
            ("t-licence", LEGAL),
        ]
    ]
    return QuestionsForm(form_questions=[FormQuestion(q, True) for q in questions])


def make_info(title, *, accordion=False, questions=(), **fields) -> WizardInfo:
    """A card (an accordion with accordion=True) linked to `questions`; fields:
    steps, sections, order …"""
    info = WizardInfo.objects.create(
        title=title,
        body="…",
        presentation="accordion" if accordion else "card",
        tone="" if accordion else "info",
        **fields,
    )
    info.dsa_questions.set(questions)
    return info


def titles(tips) -> list[str]:
    return [tip.info.title for tip in [*tips.cards, *tips.accordions]]


def by_question(tips) -> dict[str, list[str]]:
    return {q.key: titles(q.tips) for q in tips.questions}


def test_find_help_tips_general_puts_section_tips_before_step_tips(form):
    make_info("step", steps=[DETAILS], order=1)
    make_info("section", sections=[QuestionCategory.FUNDING, LEGAL, CONTACT], order=2)
    make_info("other step", steps=[WizardStep.REVIEW])
    make_info("section not in form", sections=[QuestionCategory.FUNDING])
    make_info("question only", questions=[form.questions["t-email"]])

    tips = find_help_tips(DETAILS, form).general

    assert titles(tips) == ["section", "step"]
    # the form's sections, in form order; None: the whole step
    assert [tip.sections for tip in tips.cards] == [[CONTACT, LEGAL], None]


def test_find_help_tips_groups_question_tips_by_question(form):
    email, licence = form.questions["t-email"], form.questions["t-licence"]
    make_info("both", accordion=True, questions=[email, licence], order=2)
    make_info("email", questions=[email], order=1)
    make_info("step and email", steps=[DETAILS], questions=[email], order=3)
    make_info("not in form", questions=[DsaQuestionFactory(key="t-other")])

    tips = find_help_tips(DETAILS, form)

    # form order, without questions that have no tips; cards, then accordions
    assert by_question(tips) == {
        "t-email": ["email", "step and email", "both"],
        "t-licence": ["both"],
    }
    # an info can be a general and a question tip
    assert titles(tips.general) == ["step and email"]


def test_find_help_tips_without_form_has_step_tips_only(form):
    make_info("step", steps=[WizardStep.REVIEW])
    make_info("section", sections=[LEGAL])
    make_info("question", questions=[form.questions["t-email"]])

    tips = find_help_tips(WizardStep.REVIEW)

    assert titles(tips.general) == ["step"]
    assert tips.questions == []


def test_set_help_tips_marks_questions_with_tips(form):
    make_info("email", questions=[form.questions["t-email"]])

    form.set_help_tips(find_help_tips(DETAILS, form))

    assert form["t-email"].help_tip == "t-email"
    assert form["t-licence"].help_tip == ""


def test_get_help_index_is_cached(django_assert_num_queries):
    make_info("step", steps=[DETAILS])
    get_help_index()

    with django_assert_num_queries(0):
        index = get_help_index()

    assert [info.title for info in index.by_step[DETAILS]] == ["step"]


def test_get_help_index_is_cleared_when_infos_change(
    form, django_capture_on_commit_callbacks
):
    def email_tips() -> list[str]:
        return by_question(find_help_tips(DETAILS, form)).get("t-email", [])

    email_tips()  # caches the empty index

    with django_capture_on_commit_callbacks(execute=True):
        info = make_info("email")  # saved, then linked
        info.dsa_questions.add(form.questions["t-email"])
    assert email_tips() == ["email"]

    with django_capture_on_commit_callbacks(execute=True):
        info.title = "renamed"
        info.save()
    assert email_tips() == ["renamed"]

    with django_capture_on_commit_callbacks(execute=True):
        info.delete()
    assert email_tips() == []
