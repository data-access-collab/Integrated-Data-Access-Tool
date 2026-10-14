from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from django.test import Client

api_prefix = "/api/v1"


@pytest.mark.django_db
def test_retrieve_health(client: Client):

    response = client.get(f"{api_prefix}/health")

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["api"] == "ok"
    assert data["db"] in ("ok", "error")
    assert data["mapping_status"] in ("ok", "error")
    assert isinstance(data["dsa_status"], int) or data["dsa_status"] in ("ok", "error")
