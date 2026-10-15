from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import connection
from django.db.utils import Error as DjangoDatabaseError
from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from idat.dsa40.api.schema import (
    ActionOut,
    CreateVlopseSchema,
    HealthOut,
    Status,
    UpdateVlopseSchema,
    VlopseOut,
)
from idat.dsa40.models import Vlopse

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
