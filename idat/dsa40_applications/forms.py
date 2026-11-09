from __future__ import annotations

import itertools
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from typing import NamedTuple

from django import forms
from django.core.exceptions import ValidationError

from idat.core.forms.base import IdatBaseForm
from idat.core.forms.fields import YesNoField, country_field
from idat.dsa40_applications.sections import SECTION_META
from idat.dsa40_form_handler.models import (
    DSAQuestion,
    InputType,
    QuestionCategory,
    VLOPSEQuestion,
)
from idat.vlopse.models import Vlopse

logger = logging.getLogger(__name__)

CLIENT_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10 MB

# file types the client file field knows: extension -> content type; fields
# pick their subset. The browser only checks the extension; the file's content
# must be checked when it is saved.
CLIENT_FILE_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
}
DEFAULT_CLIENT_FILE_TYPES = (".pdf", ".docx")
SHA256_RE = re.compile(r"[0-9a-f]{64}")


class VlopseSelectionForm(IdatBaseForm):
    vlopses = forms.ModelMultipleChoiceField(
        queryset=Vlopse.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={"required": "Please select at least one VLOPSE"},
    )


class ClientFileWidget(forms.Widget):
    """File input whose file stays in the browser.

    The file input itself has no name and is never submitted. The browser
    validates and encrypts the file, stores it in IndexedDB and submits only
    its metadata ({name, size, type, sha256}) as JSON in a hidden input.
    """

    template_name = "dsa40_applications/widgets/client_file.html"

    def __init__(
        self,
        attrs: dict | None = None,
        types: tuple[str, ...] = DEFAULT_CLIENT_FILE_TYPES,
    ) -> None:
        super().__init__(attrs)
        self.types = types

    def use_required_attribute(self, initial: object) -> bool:
        # the file input is empty once a file is stored in the browser
        return False

    def format_value(self, value: object) -> str:
        if not value:
            return ""
        return value if isinstance(value, str) else json.dumps(value)

    def get_context(self, name: str, value: object, attrs: dict | None) -> dict:
        context = super().get_context(name, value, attrs)
        context["widget"].update(
            {
                "max_size": CLIENT_FILE_MAX_SIZE,
                "types": json.dumps(
                    {ext: CLIENT_FILE_TYPES[ext] for ext in self.types}
                ),
                "accept": ",".join(self.types),
            }
        )
        return context


def validate_client_file_metadata(value: object) -> None:
    """Check the shape of the metadata the browser reports for a file.

    The server never sees the file here, so it cannot verify type or size; the
    browser does that, and the file itself is validated when it is saved. This
    only keeps malformed values out of the wizard state.
    """
    if not (
        isinstance(value, dict)
        and value.keys() == {"name", "size", "type", "sha256"}
        and isinstance(value["name"], str)
        and 0 < len(value["name"]) <= 255  # noqa: PLR2004
        and isinstance(value["type"], str)
        and len(value["type"]) <= 255  # noqa: PLR2004
        and isinstance(value["size"], int)
        and value["size"] > 0
        and isinstance(value["sha256"], str)
        and SHA256_RE.fullmatch(value["sha256"])
    ):
        msg = "Please select the file again."
        raise ValidationError(msg, code="invalid")


class ClientFileField(forms.JSONField):
    """Metadata of a file kept in the browser.

    `types` are the accepted extensions (keys of CLIENT_FILE_TYPES); the browser
    checks them before storing the file.
    """

    default_validators = [validate_client_file_metadata]

    def __init__(
        self, *, types: tuple[str, ...] = DEFAULT_CLIENT_FILE_TYPES, **kwargs
    ) -> None:
        if unknown := set(types) - CLIENT_FILE_TYPES.keys():
            msg = f"Unknown client file types: {', '.join(sorted(unknown))}"
            raise ValueError(msg)
        self.types = tuple(types)
        kwargs.setdefault("widget", ClientFileWidget(types=self.types))
        super().__init__(**kwargs)

    def bound_data(self, data: object, initial: object) -> object:
        # bound to already parsed metadata (e.g. stored answers), not JSON text
        return data if isinstance(data, dict) else super().bound_data(data, initial)

    def prepare_value(self, value: object) -> object:
        # keep dicts for the review; the widget serializes them
        return value


def get_question_choices(
    question: DSAQuestion | VLOPSEQuestion,
) -> list[tuple[str, str]]:
    """Get choices from the question's config["options"]."""
    if not isinstance(question.config, dict):
        return []
    return [(option, option) for option in question.config.get("options", [])]


