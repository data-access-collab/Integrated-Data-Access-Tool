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

MAX_AGE = 60 * 60 * 6  # token expires after 6h
STATE_HEADER = "X-Wizard-State"
WIZARD_ID_HEADER = "X-Wizard-Id"
FILE_KEY_HEADER = "X-Wizard-File-Key"
MAX_AGE_HEADER = "X-Wizard-Max-Age"

STATE_TOKEN_KEY_INFO = b"dsa40-wizard-token"
FILE_KEY_INFO = b"dsa40-wizard-file:"


class WizardState(TypedDict):
    wizard_id: str  # random id of this draft, used to derive its file key
    vlopses: list[int]  # list of vlopse IDs
    answers: dict[str, Any]  # DSAQuestion ID, answer


def new_wizard_id() -> str:
    return secrets.token_urlsafe(16)


def empty_wizard_state() -> WizardState:
    return WizardState(wizard_id=new_wizard_id(), vlopses=[], answers={})


class WizardJSONSerializer:
    def dumps(self, obj: WizardState) -> bytes:
        return json.dumps(obj, separators=(",", ":"), cls=DjangoJSONEncoder).encode(
            "latin-1"
        )

    def loads(self, data: bytes) -> WizardState:
        return json.loads(data.decode("latin-1"))


def _derive_key(secret: str, info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(
        secret.encode()
    )


def _state_token_cipher() -> Fernet:
    key = _derive_key(settings.WIZARD_SECRET, STATE_TOKEN_KEY_INFO)
    return Fernet(base64.urlsafe_b64encode(key))


def load_wizard_state(request: HttpRequest) -> WizardState:
    token = request.headers.get(STATE_HEADER)
    if not token:
        return empty_wizard_state()
    cipher = _state_token_cipher()
    try:
        data = cipher.decrypt(token.encode(), ttl=MAX_AGE)
    except InvalidToken:
        # Fernet raises the same error for expired and tampered tokens, so
        # retry without TTL to tell them apart
        try:
            cipher.decrypt(token.encode())
        except InvalidToken as err:  # tampered
            msg = "Invalid wizard state"
            raise SuspiciousOperation(msg) from err
        return empty_wizard_state()
    return WizardJSONSerializer().loads(zlib.decompress(data))


def dump_wizard_state(state: WizardState) -> str:
    """Encrypt the state; the token embeds its issue time through Fernet.encrypt
    (sliding expiry)."""
    data = zlib.compress(WizardJSONSerializer().dumps(state))
    return _state_token_cipher().encrypt(data).decode()


def file_encryption_key(wizard_id: str) -> bytes:
    """AES-256 key the browser uses to encrypt this draft's files."""
    return _derive_key(settings.WIZARD_SECRET, FILE_KEY_INFO + wizard_id.encode())


def encode_file_encryption_key(wizard_id: str) -> str:
    return base64.urlsafe_b64encode(file_encryption_key(wizard_id)).decode().rstrip("=")
