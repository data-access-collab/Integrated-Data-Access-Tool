from __future__ import annotations

import time
from unittest import mock

from django.core.exceptions import SuspiciousOperation
from django.test import RequestFactory, SimpleTestCase, override_settings

from idat.dsa40_applications.state import (
    MAX_AGE,
    STATE_HEADER,
    WizardState,
    dump_wizard_state,
    file_encryption_key,
    load_wizard_state,
)


def request_with_state_token(token: str):
    return RequestFactory().get("/", headers={STATE_HEADER: token})


class WizardStateTests(SimpleTestCase):
    def assertIsEmptyState(self, state: WizardState):  # noqa: N802
        self.assertEqual(state["vlopses"], [])
        self.assertEqual(state["answers"], {})
        self.assertTrue(state["wizard_id"])

    def test_dumped_state_loads_back_unchanged(self):
        state = WizardState(
            wizard_id="draft-1", vlopses=[1, 2], answers={"email-inst": "a@example.org"}
        )

        dumped_state = dump_wizard_state(state)
        loaded = load_wizard_state(request_with_state_token(dumped_state))

        self.assertEqual(loaded, state)

    def test_token_does_not_contain_answers_in_plain_text(self):
        state = WizardState(
            wizard_id="draft-1", vlopses=[1], answers={"email": "a@example.org"}
        )

        token = dump_wizard_state(state)

        self.assertNotIn("example.org", token)
        self.assertNotIn("draft-1", token)

    def test_missing_state_header_yields_empty_state(self):
        loaded = load_wizard_state(RequestFactory().get("/"))

        self.assertIsEmptyState(loaded)

    def test_empty_states_get_distinct_wizard_ids(self):
        first = load_wizard_state(RequestFactory().get("/"))
        second = load_wizard_state(RequestFactory().get("/"))

        self.assertNotEqual(first["wizard_id"], second["wizard_id"])

    def test_expired_state_token_yields_new_empty_state(self):
        issued_at = time.time() - MAX_AGE - 60
        with mock.patch("cryptography.fernet.time.time", return_value=issued_at):
            token = dump_wizard_state(
                WizardState(wizard_id="draft-1", vlopses=[1], answers={})
            )

        loaded = load_wizard_state(request_with_state_token(token))

        self.assertIsEmptyState(loaded)
        self.assertNotEqual(loaded["wizard_id"], "draft-1")

    def test_tampered_state_token_raises_suspicious_operation(self):
        token = dump_wizard_state(
            WizardState(wizard_id="draft-1", vlopses=[1], answers={})
        )
        tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

        with self.assertRaises(SuspiciousOperation):
            load_wizard_state(request_with_state_token(tampered))

    def test_token_of_unknown_secret_raises_suspicious_operation(self):
        with override_settings(WIZARD_SECRET="other-secret"):
            token = dump_wizard_state(
                WizardState(wizard_id="draft-1", vlopses=[], answers={})
            )

        with self.assertRaises(SuspiciousOperation):
            load_wizard_state(request_with_state_token(token))

    def test_file_key_is_stable_per_draft_and_differs_between_drafts(self):
        self.assertEqual(file_encryption_key("draft-1"), file_encryption_key("draft-1"))
        self.assertNotEqual(
            file_encryption_key("draft-1"), file_encryption_key("draft-2")
        )
        self.assertEqual(len(file_encryption_key("draft-1")), 32)

    def test_file_key_depends_on_secret(self):
        with override_settings(WIZARD_SECRET="other-secret"):
            other = file_encryption_key("draft-1")

        self.assertNotEqual(file_encryption_key("draft-1"), other)
