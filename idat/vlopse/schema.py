from enum import StrEnum

from pydantic import BaseModel


class ApplicationModality(StrEnum):
    unknown = "unknown"
    form = "form"
    email = "email"
    icpsr = "icpsr"


class PlatformInformation(BaseModel):
    name: str
    platform_information: str | None = None
    account_required: bool
    application_link: str
    modality: ApplicationModality
