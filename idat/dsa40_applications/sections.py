"""How each question category is presented as a section of the questions form."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from idat.dsa40_form_handler.models import QuestionCategory


@dataclass(frozen=True)
class SectionMeta:
    icon: str  # a file in templates/icons/
    description: str = ""
    label: str = ""  # overrides the category's label


# One entry per category, in the order the sections appear: "Other" (the fallback
# for general and unknown categories) last.
SECTION_META: dict[str, SectionMeta] = {
    QuestionCategory.CONTACT: SectionMeta(
        icon="user",
        description=_("How the platforms can reach you."),
    ),
    QuestionCategory.COLLABORATION: SectionMeta(
        icon="users",
        description=_("Who else works on the project."),
    ),
    QuestionCategory.QUALIFICATIONS: SectionMeta(
        icon="bookmark",
        description=_("Your academic background and expertise."),
    ),
    QuestionCategory.AFFILIATION: SectionMeta(
        icon="building",
        description=_("The research organisation you work for or with."),
    ),
    QuestionCategory.FUNDING: SectionMeta(
        icon="coins",
        description=_(
            "Who funds the research, and its independence from commercial interests."
        ),
    ),
    QuestionCategory.RESEARCH_PROJECT: SectionMeta(
        icon="flask",
        description=_(
            "What you want to find out, and how it relates to systemic risks."
        ),
    ),
    QuestionCategory.TECHNICAL: SectionMeta(
        icon="wrench",
        description=_("How you will access and process the data."),
    ),
    QuestionCategory.REQUESTED_DATA: SectionMeta(
        icon="database",
        description=_("Which data you need, and why."),
    ),
    QuestionCategory.EXPERIENCE: SectionMeta(
        icon="clock",
        description=_("Earlier data access requests to the platforms."),
    ),
    QuestionCategory.DATA_SECURITY: SectionMeta(
        icon="shield",
        description=_("How you will keep the data secure."),
    ),
    QuestionCategory.LEGAL: SectionMeta(
        icon="file-text",
        description=_("Legal basis, consent and terms."),
    ),
    QuestionCategory.GENERAL: SectionMeta(
        icon="layout-grid",
        label=_("Other"),
    ),
}
