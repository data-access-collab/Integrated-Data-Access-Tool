from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from django.db import connection
from django.db.utils import Error as DjangoDatabaseError
from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Field, Query, Router, Schema
from ninja.errors import HttpError

from idat.dsa40.api.schema import (
    ActionOut,
    CreateDSAQuestionSchema,
    CreateVlopseQuestionSchema,
    CreateVlopseSchema,
    DSAQuestionOut,
    HealthOut,
    Status,
    UpdateVlopseSchema,
    VlopseOut,
    VlopseQuestionOut,
)
from idat.dsa40.lib.models import (
    Answer,
    Condition,
    ErrorDetails,
    MappedAnswer,
    MappingError,
)
from idat.dsa40.models import DSAQuestion, InputType, Vlopse, VLOPSEQuestion
from idat.dsa40.services.condition_service import ConditionService
from idat.dsa40.services.form_engine import FormService
from idat.dsa40.services.questions import QuestionService
from idat.dsa40.services.vlopse import VlopseConfigService

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.db.models import QuerySet
    from django.http import HttpRequest

health_router = Router(tags=["health"])


@health_router.get("", response=HealthOut, auth=None)
def retrieve_health(request: HttpRequest) -> HealthOut:
    """Report API liveness and DB connectivity."""
    db_status = Status.OK
    dsa_status = Status.ERROR  # TODO: Count number of DSA questions
    mapping_status = Status.ERROR  # TODO: Call validate on Mapper
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DjangoDatabaseError:
        db_status = Status.ERROR

    return HealthOut(
        api=Status.OK,
        db=db_status,
        dsa_status=dsa_status,
        mapping_status=mapping_status,
    )


vlopse_router = Router(tags=["vlopse"])


@vlopse_router.get("", response=list[VlopseOut], auth=None)
def list_vlopses(request: HttpRequest) -> QuerySet[Vlopse]:
    """List available VLOPSEs"""
    return Vlopse.objects.all()


@vlopse_router.get("/{name}", response=list[VlopseOut], auth=None)
def retrieve_vlopse(request: HttpRequest, name: str) -> list[Vlopse]:
    """Get specific VLOPSE by its name"""
    vlopse = get_object_or_404(Vlopse.objects.filter(name=name))
    return [vlopse]


@vlopse_router.post("", response={200: ActionOut}, auth=None)
def add_vlopse(
    request: HttpRequest, data: CreateVlopseSchema
) -> tuple[int, dict[str, bool]]:
    vlopse = Vlopse(name=data.id, **data.info.model_dump(exclude_unset=True))

    try:
        vlopse.full_clean()
    except ValidationError as e:
        raise HttpError(422, str(e.message_dict)) from e
    vlopse.save()
    return 200, {"success": True}


@vlopse_router.put("/{name}", response={200: ActionOut} | {404: ActionOut}, auth=None)
def update_vlopse(
    request: HttpRequest, name: str, data: UpdateVlopseSchema
) -> tuple[int, dict[str, bool]]:
    vlopse = Vlopse.objects.filter(name=name).first()
    if vlopse is None:
        return 404, {"success": False}
    vlopse.name = data.new_name
    vlopse.save()
    return 200, {"success": True}


@vlopse_router.delete(
    "/{name}",
    response={200: ActionOut} | {404: ActionOut} | {202: ActionOut},
    auth=None,
)
def delete_vlopse(request: HttpRequest, name: str) -> tuple[int, dict[str, bool]]:
    vlopse = Vlopse.objects.filter(name=name).first()
    if vlopse is None:
        return 404, {"success": False}
    vlopse.delete()
    return 200, {"success": True}


# QUESTIONS


@vlopse_router.get(
    "/{vlopse_name}/question", response=list[VlopseQuestionOut], auth=None
)
def list_vlopse_questions(
    request: HttpRequest, vlopse_name: str
) -> QuerySet[VLOPSEQuestion]:
    return VLOPSEQuestion.objects.filter(vlopse__name=vlopse_name)


@vlopse_router.get(
    "/{vlopse_name}/question/{question_id}",
    response=VlopseQuestionOut | None,
    auth=None,
)
def get_vlopse_question(
    request: HttpRequest, vlopse_name: str, question_id: str
) -> VLOPSEQuestion:
    vlopse_qs = VLOPSEQuestion.objects.filter(vlopse__name=vlopse_name, id=question_id)
    return get_object_or_404(vlopse_qs)


