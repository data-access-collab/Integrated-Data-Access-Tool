from typing import TYPE_CHECKING

import pytest

from idat.dsa40.tests.api.test_views import api_prefix
from idat.dsa40.tests.factories import VlopseFactory

if TYPE_CHECKING:
    from django.test import Client

    from idat.dsa40.models import Vlopse


@pytest.fixture
def vlopse() -> Vlopse:
    return VlopseFactory.create()


@pytest.mark.django_db
def test_create_and_get_dsa_question(client: Client, unique_id: str):
    question_id = f"dsa-{unique_id}"
    response = client.post(
        f"{api_prefix}/question",
        json={
            "id": question_id,
            "text": "What is your name?",
            "input_type": "text",
            "help_text": "Full legal name",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}

    response = client.get(f"{api_prefix}/question/{question_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == question_id
    assert body["help_text"] == "Full legal name"


@pytest.mark.django_db
def test_get_nonexistent_dsa_question_returns_null(client: Client):
    response = client.get(f"{api_prefix}/question/does-not-exist")
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.django_db
def test_list_dsa_questions(client: Client, unique_id: str):
    question_id = f"dsa-{unique_id}"
    response = client.post(
        f"{api_prefix}/question",
        json={"id": question_id, "text": "Q", "input_type": "text", "help_text": None},
    )
    assert response.status_code == 200

    response = client.get(f"{api_prefix}/question")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(q["id"] == question_id for q in body)


@pytest.mark.django_db
def test_create_duplicate_dsa_question_conflicts(client: Client, unique_id: str):
    question_id = f"dsa-{unique_id}"
    body = {"id": question_id, "text": "Q", "input_type": "text", "help_text": None}
    response = client.post(f"{api_prefix}/question", json=body)
    assert response.status_code == 200

    response = client.post(f"{api_prefix}/question", json=body)
    assert response.status_code == 409


@pytest.mark.django_db
def test_create_dsa_question_malformed_body(client: Client):
    response = client.post(f"{api_prefix}/question", json={"id": "x"})
    assert response.status_code == 422
