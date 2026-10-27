from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from django.test import TestCase

from idat.conftest import api_prefix
from idat.dsa40.loaders import load_questions
from idat.dsa40_form_handler.api.views import AnswerRequest
from idat.dsa40_form_handler.lib.models import Answer
from idat.dsa40_form_handler.models import VLOPSEQuestion
from idat.dsa40_form_handler.tests.factories import VlopseQuestionFactory
from idat.vlopse.models import Vlopse
from idat.vlopse.tests.factories import VlopseFactory

if TYPE_CHECKING:
    from django.test import Client

    from idat.dsa40_form_handler.models import VLOPSEQuestion

VALID_ANSWERS = [
    {"question_id": "first-name", "value": "Joseph"},
    {"question_id": "last-name", "value": "Weizenbaum"},
    {"question_id": "email-inst", "value": "joseph@example.invalid"},
    {"question_id": "org-addr-country", "value": "Germany"},
    {"question_id": "data-acc-start", "value": "01-07-1999"},
    {"question_id": "data-acc-end", "value": "01-07-2000"},
    {"question_id": "cv", "value": "cv.pdf"},
    {"question_id": "prev-experience", "value": "No"},
]


@pytest.fixture
def vlopse() -> Vlopse:
    return VlopseFactory.create()


@pytest.fixture
def vlopse_question(vlopse: Vlopse) -> VLOPSEQuestion:
    return VlopseQuestionFactory.create(vlopse=vlopse)


@pytest.fixture
def mastodon() -> Vlopse:
    mastodon = Vlopse(name="mastodon")
    mastodon.save()
    return mastodon


