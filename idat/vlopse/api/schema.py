from ninja import ModelSchema, Schema

from idat.vlopse.models import Vlopse


class VlopseOut(ModelSchema):
    class Meta:
        model = Vlopse
        exclude = ["id"]


class CreateVlopseSchema(ModelSchema):
    class Meta:
        model = Vlopse
        exclude = ["id"]


class UpdateVlopseSchema(Schema):
    new_name: str
