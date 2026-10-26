from __future__ import annotations

from typing import TYPE_CHECKING

from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from idat.dsa40.api.schema import (
    ActionOut,
)
from idat.vlopse.api.schema import CreateVlopseSchema, UpdateVlopseSchema, VlopseOut
from idat.vlopse.models import Vlopse

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


router = Router(tags=["vlopse"])


@router.get("", response=list[VlopseOut], auth=None)
def list_vlopses(request: HttpRequest) -> QuerySet[Vlopse]:
    """List available VLOPSEs"""
    return Vlopse.objects.all()


@router.get("/{name}", response=VlopseOut, auth=None)
def retrieve_vlopse(request: HttpRequest, name: str) -> Vlopse:
    """Get specific VLOPSE by its name"""
    return get_object_or_404(Vlopse, name=name)


@router.post("", response={200: ActionOut}, auth=None)
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


@router.put("/{name}", response={200: ActionOut}, auth=None)
def update_vlopse(
    request: HttpRequest, name: str, data: UpdateVlopseSchema
) -> tuple[int, dict[str, bool]]:
    vlopse = get_object_or_404(Vlopse, name=name)
    vlopse.name = data.new_name
    vlopse.save()
    return 200, {"success": True}


@router.delete(
    "/{name}",
    response={200: ActionOut} | {202: ActionOut},
    auth=None,
)
def delete_vlopse(request: HttpRequest, name: str) -> tuple[int, dict[str, bool]]:
    vlopse = get_object_or_404(Vlopse, name=name)
    vlopse.delete()
    return 200, {"success": True}
