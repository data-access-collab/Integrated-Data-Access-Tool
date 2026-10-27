from __future__ import annotations

import time
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from idat.dsa40_applications.state import (
    MAX_AGE,
    STATE_HEADER,
    WizardState,
    dump_state,
    empty_state,
    load_state,
)


class WizardStateTests(SimpleTestCase):
    def test_dumped_state_loads_back_unchanged(self):
        state = WizardState(vlopses=[1, 2], answers={"email-inst": "a@example.org"})
        request = RequestFactory().get("/", headers={STATE_HEADER: dump_state(state)})

        loaded = load_state(request)

        self.assertEqual(loaded, state)

    def test_missing_state_header_yields_empty_state(self):
        request = RequestFactory().get("/")

        loaded = load_state(request)

        self.assertEqual(loaded, empty_state())

    def test_expired_state_token_yields_empty_state(self):
        issued_at = time.time() - MAX_AGE - 60
        with mock.patch("django.core.signing.time.time", return_value=issued_at):
            token = dump_state(WizardState(vlopses=[1], answers={}))
        request = RequestFactory().get("/", headers={STATE_HEADER: token})

        loaded = load_state(request)

        self.assertEqual(loaded, empty_state())