class FormTests(TestCase):
    @classmethod
    def setUpTestData(cls):

        loadedqs = load_questions()
        assert loadedqs > 4
        mastodon = Vlopse(name="mastodon")
        mastodon.save()

    @pytest.mark.django_db
    def test_applicable_questions_for_known_vlopse(self):
        response = self.client.get(
            f"{api_prefix}/questions", query_params={"vlopse": [mastodon.name]}
        )
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        ids = {q["key"] for q in body}
        assert {"first-name", "last-name", "email-inst"}.issubset(ids)

    @pytest.mark.django_db
    @pytest.mark.skip(reason="Not implemented yet")
    def test_applicable_questions_for_multiple_vlopses(self, client: Client):
        pass

    @pytest.mark.django_db
    def test_applicable_questions_requires_vlopse(self):
        response = self.client.get(f"{api_prefix}/questions")
        assert response.status_code == 422

    @pytest.mark.django_db
    def test_applicable_questions_unknown_vlopse_returns_322(self):
        response = self.client.get(
            f"{api_prefix}/questions",
            query_params={"vlopse": ["does-not-exist"]},
        )
        assert response.status_code == 322
        assert "does-not-exist" in response.text
        assert "mastodon" not in response.text

    @pytest.mark.django_db
    def test_validate_valid_answers(self):
        data = {"answers": VALID_ANSWERS}
        response = self.client.post(
            f"{api_prefix}/validate",
            query_params={"vlopse": "mastodon"},
            data=json.dumps(data),
            content_type="application/json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["errors"] == {}

    @pytest.mark.django_db
    def test_validate_missing_required_answer(self):
        data = {
            "answers": [a for a in VALID_ANSWERS if a["question_id"] != "first-name"]
        }
        response = self.client.post(
            f"{api_prefix}/validate",
            query_params={"vlopse": "mastodon"},
            data=json.dumps(data),
            content_type="application/json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["kind"] == "transformation"
        assert "X1" in body["errors"]

    @pytest.mark.django_db
    def test_validate_requires_body_and_vlopse(self):
        response = self.client.post(f"{api_prefix}/validate")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_transform_valid_answers(self):
        data = {"answers": VALID_ANSWERS}
        response = self.client.post(
            f"{api_prefix}/transform",
            query_params={"vlopse": "mastodon"},
            data=json.dumps(data),
            content_type="application/json",
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["by_vlopse"]) == 1
        vlopse_result = body["by_vlopse"][0]
        assert vlopse_result["name"] == "mastodon"

        by_question = {a["question_id"]: a for a in vlopse_result["answers"]}
        assert by_question["X1"]["type"] == "result"
        assert by_question["X1"]["value"] == "Joseph Weizenbaum"
        assert by_question["X3"]["type"] == "result"
        assert by_question["X3"]["value"] == "DEU"

    @pytest.mark.django_db
    def test_transform_requires_vlopse(self):
        response = self.client.post(f"{api_prefix}/transform")
        assert response.status_code == 400

    @pytest.mark.django_db
    def test_transform_w_vlopse_wo_questions_fails(self):
        response = self.client.post(
            f"{api_prefix}/transform",
            query_params={"vlopse": "mastodon"},
            content_type="application/json",
        )
        assert response.status_code == 422

    @pytest.mark.django_db
    def test_transform_invalid_operator_input_surfaces_as_mapping_error(self):
        answers = [
            a for a in VALID_ANSWERS if a["question_id"] != "org-addr-country"
        ] + [{"question_id": "org-addr-country", "value": "Not A Real Country"}]
        response = self.client.post(
            f"{api_prefix}/transform",
            query_params={"vlopse": "mastodon"},
            data=json.dumps({"answers": answers}),
            content_type="application/json",
        )
        assert response.status_code == 200
        by_question = {
            a["question_id"]: a for a in response.json()["by_vlopse"][0]["answers"]
        }
        assert by_question["X3"]["type"] == "error"

    @pytest.mark.django_db
    def test_conditions_for_known_vlopse(self):
        response = self.client.get(
            f"{api_prefix}/condition", query_params={"vlopse": "mastodon"}
        )
        assert response.status_code == 200
        body = response.json()
        assert "data-acc-end" in body
        assert body["data-acc-end"][0]["question_id"] == "data-acc-start"

    @pytest.mark.django_db
    def test_conditions_requires_vlopse(self):
        response = self.client.get(f"{api_prefix}/condition")
        assert response.status_code == 422

    @pytest.mark.skip(reason="Not implemented yet")
    def test_transformation_id_not_in_all_targets(self):
        # FIXME: first-name will be in all probably, so find another one
        answers = AnswerRequest(
            answers=[Answer(question_id="first-name", value="Joseph")]
        )

        response = self.client.post(
            f"{api_prefix}/transform",
            query_params={"vlopse": ["tiktok", "meta"]},
            data=answers.model_dump(),
            content_type="application/json",
        )
        assert response.status_code == 200

    @pytest.mark.skip(reason="Not implemented yet")
    def test_transformation_invalid_id(self):
        # FIXME: first-name will be in all probably, so find another one
        answers = AnswerRequest(
            answers=[Answer(question_id="doesntexist", value="Joseph")]
        )

        response = self.client.post(
            f"{api_prefix}/transform",
            query_params={"vlopse": ["tiktok", "meta"]},
            data=answers.model_dump(),
            content_type="application/json",
        )
        assert response.status_code == 322  # FIXME

    @pytest.mark.skip(reason="Not implemented yet")
    def test_transformation_invalid_vlopse(self):
        # FIXME: first-name will be in all probably, so find another one
        answers = AnswerRequest(
            answers=[Answer(question_id="first-name", value="Joseph")]
        )

        response = self.client.post(
            f"{api_prefix}/transform",
            query_params={"vlopse": ["im-invalid", "meta"]},
            data=answers.model_dump(),
            content_type="application/json",
        )
        assert response.status_code == 322  # FIXME

    @pytest.mark.skip(reason="endpoint requires full questionaire")
    def test_answer_transformation(self):
        answers = [
            {"question_id": "first-name", "value": "Joseph"},
            {"question_id": "last-name", "value": "Weizenbaum"},
            {"question_id": "commercial-purpose", "value": "no"},
        ]
        response = self.client.post(
            f"{api_prefix}/transform",
            query_params={"vlopse": ["im-invalid", "meta"]},
            data=json.dumps({"answers": answers}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        vlopse_answers = data["by_vlopse"][0]
        assert vlopse_answers["name"] == "tiktok"
        answers = vlopse_answers["answers"]
        assert answers[0]["question_id"] == "T1"
        assert answers[0]["value"] == "Joseph Weizenbaum"
