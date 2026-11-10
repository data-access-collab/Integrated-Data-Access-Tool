from __future__ import annotations

import json
import time
from http import HTTPStatus
from unittest import mock

from django.test import RequestFactory, TestCase
from django.urls import reverse

from idat.dsa40_form_handler.models import DSAQuestion, InputType, VLOPSEQuestion
from idat.dsa40_form_handler.tests.factories import (
    DsaQuestionFactory,
    VlopseQuestionFactory,
)
from idat.dsa40_form_handler.validation.config import VLOPSEConfiguration
from idat.dsa40_wizard.forms import VlopseSelectionForm
from idat.dsa40_wizard.state import (
    DRAFT_UNAVAILABLE_HEADER,
    FILE_KEY_HEADER,
    MAX_STATE_AGE,
    MAX_STATE_AGE_HEADER,
    STATE_POST_FIELD,
    STATE_REQUEST_HEADER,
    WIZARD_ID_HEADER,
    WizardState,
    dump_wizard_state,
    encode_file_encryption_key,
    load_wizard_state,
)
from idat.dsa40_wizard.views import (
    ReviewStep,
    VlopseSelectionStep,
)
from idat.vlopse.models import Vlopse
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
# applicant's role. Keyed by config file name: the mock replaces reading the file,
# so looking the file up by the VLOPSE's name still runs.
PLATFORM_CONFIGS = {
    "mastodon.json": platform_config(
        "mastodon", {"mastodon-email": "email", "mastodon-title": "project-title"}
    ),
    "tiktok.json": platform_config(
        "tiktok", {"tiktok-email": "email", "tiktok-role": "role"}
    ),
}

CONFIG_FILE_READER = "idat.dsa40_form_handler.validation.config._load_json"


def config_reader(configs: dict[str, VLOPSEConfiguration]):
    """Stand-in for reading config files: `configs` by file name, no other file
    exists."""

    def read(filename: str) -> VLOPSEConfiguration:
        try:
            return configs[filename]
        except KeyError as err:
            raise FileNotFoundError(filename) from err

    return read


def get_step_url(step: str) -> str:
    return reverse("dsa40_wizard:wizard_step", args=[step])


def get_submit_url(step: str) -> str:
    return reverse("dsa40_wizard:wizard_submit", args=[step])


HTMX_HEADERS = {"HX-Request": "true"}


def step_data(state: WizardState | None = None, data: dict | None = None) -> dict:
    """POST data of a wizard request: the form data plus the state token."""
    data = dict(data or {})
    if state is not None:
        data[STATE_POST_FIELD] = dump_wizard_state(state)
    return data


def create_state(vlopses: list[int], answers: dict | None = None) -> WizardState:
    return WizardState(wizard_id="draft-1", vlopses=vlopses, answers=answers or {})


def response_state(response) -> WizardState:
    request = RequestFactory().post(
        "/", {STATE_POST_FIELD: response[STATE_REQUEST_HEADER]}
    )
    return load_wizard_state(request)


