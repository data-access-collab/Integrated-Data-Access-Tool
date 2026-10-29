from typing import TYPE_CHECKING

from idat.dsa40_form_handler.schema import (
    Answer,
    MappedAnswer,
    MappingError,
    MappingResult,
    PlatformMapping,
    PlatformMappingComplex,
)

from .config import get_vlopse_configuration_for
from .mapping import Mapping, hydrate_mapping
from .operator import (
    AbstractOperator,
    OperatorExecutionError,
    hydrate_operator,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class OperatorValidationError(Exception):
    def __init__(self, message: str, loc: tuple[str, ...]) -> None:
        super().__init__({"message": message, "loc": loc})


class ValidationErrors(ExceptionGroup):
    def derive(self, excs: Sequence[Exception]) -> ValidationErrors:
        return ValidationErrors(self.message, excs)


class TransformationError(Exception):
    def __init__(
        self, message: str, loc: tuple[str, ...], inputs: list[str], cause: str
    ) -> None:
        super().__init__(
            {"message": message, "loc": loc, "inputs": inputs, "cause": cause}
        )


class Transformation:
    mapping: Mapping
    operator: AbstractOperator

    def __init__(self, mapping: Mapping, operator: AbstractOperator) -> None:
        self.mapping = mapping
        self.operator = operator

    def validate_args(self, args: list[Answer]) -> None:
        missing = [
            dsa_question
            for dsa_question in self.mapping.dsa_ids
            if dsa_question not in [a.question_id for a in args]
        ]

        if missing:
            es = [
                OperatorValidationError(message="missing required argument", loc=(m,))
                for m in missing
            ]
            msg = "missing arguments for {vlopse_question_id}"
            raise ValidationErrors(msg, es)

    def transform(self, args: list[Answer]) -> str:
        try:
            if len(args) == 1:
                result = self.operator.apply(args[0].value)
            else:
                result = self.operator.apply([a.value for a in args])
        except OperatorExecutionError as e:
            cause = e.args[0]
            loc = tuple([a.question_id for a in args])
            raise TransformationError(
                message="transformation failed",
                inputs=cause["inputs"],
                loc=loc,
                cause=cause["message"],
            ) from e
        return result


class AnswerTransformer:
    _mapping: dict[str, PlatformMapping]

    @classmethod
    def from_vlopse_name(cls, vlopse: str) -> AnswerTransformer:
        mapping = get_vlopse_configuration_for(vlopse).mappings
        return cls(mapping)

    def __init__(self, mapping: dict[str, PlatformMapping]) -> None:
        self._mapping = mapping

    def _get_mapping_operator(
        self, question_id: str
    ) -> str | PlatformMappingComplex | None:
        return self._mapping.get(question_id)

    def transform(
        self, answers: list[Answer], mapper: Mapping, op: AbstractOperator
    ) -> MappingResult:
        transformation = Transformation(mapper, op)

        transformation.validate_args(answers)
        output = transformation.transform(answers)
        return MappedAnswer(question_id=mapper.vlopse_id, value=output)

    def transform_safe(
        self, answers: list[Answer], mapper: Mapping, op: AbstractOperator
    ) -> MappingError | MappingResult:
        transformation = Transformation(mapper, op)
        question_id = mapper.vlopse_id
        try:
            transformation.validate_args(answers)
            output = transformation.transform(answers)
            answer = MappedAnswer(question_id=question_id, value=output)
        except ValidationErrors as e:
            errors = [
                {
                    "type": "type_error",
                    "loc": (question_id, *err.args[0]["loc"]),
                    "message": err.args[0]["message"],
                }
                for err in e.exceptions
            ]
            answer = MappingError(question_id=question_id, errors=errors)
        except TransformationError as e:
            e = e.args[0]
            loc = (*e["loc"], question_id)
            errors = [
                {
                    "type": "type_error",  # TODO: this could be more specific?
                    "loc": loc,
                    "message": e["message"],
                    "input": e["inputs"],
                }
            ]
            return MappingError(question_id=question_id, errors=errors)

        return answer

    def map(self, answers: list[Answer]) -> list[MappingResult]:
        answer_map = {a.question_id: a for a in answers}
        result: list[MappingResult] = []
        for vlopse_question, operator in self._mapping.items():
            mapper = hydrate_mapping(vlopse_question, operator)
            op = hydrate_operator(operator)
            if isinstance(operator, str):
                inputs = [answer_map[operator]]
            elif isinstance(operator.src, list):
                inputs = [a for a in answers if a.question_id in operator.src]
            elif isinstance(operator.src, str):
                inputs = [answer_map[operator.src]]
            else:
                msg = f"Unknown operation {operator}"
                raise TypeError(msg)
            output = self.transform_safe(inputs, mapper, op)
            result.append(output)

        return result
