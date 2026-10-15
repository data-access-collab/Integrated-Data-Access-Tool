import json
from typing import TYPE_CHECKING

import pytest

from idat.dsa40.tests.api.test_views import api_prefix
from idat.dsa40.tests.factories import VlopseFactory, VlopseQuestionFactory

if TYPE_CHECKING:
    from django.test import Client

    from idat.dsa40.models import Vlopse, VLOPSEQuestion


@pytest.fixture
def vlopse() -> Vlopse:
    return VlopseFactory.create()


@pytest.fixture
def vlopse_question(vlopse: Vlopse) -> VLOPSEQuestion:
    return VlopseQuestionFactory.create(vlopse=vlopse)


@pytest.mark.django_db
def test_list_vlopse_questions(client: Client, vlopse: Vlopse):
    question = VlopseQuestionFactory.create(vlopse=vlopse)
    response = client.get(
        f"{api_prefix}/vlopse/{vlopse.name}/question",
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": question.id,
            "text": question.text,
            "vlopse": question.vlopse.name,
            "required": question.required,
            "input_type": question.input_type,
            "details": question.details,
            "config": question.config,
        },
    ]


@pytest.mark.django_db
def test_get_single_vlopse_question(client: Client, vlopse_question: VLOPSEQuestion):

    response = client.get(
        f"{api_prefix}/vlopse/{vlopse_question.vlopse.name}/question/{vlopse_question.id}"
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": vlopse_question.id,
        "text": vlopse_question.text,
        "vlopse": vlopse_question.vlopse.name,
        "required": vlopse_question.required,
        "input_type": vlopse_question.input_type,
        "details": vlopse_question.details,
        "config": vlopse_question.config,
    }


@pytest.mark.django_db
def test_create_vlopse_question(client: Client, vlopse: Vlopse):
    body = {
        "id": "V1",
        "text": "Are you affiliated with an academic institution?",
        "required": True,
        "input_type": "selection",
        "config": {"type": "selection", "options": ["Yes", "No"]},
        "details": "",
    }
    response = client.post(
        f"{api_prefix}/vlopse/{vlopse.name}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}


@pytest.mark.django_db
def test_get_nonexistent_vlopse_question(client: Client, vlopse: Vlopse):
    response = client.get(f"{api_prefix}/vlopse/{vlopse.name}/question/does-not-exist")
    assert response.status_code == 404


@pytest.mark.skip(reason="Not implemented yet")
@pytest.mark.django_db
def test_create_duplicate_vlopse_question_conflicts(
    client: Client, vlopse_question: VLOPSEQuestion
):
    body = {
        "id": vlopse_question.id,
        "text": vlopse_question.text,
        "required": vlopse_question.required,
        "input_type": vlopse_question.input_type,
        "details": vlopse_question.details,
        "config": vlopse_question.config,
    }

    response = client.post(
        f"{api_prefix}/vlopse/{vlopse_question.vlopse.name}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_create_vlopse_question_malformed_body(client: Client, vlopse: Vlopse):
    body = {"id": "x"}
    response = client.post(
        f"{api_prefix}/vlopse/{vlopse}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 422