def get_question_field(question: DSAQuestion | VLOPSEQuestion) -> forms.Field:  # noqa: PLR0911
    """Get the correct form field for a question's input_type.

    A selection without options could never be answered: it falls back to a text
    field and logs a warning, so the data gets fixed.
    """
    is_selection = question.input_type in (InputType.SELECTION, InputType.MULTI_SELECT)
    if is_selection and not get_question_choices(question):
        logger.warning(
            "Question %s is a %s without options; showing a text field.",
            question.key,
            question.input_type,
        )
        return forms.CharField()

    match question.input_type:
        case InputType.TEXT:
            return forms.CharField()
        case InputType.ISO_3166_1:
            return country_field()
        case InputType.FILE_UPLOAD:
            return ClientFileField()
        case InputType.SELECTION:
            choices = get_question_choices(question)
            # Yes / No in any order; the toggle always shows Yes first
            if set(choices) == set(YesNoField.CHOICES):
                return YesNoField()
            return forms.ChoiceField(choices=choices)
        case InputType.MULTI_SELECT:
            return forms.MultipleChoiceField(choices=get_question_choices(question))
        case InputType.DATE_SELECT:
            return forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
        case _:
            return forms.CharField()


@dataclass(eq=False)
class FormSection:
    """The fields of one question category, as one section of the form."""

    category: str
    label: str
    icon: str
    description: str
    fields: list[forms.BoundField]
    # neighbouring sections, for Back / Next
    previous: FormSection | None = field(default=None, repr=False)
    next: FormSection | None = field(default=None, repr=False)

    @property
    def total(self) -> int:
        return len(self.fields)

    @property
    def answered(self) -> int:
        return sum(1 for f in self.fields if not is_unanswered(f.value()))

    @property
    def complete(self) -> bool:
        return self.answered == self.total

    @property
    def has_errors(self) -> bool:
        return any(f.errors for f in self.fields)


def is_unanswered(value: object) -> bool:
    """Whether an answer value counts as not answered: None, blank text, or an
    empty selection or file."""
    if isinstance(value, str):
        return not value.strip()
    return value in (None, [], {})


# UI library field component per question input type (QuestionBoundField.kind)
QUESTION_KINDS = {
    InputType.TEXT: "text",
    InputType.ISO_3166_1: "country",
    InputType.FILE_UPLOAD: "file",
    InputType.SELECTION: "select",
    InputType.MULTI_SELECT: "multi-select",
    InputType.DATE_SELECT: "date",
}


class FormQuestion(NamedTuple):
    """A question for a QuestionsForm, and whether the form requires an answer."""

    question: DSAQuestion | VLOPSEQuestion
    required: bool


class QuestionBoundField(forms.BoundField):
    @property
    def kind(self) -> str:
        """Which field component renders the question (see _questions_form.html)."""
        if isinstance(self.field, YesNoField):
            return "yes-no"
        if type(self.field) is forms.CharField:
            # includes selections without options (see get_question_field)
            return "text"
        input_type = self.form.questions[self.name].input_type
        return QUESTION_KINDS.get(input_type, "text")


class QuestionsForm(IdatBaseForm):
    bound_field_class = QuestionBoundField

    def __init__(
        self,
        *args,
        form_questions: list[FormQuestion],
        **kwargs,
    ) -> None:
        """One field per form question. Prefill answers with Django's `initial`
        ({question key: value}); a bound form shows its data instead."""
        super().__init__(*args, **kwargs)
        # the question behind each field, by field name (= question key)
        self.questions: dict[str, DSAQuestion | VLOPSEQuestion] = {}
        for question, required in form_questions:
            self.add_question_field(question, required)

    def add_question_field(
        self, question: DSAQuestion | VLOPSEQuestion, required: bool
    ) -> None:
        field = get_question_field(question)
        field.label = question.text
        field.required = required
        if isinstance(question, DSAQuestion):
            field.help_text = question.help_text
        self.fields[question.key] = field
        self.questions[question.key] = question

    @cached_property
    def sections(self) -> list[FormSection]:
        """The fields grouped by question category, in SECTION_META order.

        Categories without questions are left out. Within a section, fields keep
        the order of form_questions.

        DSA questions (Enter details) and VLOPSE questions (per-platform forms
        = applications) are grouped by their own category.
        """
        # TODO: Order fields within a section explicitly (e.g. first name before
        #  email). Currently, they just follow form_questions, which follow the $
        #  question mapper, so we should consider an `order` field on DSAQuestion
        #  (and VlopseQuestion).
        fields: dict[str, list[forms.BoundField]] = defaultdict(list)
        for bound_field in self:
            category = self.questions[bound_field.name].category
            if category not in SECTION_META:
                # unknown category: still shown, under "Other"
                category = QuestionCategory.GENERAL
            fields[category].append(bound_field)

        sections = []
        for category in SECTION_META:
            if not fields[category]:
                continue
            meta = SECTION_META[category]
            sections.append(
                FormSection(
                    category=category,
                    label=meta.label or QuestionCategory(category).label,
                    icon=meta.icon,
                    description=meta.description,
                    fields=fields[category],
                )
            )
        for previous, following in itertools.pairwise(sections):
            previous.next = following
            following.previous = previous
        return sections

    @property
    def initial_section(self) -> str:
        """The section to show first: the first one with errors, else the first."""
        sections = self.sections
        for section in sections:
            if section.has_errors:
                return section.category
        return sections[0].category if sections else ""