# mocked to use the stable test configs defined above
@mock.patch(CONFIG_FILE_READER, new=config_reader(PLATFORM_CONFIGS))
class WizardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # replace the questions and vlopses seeded by the data migrations
        VLOPSEQuestion.objects.all().delete()
        DSAQuestion.objects.all().delete()
        Vlopse.objects.all().delete()
        # named like the seeded VLOPSEs, unlike their config files
        cls.mastodon = VlopseFactory.create(name="Mastodon")
        cls.tiktok = VlopseFactory.create(name="TikTok")
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
        response = self.client.get(reverse("dsa40_wizard:create"))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f'hx-post="{get_step_url("choose-vlopses")}"')

    def test_non_htmx_step_request_returns_shell_that_refetches_step_via_htmx(self):
        response = self.client.get(get_step_url("enter-details"))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f'hx-post="{get_step_url("enter-details")}"')
        self.assertNotIn(STATE_REQUEST_HEADER, response)

    def test_shell_sidebar_shows_the_requested_step_as_current(self):
        response = self.client.get(get_step_url("enter-details"))

        self.assertEqual(response.context["current_step"], "enter-details")
        self.assertNotContains(response, 'hx-swap-oob="true"')

    def test_step_response_sends_sidebar_out_of_band(self):
        state = create_state([self.mastodon.pk], {})

        response = self.client.post(
            get_step_url("enter-details"),
            data=step_data(state),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response.context["current_step"], "enter-details")
        self.assertContains(response, '<div id="wizard-sidebar" hx-swap-oob="true">')
        # one sidebar item and one form section per question category
        self.assertContains(response, 'href="#section-general"', count=1)
        self.assertContains(response, 'id="section-general"', count=1)

    def test_history_restore_request_returns_shell_not_step_partial(self):
        headers = {**HTMX_HEADERS, "HX-History-Restore-Request": "true"}

        response = self.client.get(get_step_url("choose-vlopses"), headers=headers)

        self.assertContains(response, f'hx-post="{get_step_url("choose-vlopses")}"')
        self.assertNotIn(STATE_REQUEST_HEADER, response)

    def test_step_response_varies_on_hx_request(self):
        response = self.client.post(
            get_step_url("choose-vlopses"),
            data=step_data(),
            headers=HTMX_HEADERS,
        )

        self.assertIn("HX-Request", response["Vary"])

    def test_loading_a_step_replaces_the_url_instead_of_pushing(self):
        response = self.client.post(
            get_step_url("choose-vlopses"),
            data=step_data(),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Replace-Url"], get_step_url("choose-vlopses"))
        self.assertNotIn("HX-Push-Url", response)

    def test_unknown_step_returns_404(self):
        response = self.client.post(
            get_step_url("no-such-step"),
            data=step_data(),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def ensure_draft_is_unavailable(self, response):
        # no content to swap: wizard.js discards the draft and goes to the page
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(
            response[DRAFT_UNAVAILABLE_HEADER],
            reverse("dsa40_wizard:draft_unavailable"),
        )
        self.assertEqual(response[MAX_STATE_AGE_HEADER], str(MAX_STATE_AGE))
        self.assertNotIn(STATE_REQUEST_HEADER, response)

    def test_tampered_state_token_makes_draft_unavailable(self):
        response = self.client.post(
            get_step_url("review"),
            data={STATE_POST_FIELD: "not-an-encrypted-token"},
            headers=HTMX_HEADERS,
        )

        self.ensure_draft_is_unavailable(response)

    def test_expired_state_token_makes_draft_unavailable(self):
        issued_at = time.time() - MAX_STATE_AGE - 60
        with mock.patch("cryptography.fernet.time.time", return_value=issued_at):
            data = step_data(create_state([self.mastodon.pk]))

        response = self.client.post(
            get_step_url("enter-details"), data=data, headers=HTMX_HEADERS
        )

        self.ensure_draft_is_unavailable(response)

    def test_later_step_without_token_makes_draft_unavailable(self):
        # e.g. a step URL opened in another tab: its draft lives in the first tab
        response = self.client.post(
            get_step_url("review"), data=step_data(), headers=HTMX_HEADERS
        )

        self.ensure_draft_is_unavailable(response)

    def test_first_step_without_token_starts_a_new_draft(self):
        response = self.client.post(
            get_step_url("choose-vlopses"), data=step_data(), headers=HTMX_HEADERS
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response_state(response)["vlopses"], [])

    def test_draft_unavailable_page_names_the_token_ttl(self):
        response = self.client.get(reverse("dsa40_wizard:draft_unavailable"))

        self.assertContains(response, "This draft is no longer available")
        hours = MAX_STATE_AGE // 3600
        self.assertContains(response, f"inactive for more than {hours} hours")

    def test_vlopse_step_preselects_previously_chosen_vlopses(self):
        state = create_state([self.mastodon.pk], {})

        response = self.client.post(
            get_step_url("choose-vlopses"),
            data=step_data(state),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(
            response.context["form"]["vlopses"].value(), [self.mastodon.pk]
        )

    def test_vlopse_step_rejects_empty_selection(self):
        response = self.client.post(
            get_submit_url("choose-vlopses"),
            data=step_data(None, {}),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Replace-Url"], get_step_url("choose-vlopses"))
        self.assertTrue(response.context["form"].has_error("vlopses", code="required"))
        message = VlopseSelectionForm.base_fields["vlopses"].error_messages["required"]
        self.assertContains(response, message)

    def test_vlopse_step_advances_to_questions_and_stores_selection(self):
        response = self.client.post(
            get_submit_url("choose-vlopses"),
            data=step_data(None, {"vlopses": [self.mastodon.pk]}),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Push-Url"], get_step_url("enter-details"))
        self.assertContains(response, "Project title")
        self.assertNotContains(response, "Role in organisation")
        self.assertEqual(response_state(response)["vlopses"], [self.mastodon.pk])

    def test_deselecting_vlopse_drops_answers_that_only_dropped_needed(self):
        state = create_state(
            [self.mastodon.pk, self.tiktok.pk],
            {"email": "a@example.org", "role": "Researcher"},
        )

        response = self.client.post(
            get_submit_url("choose-vlopses"),
            data=step_data(state, {"vlopses": [self.mastodon.pk]}),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(
            response_state(response)["answers"], {"email": "a@example.org"}
        )

    def test_questions_step_without_vlopses_falls_back_to_selection(self):
        response = self.client.post(
            get_step_url("enter-details"),
            data=step_data(create_state([])),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Replace-Url"], get_step_url("choose-vlopses"))
        self.assertTemplateUsed(response, VlopseSelectionStep.template_name)

    def test_vlopse_step_rejects_vlopse_without_question_mapping(self):
        unmapped = VlopseFactory.create(name="Bluesky")

        response = self.client.post(
            get_submit_url("choose-vlopses"),
            data=step_data(None, {"vlopses": [self.mastodon.pk, unmapped.pk]}),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Replace-Url"], get_step_url("choose-vlopses"))
        self.assertTrue(
            response.context["form"].has_error("vlopses", code="unavailable")
        )
        self.assertContains(response, "Applications for Bluesky")
        self.assertEqual(response_state(response)["vlopses"], [])

    def test_deleted_vlopses_are_dropped_from_the_selection(self):
        deleted = VlopseFactory.create(name="Bluesky")
        deleted_pk = deleted.pk
        deleted.delete()

        response = self.client.post(
            get_step_url("enter-details"),
            data=step_data(create_state([deleted_pk, self.mastodon.pk])),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Replace-Url"], get_step_url("enter-details"))
        self.assertEqual(response_state(response)["vlopses"], [self.mastodon.pk])

    def test_later_step_with_only_deleted_vlopses_falls_back_to_selection(self):
        deleted = VlopseFactory.create(name="Bluesky")
        deleted_pk = deleted.pk
        deleted.delete()

        response = self.client.post(
            get_step_url("enter-details"),
            data=step_data(create_state([deleted_pk])),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Replace-Url"], get_step_url("choose-vlopses"))
        self.assertEqual(response_state(response)["vlopses"], [])

    def test_later_step_with_unavailable_vlopse_falls_back_to_selection(self):
        unmapped = VlopseFactory.create(name="Bluesky")
        state = create_state(
            [self.mastodon.pk, unmapped.pk], {"email": "a@example.org"}
        )

        for step in ("enter-details", "review", "generate"):
            with self.subTest(step=step):
                response = self.client.post(
                    get_step_url(step), data=step_data(state), headers=HTMX_HEADERS
                )

                self.assertEqual(
                    response["HX-Replace-Url"], get_step_url("choose-vlopses")
                )
                self.assertContains(response, "Applications for Bluesky")
                self.assertEqual(
                    response.context["form"]["vlopses"].value(),
                    [self.mastodon.pk, unmapped.pk],
                )

    def test_questions_step_rejects_missing_required_answer(self):
        state = create_state([self.mastodon.pk], {})

        response = self.client.post(
            get_submit_url("enter-details"),
            data=step_data(state, {"project-title": "Feed ranking audit"}),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Replace-Url"], get_step_url("enter-details"))
        self.assertContains(response, "This field is required.")
        self.assertEqual(response_state(response)["answers"], {})

    def test_questions_step_advances_to_review_and_stores_answers(self):
        state = create_state([self.mastodon.pk], {})

        response = self.client.post(
            get_submit_url("enter-details"),
            data=step_data(state, {"email": "a@example.org"}),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Push-Url"], get_step_url("review"))
        self.assertContains(response, "a@example.org")
        self.assertEqual(response_state(response)["answers"]["email"], "a@example.org")

    def test_review_advances_to_generate(self):
        # every question is stored, unanswered ones empty (QuestionsStep.update_state)
        answers = {"email": "a@example.org", "project-title": ""}
        state = create_state([self.mastodon.pk], answers)

        response = self.client.post(
            get_submit_url("review"),
            data=step_data(state),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Push-Url"], get_step_url("generate"))
        self.assertIn("application_previews", response.context)
        # answers are untouched: the review submits none
        self.assertEqual(response_state(response)["answers"], answers)

    def test_review_post_with_invalid_stored_answers_falls_back_to_questions(self):
        state = create_state(
            [self.mastodon.pk], {"project-title": "Feed ranking audit"}
        )

        response = self.client.post(
            get_submit_url("review"),
            data=step_data(state),
            headers=HTMX_HEADERS,
        )

        # a POST that lands on another step pushes (render_step)
        self.assertEqual(response["HX-Push-Url"], get_step_url("enter-details"))

    def test_generate_shows_each_platforms_mapped_answers(self):
        state = create_state(
            [self.mastodon.pk, self.tiktok.pk],
            {"email": "a@example.org", "project-title": "", "role": "PI"},
        )

        response = self.client.post(
            get_step_url("generate"),
            data=step_data(state),
            headers=HTMX_HEADERS,
        )

        previews = response.context["application_previews"]
        self.assertEqual([p.vlopse_name for p in previews], ["Mastodon", "TikTok"])
        mastodon, tiktok = (p.form for p in previews)
        self.assertEqual(mastodon["mastodon-email"].value(), "a@example.org")
        self.assertIsNone(mastodon["mastodon-title"].value())
        self.assertEqual(tiktok["tiktok-role"].value(), "PI")
        # the unanswered optional title is empty, not a mapping error
        self.assertEqual([p.mapping_errors for p in previews], [{}, {}])

    def test_review_step_with_invalid_stored_answers_falls_back_to_questions(self):
        state = create_state(
            [self.mastodon.pk], {"project-title": "Feed ranking audit"}
        )

        response = self.client.post(
            get_step_url("review"),
            data=step_data(state),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response["HX-Replace-Url"], get_step_url("enter-details"))
        self.assertContains(response, "Institutional e-mail")

    def test_step_response_carries_wizard_id_file_key_and_max_age(self):
        response = self.client.post(
            get_step_url("choose-vlopses"),
            data=step_data(create_state([])),
            headers=HTMX_HEADERS,
        )

        self.assertEqual(response[WIZARD_ID_HEADER], "draft-1")
        self.assertEqual(
            response[FILE_KEY_HEADER], encode_file_encryption_key("draft-1")
        )
        self.assertEqual(response[MAX_STATE_AGE_HEADER], str(MAX_STATE_AGE))

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
            "mastodon.json": platform_config(
                "mastodon", {"mastodon-email": "email", "mastodon-cv": "cv"}
            )
        }

        # override mock to include the file field in the configs
        with mock.patch(CONFIG_FILE_READER, new=config_reader(configs)):
            response = self.client.post(
                get_submit_url("enter-details"),
                data=step_data(
                    create_state([self.mastodon.pk]),
                    {"email": "a@example.org", "cv": json.dumps(meta)},
                ),
                headers=HTMX_HEADERS,
            )

        self.assertEqual(response["HX-Push-Url"], get_step_url("review"))
        self.assertContains(response, "cv.pdf (2.0\xa0KB)")
        self.assertEqual(response_state(response)["answers"]["cv"], meta)

    def test_htmx_get_to_a_step_is_not_allowed(self):
        # the token travels in the POST body only, never in a URL
        response = self.client.get(get_step_url("choose-vlopses"), headers=HTMX_HEADERS)

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_post_to_the_plain_step_url_only_shows_the_step(self):
        # e.g. "Back" from Generate: must not confirm the review and move on
        answers = {"email": "a@example.org", "project-title": ""}
        state = create_state([self.mastodon.pk], answers)

        response = self.client.post(
            get_step_url("review"), data=step_data(state), headers=HTMX_HEADERS
        )

        self.assertEqual(response["HX-Replace-Url"], get_step_url("review"))
        self.assertNotIn("HX-Push-Url", response)
        self.assertTemplateUsed(response, ReviewStep.template_name)

    def test_shell_for_a_submit_url_loads_the_plain_step_url(self):
        # a plain page load of .../submit/ must not submit once the shell loads
        response = self.client.get(get_submit_url("review"))

        self.assertContains(response, f'hx-post="{get_step_url("review")}"')
        self.assertNotContains(response, f'hx-post="{get_submit_url("review")}"')
