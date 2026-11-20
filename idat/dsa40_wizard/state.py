from __future__ import annotations

import base64
import json
import secrets
import typing
import zlib
from typing import Any, TypedDict

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.core.serializers.json import DjangoJSONEncoder

if typing.TYPE_CHECKING:
    from django.http.request import HttpRequest

MAX_STATE_AGE = (
    60 * 60 * 6
)  # sliding token TTL in seconds; also the TTL of browser-stored files.

# Mirrored in static/dsa40_wizard/wizard.js - if you change
# the values here, also change them in wizard.js
# The token goes to the server as a POST parameter and comes back in a response header.
STATE_POST_FIELD = "wizard_state"
STATE_REQUEST_HEADER = "X-Wizard-State"
WIZARD_ID_HEADER = "X-Wizard-Id"
FILE_KEY_HEADER = "X-Wizard-File-Key"
MAX_STATE_AGE_HEADER = "X-Wizard-Max-Age"
# the draft can't be loaded: the browser discards it and goes to this URL
DRAFT_UNAVAILABLE_HEADER = "X-Wizard-Draft-Unavailable"

# Encryption domain separation.
# Don't change - invalidates all existing tokens and client-side stored files
_STATE_TOKEN_KEY_INFO = b"dsa40-wizard-token"
_FILE_KEY_INFO = b"dsa40-wizard-file:"


class WizardStateExpiredError(Exception):
    """The state token is valid but older than MAX_STATE_AGE."""


class WizardState(TypedDict):
    wizard_id: str  # random id of this draft, used to derive its file key
    vlopses: list[int]  # list of VLOPSE IDs
    answers: dict[str, Any]  # {question key: JSON-serialized cleaned value}


def new_wizard_id() -> str:
    return secrets.token_urlsafe(16)


def empty_wizard_state() -> WizardState:
    return WizardState(wizard_id=new_wizard_id(), vlopses=[], answers={})


class WizardJSONSerializer:
    def dumps(self, obj: WizardState) -> bytes:
        return json.dumps(obj, separators=(",", ":"), cls=DjangoJSONEncoder).encode()

    def loads(self, data: bytes) -> WizardState:
        return json.loads(data.decode())


def _derive_key(secret: str, info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(
        secret.encode()
    )


def _state_token_cipher() -> Fernet:
    key = _derive_key(settings.WIZARD_SECRET, _STATE_TOKEN_KEY_INFO)
    return Fernet(base64.urlsafe_b64encode(key))


def load_wizard_state(request: HttpRequest) -> WizardState:
    """Load the state from the request's POST parameter.

    Missing token → new empty state.
    Expired token → raises WizardStateExpiredError.
    Tampered token, or one encrypted with another secret → raises SuspiciousOperation.
    """
    token = request.POST.get(STATE_POST_FIELD)
    if not token:
        return empty_wizard_state()
    cipher = _state_token_cipher()
    try:
        data = cipher.decrypt(token.encode(), ttl=MAX_STATE_AGE)
    except InvalidToken:
        # Fernet raises the same error for expired and tampered tokens, so
        # retry without TTL to tell them apart
        try:
            cipher.decrypt(token.encode())
        except InvalidToken as err:  # tampered
            msg = "Invalid wizard state"
            raise SuspiciousOperation(msg) from err
        raise WizardStateExpiredError from None
    return WizardJSONSerializer().loads(zlib.decompress(data))


def dump_wizard_state(state: WizardState) -> str:
    """Encrypt the state; the token embeds its issue time through Fernet.encrypt
    (sliding expiry)."""
    data = zlib.compress(WizardJSONSerializer().dumps(state))
    return _state_token_cipher().encrypt(data).decode()


def file_encryption_key(wizard_id: str) -> bytes:
    """AES-256 key the browser uses to encrypt this draft's files.

    Note: Only hand out for a verified token (Wizard State) to honor file expiry.
    """
    return _derive_key(settings.WIZARD_SECRET, _FILE_KEY_INFO + wizard_id.encode())


def encode_file_encryption_key(wizard_id: str) -> str:
    return base64.urlsafe_b64encode(file_encryption_key(wizard_id)).decode().rstrip("=")
