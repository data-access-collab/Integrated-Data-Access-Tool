from enum import StrEnum

from ninja import Schema


class Status(StrEnum):
    OK = "ok"
    ERROR = "error"


class HealthOut(Schema):
    api: Status
    db: Status
    dsa_status: int | Status
    mapping_status: int | Status
