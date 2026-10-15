from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import connection
from django.db.utils import Error as DjangoDatabaseError
from ninja import Router

from idat.dsa40.api.schema import HealthOut, Status

if TYPE_CHECKING:
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
