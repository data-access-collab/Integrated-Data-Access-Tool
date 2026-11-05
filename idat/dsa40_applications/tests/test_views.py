from __future__ import annotations

import json
from http import HTTPStatus
from unittest import mock

from django.test import RequestFactory, TestCase
from django.urls import reverse

from idat.dsa40.lib.config import VLOPSEConfiguration
from idat.dsa40.models import InputType
from idat.dsa40.tests.factories import DsaQuestionFactory, VlopseQuestionFactory
from idat.dsa40_applications.forms import VlopseSelectionForm
from idat.dsa40_applications.state import (
    FILE_KEY_HEADER,
    MAX_AGE,
    MAX_AGE_HEADER,
    STATE_HEADER,
    WIZARD_ID_HEADER,
    WizardState,
    dump_wizard_state,
    encode_file_encryption_key,
    load_wizard_state,
)
from idat.dsa40_applications.views import VlopseSelectionStep
from idat.vlopse.tests.factories import VlopseFactory


def platform_config(name: str, mappings: dict[str, str]) -> VLOPSEConfiguration:
    return VLOPSEConfiguration.model_validate(
        {
            "info": {
                "name": name,
                "account_required": False,
                "application_link": f"https://{name}.example.org/apply",
                "modality": "form",
            },
            "mappings": mappings,
            "conditions": {},
        }
    )


# Example mappings for the real Mastodon and TikTok VLOPSEs, defined here so the
# tests do not depend on dsa40/fixtures/vlopses. Both ask for an institutional
# e-mail; Mastodon also asks for an optional project title, TikTok for the
# applicant's role.
PLATFORM_CONFIGS = {
    "mastodon": platform_config(
        "mastodon", {"mastodon-email": "email", "mastodon-title": "project-title"}
    ),
    "tiktok": platform_config(
        "tiktok", {"tiktok-email": "email", "tiktok-role": "role"}
    ),
}


def get_step_url(step: int) -> str:
    return reverse("dsa40_applications:wizard_step", args=[step])


def get_htmx_headers(state: WizardState | None = None) -> dict[str, str]:
    headers = {"HX-Request": "true"}
    if state is not None:
        headers[STATE_HEADER] = dump_wizard_state(state)
    return headers


def create_state(vlopses: list[int], answers: dict | None = None) -> WizardState:
    return WizardState(wizard_id="draft-1", vlopses=vlopses, answers=answers or {})


def response_state(response) -> WizardState:
    request = RequestFactory().get("/", headers={STATE_HEADER: response[STATE_HEADER]})
    return load_wizard_state(request)


