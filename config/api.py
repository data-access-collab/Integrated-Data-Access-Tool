from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.db.utils import Error as DjangoDatabaseError
from ninja import NinjaAPI, Router, Schema
from ninja.security import SessionAuth

from idat.dsa40_form_handler.models import DSAQuestion
from idat.dsa40_form_handler.services.questions import QuestionService
from idat.dsa40_form_handler.validation.mapping import (
    MappingValidationError,
    QuestionMapper,
)
from idat.vlopse.models import Vlopse

if TYPE_CHECKING:
    from django.http import HttpRequest


class Status(StrEnum):
    OK = "ok"
    ERROR = "error"


class HealthOut(Schema):
    api: Status
    db: Status
    dsa_status: int | Status
    mapping_status: int | Status


api = NinjaAPI(
    title="DSA40 Application Helper",
    version="1.0.0",
    urls_namespace="api",
    auth=SessionAuth(),
    docs_decorator=staff_member_required,
)

health_router = Router(tags=["health"])


@health_router.get("", response=HealthOut, auth=None)
def retrieve_health(request: HttpRequest) -> HealthOut:
    """Report API liveness and DB connectivity."""
    db_status = Status.OK
    mapping_status = Status.ERROR
    dsa_status = DSAQuestion.objects.count()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_status = Status.OK
    except DjangoDatabaseError:
        db_status = Status.ERROR
    try:
        vlopses = Vlopse.objects.values_list("name", flat=True)
        mapper = QuestionMapper.from_vlopse_names(vlopses, QuestionService())
        _ = mapper._validate()  # noqa: SLF001
        mapping_status = Status.OK
    except MappingValidationError:
        db_status = Status.ERROR

    return HealthOut(
        api=Status.OK,
        db=db_status,
        dsa_status=dsa_status,
        mapping_status=mapping_status,
    )


api.add_router("/users/", "idat.users.api.views.router")
api.add_router("/v1/health", health_router)
api.add_router("/v1/vlopse", "idat.vlopse.api.views.router")
api.add_router(
    "/v1/vlopse/{vlopse_name}/question",
    "idat.dsa40_form_handler.api.views.vlopse_question_router",
)
api.add_router("/v1/question", "idat.dsa40_form_handler.api.views.dsa_question_router")
api.add_router("/v1/", "idat.dsa40_form_handler.api.views.form_router")
