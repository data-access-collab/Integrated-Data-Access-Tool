from ninja import Field, ModelSchema

from idat.dsa40_form_handler.models import DSAQuestion, VLOPSEQuestion


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
