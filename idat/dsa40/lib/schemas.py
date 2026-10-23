import pathlib
from typing import Annotated, Literal

from pycountry import countries
from pydantic import BaseModel, Field, TypeAdapter


class ISO_3166_1(BaseModel):  # noqa: N801
    type: Literal["iso-3166-1"]

    def validate_answer(self, value: str) -> str | None:
        country = countries.get(name=value)
        if country is None:
            return f"Invalid selection: {value}"
        return None


class Selection(BaseModel):
    # TODO: rename property name
    type: Literal["selection"]
    options: list[str]
    multiple: bool = False

    def validate_answer(self, value: str | list[str]) -> str | None:
        if isinstance(value, list) and not self.multiple:
            return "Only one selection allowed"
        values = value if isinstance(value, list) else [value]
        invalid = [v for v in values if v not in self.options]
        if invalid:
            return f"""Invalid option(s): {", ".join(invalid)}.
            Possible: {", ".join(self.options)}"""
        return None


class Boolean(BaseModel):
    type: Literal["boolean"]

    def validate_answer(self, value: str) -> str | None:
        if value.lower() not in ["yes", "no", "true", "false"]:
            return f"Invalid boolean {value}"
        return None


class Text(BaseModel):
    type: Literal["text"]
    max_length: int | None = None

    def validate_answer(self, value: str) -> str | None:
        if self.max_length and len(value) > self.max_length:
            return f"Must not exceed {self.max_length} characters"
        return None


class FileUpload(BaseModel):
    type: Literal["file_upload"]

    def validate_answer(self, value: str) -> str | None:
        try:
            p = pathlib.Path(value)
            if not p.name:
                return f"{value} does not look like a file name."

        except ValueError:
            return f"{value} does not look like a file name."
        return None


class DateRange(BaseModel):
    type: Literal["daterange"]
    begin: Literal["TODO"]


class DateSelect(BaseModel):
    type: Literal["date_select"]


ConstraintConfig = Annotated[Selection | Text | ISO_3166_1, Field(discriminator="type")]


config_adapter = TypeAdapter(ConstraintConfig)
