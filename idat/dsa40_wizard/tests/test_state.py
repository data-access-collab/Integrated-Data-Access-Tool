from __future__ import annotations

import base64
import datetime
import time
from unittest import mock

from django.core.exceptions import SuspiciousOperation
from django.test import RequestFactory, SimpleTestCase, override_settings

from idat.dsa40_wizard.state import (
    MAX_STATE_AGE,
    STATE_POST_FIELD,
    WizardState,
    WizardStateExpiredError,
    dump_wizard_state,
    file_encryption_key,
    load_wizard_state,
)


def request_with_state_token(token: str):
    return RequestFactory().post("/", {STATE_POST_FIELD: token})


class WizardStateTests(SimpleTestCase):
    def test_dumped_state_loads_back_with_dates_as_iso_strings(self):
        state = WizardState(
            wizard_id="draft-1",
            vlopses=[1, 2],
            answers={
                "email-inst": "a@example.org",
                "city": "Zürich",
                "risks": ["Posts", "Comments"],
                "start": datetime.date(2026, 1, 31),
            },
        )

        dumped_state = dump_wizard_state(state)
        loaded = load_wizard_state(request_with_state_token(dumped_state))

        self.assertEqual(
            loaded,
            WizardState(
                wizard_id="draft-1",
                vlopses=[1, 2],
                answers={
                    "email-inst": "a@example.org",
                    "city": "Zürich",
                    "risks": ["Posts", "Comments"],
                    "start": "2026-01-31",
                },
            ),
        )

    def test_token_does_not_contain_answers_in_plain_text(self):
        state = WizardState(
            wizard_id="draft-1", vlopses=[1], answers={"email": "a@example.org"}
        )

        token = dump_wizard_state(state)

        self.assertNotIn("example.org", token)
        self.assertNotIn("draft-1", token)

    def test_missing_state_token_yields_empty_state_with_new_wizard_id(self):
        first = load_wizard_state(RequestFactory().get("/"))
        second = load_wizard_state(RequestFactory().get("/"))

        self.assertEqual((first["vlopses"], first["answers"]), ([], {}))
        self.assertTrue(first["wizard_id"])
        self.assertNotEqual(first["wizard_id"], second["wizard_id"])

    def test_expired_state_token_raises_expired_error(self):
        issued_at = time.time() - MAX_STATE_AGE - 60
        with mock.patch("cryptography.fernet.time.time", return_value=issued_at):
            token = dump_wizard_state(
                WizardState(wizard_id="draft-1", vlopses=[1], answers={})
            )

        with self.assertRaises(WizardStateExpiredError):
            load_wizard_state(request_with_state_token(token))

    def test_tampered_state_token_raises_suspicious_operation(self):
        token = dump_wizard_state(
            WizardState(wizard_id="draft-1", vlopses=[1], answers={})
        )
        # flip one bit of the token's HMAC
        raw = bytearray(base64.urlsafe_b64decode(token))
        raw[-1] ^= 1
        tampered = base64.urlsafe_b64encode(raw).decode()

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
