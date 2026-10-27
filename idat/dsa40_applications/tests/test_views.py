from __future__ import annotations

from http import HTTPStatus
from unittest import mock

from django.core import signing
from django.test import TestCase
from django.urls import reverse

from idat.dsa40.lib.config import VLOPSEConfiguration
from idat.dsa40.models import InputType
from idat.dsa40.tests.factories import (
    DsaQuestionFactory,
    VlopseFactory,
    VlopseQuestionFactory,
)
from idat.dsa40_applications.state import (
    SALT,
    STATE_HEADER,
    WizardJSONSerializer,
    WizardState,
    dump_state,
)


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


def step_url(step: int) -> str:
    return reverse("dsa40_applications:wizard_step", args=[step])


def htmx_headers(state: WizardState | None = None) -> dict[str, str]:
    headers = {"HX-Request": "true"}
    if state is not None:
        headers[STATE_HEADER] = dump_state(state)
    return headers


def response_state(response) -> WizardState:
    return signing.loads(
        response[STATE_HEADER], salt=SALT, serializer=WizardJSONSerializer
    )


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
        self.assertContains(response, f'hx-get="{step_url(1)}"')

    def test_non_htmx_step_request_returns_shell_that_refetches_step_via_htmx(self):
        response = self.client.get(step_url(2))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f'hx-get="{step_url(2)}"')
        self.assertNotIn(STATE_HEADER, response)

    def test_unknown_step_returns_404(self):
        response = self.client.get(step_url(4), headers=htmx_headers())

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_tampered_state_header_returns_400(self):
        headers = {"HX-Request": "true", STATE_HEADER: "not-a-signed-token"}

        response = self.client.get(step_url(1), headers=headers)

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_vlopse_step_preselects_previously_chosen_vlopses(self):
        state = WizardState(vlopses=[self.mastodon.pk], answers={})

        response = self.client.get(step_url(1), headers=htmx_headers(state))

        self.assertEqual(
            response.context["form"]["vlopses"].value(), [self.mastodon.pk]
        )

    def test_vlopse_step_rejects_empty_selection(self):
        response = self.client.post(step_url(1), data={}, headers=htmx_headers())

        self.assertEqual(response["HX-Push-Url"], step_url(1))
        self.assertContains(response, "Please select at least one Vlopse")

    def test_vlopse_step_advances_to_questions_and_stores_selection(self):
        response = self.client.post(
            step_url(1), data={"vlopses": [self.mastodon.pk]}, headers=htmx_headers()
        )

        self.assertEqual(response["HX-Push-Url"], step_url(2))
        self.assertContains(response, "Project title")
        self.assertNotContains(response, "Role in organisation")
        self.assertEqual(response_state(response)["vlopses"], [self.mastodon.pk])

    def test_deselecting_vlopse_drops_answers_only_dropped_needed(self):
        state = WizardState(
            vlopses=[self.mastodon.pk, self.tiktok.pk],
            answers={"email": "a@example.org", "role": "Researcher"},
        )

        response = self.client.post(
            step_url(1),
            data={"vlopses": [self.mastodon.pk]},
            headers=htmx_headers(state),
        )

        self.assertEqual(
            response_state(response)["answers"], {"email": "a@example.org"}
        )

    def test_questions_step_without_vlopses_falls_back_to_selection(self):
        response = self.client.get(step_url(2), headers=htmx_headers())

        self.assertEqual(response["HX-Push-Url"], step_url(1))
        self.assertContains(response, "Select VLOPSEs")

    def test_questions_step_rejects_missing_required_answer(self):
        state = WizardState(vlopses=[self.mastodon.pk], answers={})

        response = self.client.post(
            step_url(2),
            data={"project-title": "Feed ranking audit"},
            headers=htmx_headers(state),
        )

        self.assertEqual(response["HX-Push-Url"], step_url(2))
        self.assertContains(response, "This field is required.")
        self.assertEqual(response_state(response)["answers"], {})

    def test_questions_step_advances_to_review_and_stores_answers(self):
        state = WizardState(vlopses=[self.mastodon.pk], answers={})

        response = self.client.post(
            step_url(2),
            data={"email": "a@example.org"},
            headers=htmx_headers(state),
        )

        self.assertEqual(response["HX-Push-Url"], step_url(3))
        self.assertContains(response, "a@example.org")
        self.assertEqual(response_state(response)["answers"]["email"], "a@example.org")

    def test_review_step_with_invalid_stored_answers_falls_back_to_questions(self):
        state = WizardState(
            vlopses=[self.mastodon.pk],
            answers={"project-title": "Feed ranking audit"},
        )

        response = self.client.get(step_url(3), headers=htmx_headers(state))

        self.assertEqual(response["HX-Push-Url"], step_url(2))
        self.assertContains(response, "Institutional e-mail")
