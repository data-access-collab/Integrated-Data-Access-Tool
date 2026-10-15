from enum import StrEnum

from ninja import ModelSchema, Schema

from idat.dsa40.models import DSAQuestion, Vlopse, VLOPSEQuestion


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


class VlopseInfoSchema(ModelSchema):
    class Meta:
        model = Vlopse
        fields = [
            "platform_information",
            "account_required",
            "application_link",
            "modality",
        ]


class VlopseOut(Schema):
    id: str
    info: VlopseInfoSchema

    @staticmethod
    def resolve_id(obj: Vlopse) -> str:
        return obj.name

    @staticmethod
    def resolve_info(obj: Vlopse) -> Vlopse:
        return obj


class CreateVlopseSchema(Schema):
    id: str
    info: VlopseInfoSchema


class UpdateVlopseSchema(Schema):
    new_name: str


class VlopseQuestionOut(ModelSchema):
    class Meta:
        model = VLOPSEQuestion
        fields = [
            "id",
            "text",
            "vlopse",
            "required",
            "input_type",
            "details",
            "config",
        ]


class CreateVlopseQuestionSchema(ModelSchema):
    class Meta:
        model = VLOPSEQuestion
        exclude = ["vlopse"]


class DSAQuestionOut(ModelSchema):
    options: list[str] = []
    required: bool = True

    class Meta:
        model = DSAQuestion
        fields = [
            "id",
            "text",
            "help_text",
            "input_type",
            "config",
        ]


class CreateDSAQuestionSchema(ModelSchema):
    class Meta:
        model = DSAQuestion
        fields = [
            "id",
            "text",
            "help_text",
            "input_type",
            "config",
        ]
