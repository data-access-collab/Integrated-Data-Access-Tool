from enum import StrEnum

from ninja import Field, ModelSchema, Schema

from idat.dsa40.models import DSAQuestion, VLOPSEQuestion


class Status(StrEnum):
    OK = "ok"
    ERROR = "error"


class HealthOut(Schema):
    api: Status
    db: Status
    dsa_status: int | Status
    mapping_status: int | Status


class ActionOut(Schema):
    success: bool


class VlopseQuestionOut(ModelSchema):
    vlopse: str = Field(..., alias="vlopse.name")

    class Meta:
        model = VLOPSEQuestion
        exclude = ["id"]


class CreateVlopseQuestionSchema(ModelSchema):
    class Meta:
        model = VLOPSEQuestion
        exclude = ["vlopse"]


class DSAQuestionOut(ModelSchema):
    options: list[str] = []
    required: bool = True

    class Meta:
        model = DSAQuestion
        exclude = ["id"]


class CreateDSAQuestionSchema(ModelSchema):
    class Meta:
        model = DSAQuestion
        exclude = ["id"]
