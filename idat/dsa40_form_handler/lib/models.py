from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class PlatformMappingComplex(BaseModel):
    src: str | list[str]
    operation: str


PlatformMapping = str | PlatformMappingComplex


class VlopseAnswer(BaseModel):
    id: str
    value: str


class Answer(BaseModel):
    question_id: str
    value: str | None


class MappingResult(BaseModel):
    question_id: str


class MappedAnswer(MappingResult):
    type: Literal["result"] = "result"
    value: str


class ErrorDetails(BaseModel):
    type: Literal["type_error", "value_error"]
    loc: list[str]
    message: str


class MappingError(MappingResult):
    type: Literal["error"] = "error"
    errors: list[ErrorDetails]


class Operator(StrEnum):
    eq = "eq"
    neq = "neq"


class Condition(BaseModel):
    question_id: str
    operator: Operator
    value: str
