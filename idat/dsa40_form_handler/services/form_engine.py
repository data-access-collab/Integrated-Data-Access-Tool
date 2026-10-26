from typing import TYPE_CHECKING

from pycountry import countries

from idat.dsa40_form_handler.lib.mapping import QuestionMapper
from idat.dsa40_form_handler.lib.models import (
    Answer,
    ErrorDetails,
    MappingError,
    MappingResult,
)
from idat.dsa40_form_handler.lib.transform import AnswerTransformer
from idat.dsa40_form_handler.models import DSAQuestion, InputType
from idat.dsa40_form_handler.services.questions import QuestionService

if TYPE_CHECKING:
    from collections.abc import Mapping


class AnswerToUnknownQuestion(BaseException):
    pass


class FormService:
    def __init__(self) -> None:
        self.question_service = QuestionService()

    def compute_options(self, question: DSAQuestion) -> list[str] | None:
        # TODO: think this should go to mapper and check dependent questions
        if question.input_type == InputType.ISO_3166_1:
            return [c.name for c in countries]
        return None

    def map_unified_to_vlopse_and_validate(
        self, answers: list[Answer], vlopses: list[str]
    ) -> tuple[bool, Mapping[str, list[ErrorDetails]]]:
        ok = True
        errors: dict[str, list[ErrorDetails]] = {}
        for vlopse in vlopses:
            # TODO: should not load questions or mappings but receive them
            transformer = AnswerTransformer.from_vlopse_name(vlopse)
            transformed = transformer.map(answers)
            if any(isinstance(t, MappingError) for t in transformed):
                ok = False
                for t in transformed:
                    if isinstance(t, MappingError):
                        errors[t.question_id] = t.errors

        return ok, errors

    def validate_unified_question(
        self, answers: list[Answer], vlopses: list[str]
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        mapper = QuestionMapper.from_vlopse_names(vlopses, self.question_service)
        mapped = mapper.map_vlopse_to_unified()

        for a in answers:
            # TODO: this should ask the db seperately.
            qs = [(req, q) for req, q in mapped if q.key == a.question_id]

            if not qs:
                msg = f"{a.question_id} not defined!"
                raise AnswerToUnknownQuestion(msg)
            is_required, q = qs[0]

            if is_required and (a.value is None or a.value == ""):
                result[q.id] = "None or empty string not allowed"
                continue
            config = q.parsed_config

            if config and a.value is not None:
                error = config.validate_answer(a.value)
                if error:
                    result[q.id] = error
        return result

    def get_mapped_questions_for(
        self, vlopses: list[str]
    ) -> list[tuple[bool, DSAQuestion]]:
        # FIXME: Question mapper should just build a mapping and provide traces, can be annotated in a amapper service later. this form engine is way too huge anyhow  # noqa: E501
        mapper = QuestionMapper.from_vlopse_names(vlopses, self.question_service)
        return mapper.map_vlopse_to_unified()

    def enhance_with_text(
        self, val: MappingError | MappingResult
    ) -> MappingError | MappingResult:
        q = self.question_service.get(val.question_id)
        text = str(q.text) if q else "N/A"
        v = val.model_dump()
        v["text"] = text
        return v

    def transform_answers_to_vlopse_answers(
        self, vlopses: list[str], answers: list[Answer]
    ) -> list[tuple[str, list[MappingResult] | list[str]]]:
        result = []
        for vlopse in vlopses:
            # TODO: should not load questions or mappings but receive them
            transformer = AnswerTransformer.from_vlopse_name(vlopse)
            transformed = [self.enhance_with_text(t) for t in transformer.map(answers)]
            result.append((vlopse, transformed))
        return result
