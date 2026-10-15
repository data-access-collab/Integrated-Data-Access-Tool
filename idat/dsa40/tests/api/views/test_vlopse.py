from __future__ import annotations

import json
import uuid
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from idat.dsa40.tests.api.test_views import api_prefix
from idat.dsa40.tests.factories import VlopseFactory

if TYPE_CHECKING:
    from django.test import Client

    from idat.dsa40.models import Vlopse


@pytest.fixture
def vlopse():
    return VlopseFactory.create()


def _info(name: str) -> dict:
    return {
        "name": name,
        "account_required": False,
        "application_link": "https://example.invalid/apply",
        "modality": "form",
    }


@pytest.fixture
def unique_id():
    return uuid.uuid4()


@pytest.mark.django_db
def test_list_vlopse(client: Client, vlopse: Vlopse):

    response = client.get(f"{api_prefix}/vlopse")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == [
        {
            "id": vlopse.name,
            "info": {
                "platform_information": vlopse.platform_information,
                "account_required": vlopse.account_required,
                "application_link": vlopse.application_link,
                "modality": vlopse.modality,
            },
        },
    ]


@pytest.mark.django_db
def test_get_vlopse_by_name(client: Client, unique_id: str):
    name = f"vlopse-{unique_id}"
    vlopse = VlopseFactory.create(name=name)
    response = client.get(f"{api_prefix}/vlopse/{name}")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": vlopse.name,
            "info": {
                "platform_information": vlopse.platform_information,
                "account_required": vlopse.account_required,
                "application_link": vlopse.application_link,
                "modality": vlopse.modality,
            },
        },
    ]


@pytest.mark.django_db
def test_create_vlopse(client: Client, unique_id: str):
    name = f"vlopse-{unique_id}"
    data = json.dumps({"id": name, "info": _info(name)})
    response = client.post(
        f"{api_prefix}/vlopse", data=data, content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}


@pytest.mark.django_db
def test_delete_vlopse(client: Client, unique_id: str):
    name = f"vlopse-{unique_id}"
    VlopseFactory.create(name=name)

    response = client.delete(f"{api_prefix}/vlopse/{name}")
    assert response.status_code == 200

    response = client.get(f"{api_prefix}/vlopse")
    assert not any(v["id"] == name for v in response.json())


@pytest.mark.django_db
def test_create_and_delete_vlopse(client: Client, unique_id: str):
    name = f"vlopse-{unique_id}"
    data = json.dumps({"id": name, "info": _info(name)})
    response = client.post(
        f"{api_prefix}/vlopse",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}

    response = client.get(f"{api_prefix}/vlopse")
    assert any(v["id"] == name for v in response.json())

    response = client.delete(f"{api_prefix}/vlopse/{name}")
    assert response.status_code == 200

    response = client.get(f"{api_prefix}/vlopse")
    assert not any(v["id"] == name for v in response.json())


@pytest.mark.django_db
def test_create_vlopse_malformed_body(client: Client):
    data = json.dumps({"not": "valid"})
    response = client.post(
        f"{api_prefix}/vlopse",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 422


@pytest.mark.skip(reason="Not yet implemented")
@pytest.mark.django_db
def test_create_duplicate_vlopse_conflicts(client: Client, vlopse: Vlopse):
    name = vlopse.name
    data = json.dumps({"id": name, "info": _info(name)})
    response = client.post(
        f"{api_prefix}/vlopse",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_rename_vlopse(client: Client, vlopse: Vlopse):
    vlopse = vlopse.name
    new_name = f"{vlopse}-renamed"
    data = json.dumps({"new_name": new_name})
    response = client.put(
        f"{api_prefix}/vlopse/{vlopse}",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 200
    client.delete(f"{api_prefix}/vlopse/{new_name}")


@pytest.mark.django_db
def test_rename_nonexistent_vlopse(client: Client, unique_id: str):
    data = json.dumps({"new_name": "irrelevant"})
    response = client.put(
        f"{api_prefix}/vlopse/does-not-exist-{unique_id}",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_rename_to_existing_name_conflicts(client: Client, vlopse: Vlopse):
    name = vlopse.name
    other = VlopseFactory.create()

    data = json.dumps({"new_name": other.name})
    response = client.put(
        f"{api_prefix}/vlopse/{name}",
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_rename_missing_body(client: Client, vlopse: Vlopse):

    response = client.put(f"{api_prefix}/vlopse/{vlopse.name}")
    assert response.status_code == 422


@pytest.mark.django_db
def test_delete_nonexistent_vlopse(client: Client, unique_id: str):
    response = client.delete(f"{api_prefix}/vlopse/does-not-exist-{unique_id}")
    assert response.status_code == 404


@pytest.mark.django_db
def test_get_missing_vlopse(client: Client):
    response = client.get(f"{api_prefix}/vlopse/does-not-exist")
    assert response.status_code == 404
