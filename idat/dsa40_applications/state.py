import json
import typing
from typing import Any, TypedDict

from django.core import signing
from django.core.exceptions import SuspiciousOperation
from django.core.serializers.json import DjangoJSONEncoder

if typing.TYPE_CHECKING:
    from django.http.request import HttpRequest

SALT = "dsa40-application-wizard"
MAX_AGE = 60 * 60 * 6  # token expires after 6h
STATE_HEADER = "X-Wizard-State"


class WizardState(TypedDict):
    vlopses: list[int]  # list of vlopse IDs
    answers: dict[str, Any]  # DSAQuestion ID, answer


def empty_state() -> WizardState:
    return WizardState(vlopses=[], answers={})


class WizardJSONSerializer:
    def dumps(self, obj: WizardState) -> bytes:
        return json.dumps(obj, separators=(",", ":"), cls=DjangoJSONEncoder).encode(
            "latin-1"
        )

    def loads(self, data: bytes) -> WizardState:
        return json.loads(data.decode("latin-1"))


def load_state(request: HttpRequest) -> WizardState:
    token = request.headers.get(STATE_HEADER)
    if not token:
        return empty_state()
    try:
        return signing.loads(
            token, salt=SALT, max_age=MAX_AGE, serializer=WizardJSONSerializer
        )
    except signing.SignatureExpired:
        return empty_state()
    except signing.BadSignature as err:  # tampered or expired
        msg = "Invalid wizard state"
        raise SuspiciousOperation(msg) from err


def dump_state(state: WizardState) -> str:
    return signing.dumps(
        state, salt=SALT, compress=True, serializer=WizardJSONSerializer
    )