@vlopse_router.post("/{vlopse_name}/question", auth=None)
def create_vlopse_question(
    request: HttpRequest, vlopse_name: str, data: CreateVlopseQuestionSchema
) -> tuple[int, dict[str, bool]]:
    vlopse = get_object_or_404(Vlopse, name=vlopse_name)
    vlopse_question = VLOPSEQuestion(
        vlopse=vlopse, **data.model_dump(exclude_unset=True)
    )

    try:
        vlopse_question.full_clean()
    except ValidationError as e:
        raise HttpError(422, str(e.message_dict)) from e
    vlopse_question.save()
    return 200, {"success": True}


dsa_question_router = Router(tags=["dsa"])


@dsa_question_router.get("", response=list[DSAQuestionOut], auth=None)
def list_dsa_questions(request: HttpRequest) -> QuerySet[DSAQuestion]:
    return DSAQuestion.objects.filter()


@dsa_question_router.get(
    "/{question_id}",
    response=DSAQuestionOut | None,
    auth=None,
)
def get_dsa_question(request: HttpRequest, question_id: str) -> DSAQuestion:
    question_qs = DSAQuestion.objects.filter(id=question_id)
    return get_object_or_404(question_qs)


@dsa_question_router.post("", auth=None)
def create_dsa_question(
    request: HttpRequest, data: CreateDSAQuestionSchema
) -> tuple[int, dict[str, bool]]:
    dsa_question = DSAQuestion(**data.model_dump(exclude_unset=True))

    try:
        dsa_question.full_clean()
    except ValidationError as e:
        raise HttpError(422, str(e.message_dict)) from e
    dsa_question.save()
    return 200, {"success": True}


form_router = Router(tags=["form"])

service = VlopseConfigService()
form_service = FormService()
question_service = QuestionService()
condition_service = ConditionService()


@form_router.get(
    "questions",
    auth=None,
)
def applicable_questions(
    request: HttpRequest,
    vlopse: list[str] = Query(...),  # noqa: B008
) -> list[DSAQuestionOut]:
    selected_vlopses = Vlopse.objects.filter(name__in=vlopse)
    if len(selected_vlopses) != len(vlopse):
        names = [v.name for v in selected_vlopses]
        missing = [v for v in vlopse if v not in names]
        if missing:
            raise HttpError(322, f"Unknown vlopse(s): {missing}")

    qs = form_service.get_mapped_questions_for(vlopse)

    response: list[DSAQuestionOut] = []
    for req, q in qs:
        out = DSAQuestionOut.from_orm(q)
        opts = form_service.compute_options(q)
        if opts is not None:
            out.options = opts
        out.required = req
        response.append(out)

    return response


class PostDSAQuestionRequest(Schema):
    id: str
    text: str
    input_type: InputType
    help_text: str | None = None
    config: dict[str, str] | None = None


class MappedAnswerWithText(MappedAnswer):
    text: str


class MappingErrorWithText(MappingError):  # noqa: N818
    text: str


MappingResultWithText = Annotated[
    MappedAnswerWithText | MappingErrorWithText, Field(discriminator="type")
]


class AnswerRequest(Schema):
    answers: list[Answer]


class TransformResponseForVlopse(Schema):
    name: str
    answers: list[MappingResultWithText]


class TransformResponse(Schema):
    by_vlopse: list[TransformResponseForVlopse]


class ValidationResponse(Schema):
    errors: dict[str, list[ErrorDetails] | str]
    ok: bool
    kind: Literal["validation", "transformation"]


@form_router.post("/validate", auth=None)
def validate_answers(
    request: HttpRequest,
    data: AnswerRequest,
    vlopse: list[str] = Query(...),  # noqa: B008
) -> ValidationResponse:
    answers_inner = data.answers
    result = form_service.validate_unified_question(answers_inner, vlopse)
    kind = "validation"
    ok = len(result) == 0
    if ok:
        ok, result = form_service.map_unified_to_vlopse_and_validate(
            answers_inner, vlopse
        )
        kind = "transformation"
    return ValidationResponse(errors=result, ok=ok, kind=kind)


@form_router.post("/transform", auth=None)
def transform_answers(
    request: HttpRequest,
    data: AnswerRequest,
    vlopse: list[str] = Query(...),  # noqa: B008
) -> TransformResponse:
    answers_inner = data.answers
    result = form_service.transform_answers_to_vlopse_answers(vlopse, answers_inner)
    res = [TransformResponseForVlopse(name=name, answers=res) for name, res in result]

    return TransformResponse(by_vlopse=res)


@form_router.get("/condition", auth=None)
def get_conditions(
    request: HttpRequest,
    vlopse: list[str] = Query(...),  # noqa: B008
) -> Mapping[str, list[Condition]]:
    return condition_service.get_merged_conditions(vlopse)
