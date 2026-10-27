from enum import StrEnum

from pydantic import BaseModel


class ApplicationModality(StrEnum):
    form = "form"
    email = "email"


class PlatformInformation(BaseModel):
    name: str
    platform_information: str | None = None
    account_required: bool
    application_link: str
    modality: ApplicationModality
