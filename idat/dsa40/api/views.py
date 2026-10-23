from __future__ import annotations

from collections.abc import Mapping
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
from idat.dsa40.models import DSAQuestion, Vlopse, VLOPSEQuestion
from idat.dsa40.services.condition_service import ConditionService
from idat.dsa40.services.form_engine import FormService
from idat.dsa40.services.questions import QuestionService
from idat.dsa40.services.vlopse import VlopseConfigService

if TYPE_CHECKING:
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


@vlopse_router.get("/{name}", response=VlopseOut, auth=None)
def retrieve_vlopse(request: HttpRequest, name: str) -> Vlopse:
    """Get specific VLOPSE by its name"""
    return get_object_or_404(Vlopse, name=name)


@vlopse_router.post("", response={200: ActionOut}, auth=None)
def add_vlopse(
    request: HttpRequest, data: CreateVlopseSchema
) -> tuple[int, dict[str, bool]]:
    vlopse = Vlopse(**data.model_dump(exclude_unset=True))

    try:
        vlopse.full_clean()
    except ValidationError as e:
        raise HttpError(422, str(e.message_dict)) from e
    vlopse.save()
    return 200, {"success": True}


@vlopse_router.put("/{name}", response={200: ActionOut}, auth=None)
def update_vlopse(
    request: HttpRequest, name: str, data: UpdateVlopseSchema
) -> tuple[int, dict[str, bool]]:
    vlopse = get_object_or_404(Vlopse, name=name)
    vlopse.key = data.new_name
    vlopse.save()
    return 200, {"success": True}


@vlopse_router.delete(
    "/{name}",
    response={200: ActionOut} | {202: ActionOut},
    auth=None,
)
def delete_vlopse(request: HttpRequest, name: str) -> tuple[int, dict[str, bool]]:
    vlopse = get_object_or_404(Vlopse, name=name)
    vlopse.delete()
    return 200, {"success": True}


# QUESTIONS


@vlopse_router.get(
    "/{vlopse_name}/question", response=list[VlopseQuestionOut], auth=None
)
def list_vlopse_questions(
    request: HttpRequest, vlopse_name: str
) -> QuerySet[VLOPSEQuestion]:
    return VLOPSEQuestion.objects.filter(vlopse__name=vlopse_name).select_related(
        "vlopse"
    )


@vlopse_router.get(
    "/{vlopse_name}/question/{question_key}",
    response=VlopseQuestionOut,
    auth=None,
)
def get_vlopse_question(
    request: HttpRequest,
    vlopse_name: str,
    question_key: str,
) -> VLOPSEQuestion:
    return get_object_or_404(VLOPSEQuestion, vlopse__name=vlopse_name, key=question_key)


@vlopse_router.post("/{vlopse_name}/question", response=ActionOut, auth=None)
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
    return DSAQuestion.objects.all()


@dsa_question_router.get("/{key}", response=DSAQuestionOut, auth=None)
def get_dsa_question(request: HttpRequest, key: str) -> DSAQuestion:
    return get_object_or_404(DSAQuestion, key=key)


@dsa_question_router.post("", response=ActionOut, auth=None)
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
    response=list[DSAQuestionOut],
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


@form_router.post("/validate", response=ValidationResponse, auth=None)
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


@form_router.post("/transform", response=TransformResponse, auth=None)
def transform_answers(
    request: HttpRequest,
    data: AnswerRequest,
    vlopse: list[str] = Query(...),  # noqa: B008
) -> TransformResponse:
    answers_inner = data.answers
    result = form_service.transform_answers_to_vlopse_answers(vlopse, answers_inner)
    res = [TransformResponseForVlopse(name=name, answers=res) for name, res in result]

    return TransformResponse(by_vlopse=res)


@form_router.get("/condition", response=Mapping[str, list[Condition]], auth=None)
def get_conditions(
    request: HttpRequest,
    vlopse: list[str] = Query(...),  # noqa: B008
) -> Mapping[str, list[Condition]]:
    return condition_service.get_merged_conditions(vlopse)