# mocked to use the stable test configs defined above
@mock.patch(
    "idat.dsa40.lib.mapping.get_vlopse_configuration_for",
    new=PLATFORM_CONFIGS.__getitem__,
)
class WizardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mastodon = VlopseFactory.create(name="mastodon")
        cls.tiktok = VlopseFactory.create(name="tiktok")
        for key, text in [
            ("email", "Institutional e-mail"),
            ("project-title", "Project title"),
            ("role", "Role in organisation"),
        ]:
            DsaQuestionFactory.create(
                key=key, text=text, input_type=InputType.TEXT, config=None
            )
        for key, vlopse, required in [
            ("mastodon-email", cls.mastodon, True),
            ("mastodon-title", cls.mastodon, False),
            ("tiktok-email", cls.tiktok, True),
            ("tiktok-role", cls.tiktok, True),
        ]:
            VlopseQuestionFactory.create(
                key=key, vlopse=vlopse, required=required, input_type=InputType.TEXT
            )

    def test_create_page_loads_first_step(self):
        response = self.client.get(reverse("dsa40_applications:create"))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f'hx-get="{get_step_url(1)}"')

    def test_non_htmx_step_request_returns_shell_that_refetches_step_via_htmx(self):
        response = self.client.get(get_step_url(2))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f'hx-get="{get_step_url(2)}"')
        self.assertNotIn(STATE_HEADER, response)

    def test_unknown_step_returns_404(self):
        response = self.client.get(get_step_url(4), headers=get_htmx_headers())

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_tampered_state_header_returns_400(self):
        headers = {"HX-Request": "true", STATE_HEADER: "not-an-encrypted-token"}

        response = self.client.get(get_step_url(1), headers=headers)

        # The 400 is returned by Django's internal request handler
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_vlopse_step_preselects_previously_chosen_vlopses(self):
        state = create_state([self.mastodon.pk], {})

        response = self.client.get(get_step_url(1), headers=get_htmx_headers(state))

        self.assertEqual(
            response.context["form"]["vlopses"].value(), [self.mastodon.pk]
        )

    def test_vlopse_step_rejects_empty_selection(self):
        response = self.client.post(
            get_step_url(1), data={}, headers=get_htmx_headers()
        )

        self.assertEqual(response["HX-Push-Url"], get_step_url(1))
        self.assertTrue(response.context["form"].has_error("vlopses", code="required"))
        message = VlopseSelectionForm.base_fields["vlopses"].error_messages["required"]
        self.assertContains(response, message)

    def test_vlopse_step_advances_to_questions_and_stores_selection(self):
        response = self.client.post(
            get_step_url(1),
            data={"vlopses": [self.mastodon.pk]},
            headers=get_htmx_headers(),
        )

        self.assertEqual(response["HX-Push-Url"], get_step_url(2))
        self.assertContains(response, "Project title")
        self.assertNotContains(response, "Role in organisation")
        self.assertEqual(response_state(response)["vlopses"], [self.mastodon.pk])

    def test_deselecting_vlopse_drops_answers_that_only_dropped_needed(self):
        state = create_state(
            [self.mastodon.pk, self.tiktok.pk],
            {"email": "a@example.org", "role": "Researcher"},
        )

        response = self.client.post(
            get_step_url(1),
            data={"vlopses": [self.mastodon.pk]},
            headers=get_htmx_headers(state),
        )

        self.assertEqual(
            response_state(response)["answers"], {"email": "a@example.org"}
        )

    def test_questions_step_without_vlopses_falls_back_to_selection(self):
        response = self.client.get(get_step_url(2), headers=get_htmx_headers())

        self.assertEqual(response["HX-Push-Url"], get_step_url(1))
        self.assertTemplateUsed(response, VlopseSelectionStep.template_name)

    def test_questions_step_rejects_missing_required_answer(self):
        state = create_state([self.mastodon.pk], {})

        response = self.client.post(
            get_step_url(2),
            data={"project-title": "Feed ranking audit"},
            headers=get_htmx_headers(state),
        )

        self.assertEqual(response["HX-Push-Url"], get_step_url(2))
        self.assertContains(response, "This field is required.")
        self.assertEqual(response_state(response)["answers"], {})

    def test_questions_step_advances_to_review_and_stores_answers(self):
        state = create_state([self.mastodon.pk], {})

        response = self.client.post(
            get_step_url(2),
            data={"email": "a@example.org"},
            headers=get_htmx_headers(state),
        )

        self.assertEqual(response["HX-Push-Url"], get_step_url(3))
        self.assertContains(response, "a@example.org")
        self.assertEqual(response_state(response)["answers"]["email"], "a@example.org")

    def test_review_step_with_invalid_stored_answers_falls_back_to_questions(self):
        state = create_state(
            [self.mastodon.pk], {"project-title": "Feed ranking audit"}
        )

        response = self.client.get(get_step_url(3), headers=get_htmx_headers(state))

        self.assertEqual(response["HX-Push-Url"], get_step_url(2))
        self.assertContains(response, "Institutional e-mail")

    def test_step_response_carries_wizard_id_file_key_and_max_age(self):
        response = self.client.get(
            get_step_url(1), headers=get_htmx_headers(create_state([]))
        )

        self.assertEqual(response[WIZARD_ID_HEADER], "draft-1")
        self.assertEqual(
            response[FILE_KEY_HEADER], encode_file_encryption_key("draft-1")
        )
        self.assertEqual(response[MAX_AGE_HEADER], str(MAX_AGE))

    def test_file_answer_is_stored_as_metadata_and_shown_in_review(self):
        DsaQuestionFactory.create(
            key="cv", text="Curriculum Vitae", input_type=InputType.FILE_UPLOAD
        )
        VlopseQuestionFactory.create(
            key="mastodon-cv",
            vlopse=self.mastodon,
            required=True,
            input_type=InputType.FILE_UPLOAD,
        )
        meta = {
            "name": "cv.pdf",
            "size": 2048,
            "type": "application/pdf",
            "sha256": "b" * 64,
        }
        configs = {
            "mastodon": platform_config(
                "mastodon", {"mastodon-email": "email", "mastodon-cv": "cv"}
            )
        }

        # override mock to include the file field in the configs
        with mock.patch(
            "idat.dsa40.lib.mapping.get_vlopse_configuration_for",
            new=configs.__getitem__,
        ):
            response = self.client.post(
                get_step_url(2),
                data={"email": "a@example.org", "cv": json.dumps(meta)},
                headers=get_htmx_headers(create_state([self.mastodon.pk])),
            )

        self.assertEqual(response["HX-Push-Url"], get_step_url(3))
        self.assertContains(response, "cv.pdf (2.0\xa0KB)")
        self.assertEqual(response_state(response)["answers"]["cv"], meta)
