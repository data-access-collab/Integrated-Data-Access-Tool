"""The tips of the help panel: which WizardInfos a wizard page shows, and where.

All WizardInfos are loaded at once into a HelpIndex, cached until one changes
(signals.py); find_help_tips() picks a page's tips from it without querying.

The panel has two levels:
- general: the tips of the step and of the shown section (Enter details);
- question: the tips of one question.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.core.cache import cache

from idat.dsa40_form_handler.models import DSAQuestion
from idat.dsa40_wizard.models import WizardInfo

if TYPE_CHECKING:
    from idat.dsa40_form_handler.models import VLOPSEQuestion
    from idat.dsa40_wizard.forms import QuestionsForm
    from idat.dsa40_wizard.steps import WizardStep


HELP_INDEX_CACHE_KEY = "dsa40_wizard:help_index"
# a safety net: signals don't fire for raw loads or QuerySet.update()
HELP_INDEX_TIMEOUT = 60 * 60


# a question as an index key: ("dsa" | "vlopse", pk)
QuestionRef = tuple[str, int]


@dataclass(frozen=True)
class HelpIndex:
    """All WizardInfos by target, each list in WizardInfo order (order, pk)."""

    by_step: dict[str, list[WizardInfo]]
    by_section: dict[str, list[WizardInfo]]
    by_question: dict[QuestionRef, list[WizardInfo]]


def question_ref(question: DSAQuestion | VLOPSEQuestion) -> QuestionRef:
    kind = "dsa" if isinstance(question, DSAQuestion) else "vlopse"
    return kind, question.pk


def load_help_index() -> HelpIndex:
    """Build the index from the database (three queries). The question links come
    from the link tables, not prefetch_related, so the cached instances stay
    small."""
    infos = {info.pk: info for info in WizardInfo.objects.all()}
    dsa_links = WizardInfo.dsa_questions.through.objects.values_list(
        "wizardinfo_id", "dsaquestion_id"
    )
    vlopse_links = WizardInfo.vlopse_questions.through.objects.values_list(
        "wizardinfo_id", "vlopsequestion_id"
    )

    index = HelpIndex(by_step={}, by_section={}, by_question={})
    for info in infos.values():
        for step in info.steps:
            index.by_step.setdefault(step, []).append(info)
        for section in info.sections:
            index.by_section.setdefault(section, []).append(info)
    for kind, links in [("dsa", dsa_links), ("vlopse", vlopse_links)]:
        for info_pk, question_pk in links:
            index.by_question.setdefault((kind, question_pk), []).append(infos[info_pk])
    for tips in index.by_question.values():
        tips.sort(key=info_order)
    return index


def info_order(info: WizardInfo) -> tuple[int, int]:
    """WizardInfo.Meta.ordering, for lists merged in Python."""
    return info.order, info.pk


def get_help_index() -> HelpIndex:
    """The cached index; loaded on first use and after a WizardInfo changed."""
    index = cache.get(HELP_INDEX_CACHE_KEY)
    if index is None:
        index = load_help_index()
        cache.set(HELP_INDEX_CACHE_KEY, index, HELP_INDEX_TIMEOUT)
    return index


def clear_help_index() -> None:
    cache.delete(HELP_INDEX_CACHE_KEY)


@dataclass
class HelpTip:
    """A WizardInfo as shown on one page."""

    info: WizardInfo

    # Not question specific tips only: the form sections (question categories)
    # the tip is shown with (None = relates to the whole step).
    sections: list[str] | None = None


@dataclass
class TipList:
    """Tips by presentation, each in WizardInfo order."""

    cards: list[HelpTip] = field(default_factory=list)
    accordions: list[HelpTip] = field(default_factory=list)

    def add(self, tip: HelpTip) -> None:
        if tip.info.presentation == WizardInfo.Presentation.ACCORDION:
            self.accordions.append(tip)
        else:
            self.cards.append(tip)

    def __bool__(self) -> bool:
        return bool(self.cards or self.accordions)


@dataclass
class QuestionTips:
    """The tips of one question of the form."""

    key: str  # field name
    label: str  # question text
    tips: TipList


@dataclass
class HelpTips:
    """The tips of a page."""

    # section tips first, then step tips
    general: TipList
    # in form order; only questions with tips
    questions: list[QuestionTips]

    @property
    def has_cards(self) -> bool:
        return bool(self.general.cards) or any(q.tips.cards for q in self.questions)


def find_help_tips(
    step: WizardStep,
    form: QuestionsForm | None = None,
    index: HelpIndex | None = None,
) -> HelpTips:
    """The tips of a step: general ones targeting the step or, with a questions
    form, one of its sections; and per question of the form, the ones targeting it.
    `index` defaults to the cached one.

    - An WizardInfo can be both a general tip and a question tip, and the tip of several
      questions.
    - An info targeting the step is a step tip, even if it targets sections too.
    - A question belongs to the section the form shows it in (unknown categories
      land in "General"), not to its category.
    """
    index = index or get_help_index()
    form_sections = [section.category for section in form.sections] if form else []

    step_infos = index.by_step.get(step, [])
    step_pks = {info.pk for info in step_infos}
    section_infos = {
        info.pk: info
        for section in form_sections
        for info in index.by_section.get(section, [])
        if info.pk not in step_pks
    }

    general = TipList()
    for info in sorted(section_infos.values(), key=info_order):
        sections = [s for s in form_sections if s in info.sections]
        general.add(HelpTip(info, sections))
    for info in step_infos:
        general.add(HelpTip(info))

    questions = []
    for key, question in (form.questions if form else {}).items():
        tips = TipList()
        for info in index.by_question.get(question_ref(question), []):
            tips.add(HelpTip(info))
        if tips:
            questions.append(
                QuestionTips(key=key, label=str(form.fields[key].label), tips=tips)
            )
    return HelpTips(general=general, questions=questions)
