"""What each VLOPSE's application contains: the stored wizard answers mapped to
the platform's questions. Shown in the review step, the basis for generating."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pycountry

from idat.dsa40_form_handler.models import InputType, VLOPSEQuestion
from idat.dsa40_form_handler.schema import Answer as MappingInput
from idat.dsa40_form_handler.schema import MappedAnswer, MappingError
from idat.dsa40_form_handler.validation.config import get_vlopse_configuration_for
from idat.dsa40_form_handler.validation.mapping import hydrate_mapping
from idat.dsa40_form_handler.validation.transform import AnswerTransformer
from idat.dsa40_wizard.forms import FormQuestion, QuestionsForm, is_unanswered
from idat.vlopse.models import Vlopse

if TYPE_CHECKING:
    from idat.dsa40_form_handler.schema import ErrorDetails


@dataclass
class VlopseApplicationPreview:
    """A VLOPSE application in the review step: its answers in a read-only form.

    `mapping_errors` maps question text to message for answers the platform's
    mapping could not use (e.g. an unknown country). Unanswered questions are not
    errors: they show as empty in the form.
    """

    vlopse_name: str
    form: QuestionsForm
    mapping_errors: dict[str, str] = field(default_factory=dict)


def to_mapping_input_value(value: Any, input_type: str | None) -> str | None:  # noqa: ANN401
    """Convert one stored wizard answer into a mapping operator input string
    accepted by AnswerTransformer.map.

    "DE" (country) -> "Germany", ["Posts", "Comments"] -> "Posts, Comments",
    file metadata -> its JSON; unanswered (see is_unanswered) -> None.
    """
    if is_unanswered(value):
        return None
    if input_type == InputType.ISO_3166_1:
        # stored as an alpha-2 code (country_field); make-iso expects the name
        country = pycountry.countries.get(alpha_2=value)
        return country.name if country else value
    if isinstance(value, list):  # multi-select
        return ", ".join(value)
    if isinstance(value, dict):  # file metadata: ClientFileField parses it back
        return json.dumps(value)
    return str(value)


def build_mapping_input(
    state_answers: dict[str, Any], input_types: dict[str, str]
) -> list[MappingInput]:
    """The wizard state's DSA answers ({DSA question key: value}) as input for the
    mapping engine (AnswerTransformer), converted per question input type."""
    return [
        MappingInput(
            question_id=key,
            value=to_mapping_input_value(value, input_types.get(key)),
        )
        for key, value in state_answers.items()
    ]


def build_application_preview(
    vlopse: Vlopse, mapping_input: list[MappingInput]
) -> VlopseApplicationPreview:
    """Map the DSAQuestion answers to the VLOPSEQuestions and bind them to a
    read-only form.

    Lists every question the VLOPSE maps, answered or not.
    Assumes that all required questions are answered when this stage is reached.
    """
    # TODO: Update the form_handler site to not read files from disk on every call
    mappings = get_vlopse_configuration_for(vlopse.name).mappings
    answered = {i.question_id for i in mapping_input if i.value is not None}

    values: dict[str, str] = {}
    errors: dict[str, list[ErrorDetails]] = {}
    for result in AnswerTransformer(mappings).map(mapping_input):
        key = result.question_id
        if isinstance(result, MappedAnswer):
            values[key] = result.value
        elif isinstance(result, MappingError):
            # operators reject empty input:
            #  only an error if something was answered (= intersection exists)
            sources = hydrate_mapping(key, mappings[key]).dsa_ids
            if answered.intersection(sources):
                errors[key] = result.errors

    questions = list(
        VLOPSEQuestion.objects.filter(vlopse=vlopse, key__in=mappings.keys())
    )
    texts = {q.key: q.text for q in questions}
    return VlopseApplicationPreview(
        vlopse_name=vlopse.name,
        form=QuestionsForm(
            data=values,
            form_questions=[FormQuestion(q, q.required) for q in questions],
        ),
        mapping_errors={
            texts.get(key, key): "; ".join(e.message for e in errs)
            for key, errs in errors.items()
        },
    )


def build_application_previews(
    vlopse_ids: list[int],
    state_answers: dict[str, Any],
    input_types: dict[str, str],
) -> list[VlopseApplicationPreview]:
    """One preview per selected VLOPSE, in selection order; unknown ids are skipped."""
    mapping_input = build_mapping_input(state_answers, input_types)
    vlopses = Vlopse.objects.in_bulk(vlopse_ids)
    return [
        build_application_preview(vlopses[vlopse_id], mapping_input)
        for vlopse_id in vlopse_ids
        if vlopse_id in vlopses
    ]
