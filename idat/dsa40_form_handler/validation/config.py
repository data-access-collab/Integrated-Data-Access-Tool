from pathlib import Path

from pydantic import BaseModel

from idat.dsa40_form_handler.schema import Condition, PlatformMapping  # noqa: TC001

_VLOPSE_CONFIG_DIR = Path(__file__).parent.parent / "fixtures" / "vlopses"


class VLOPSEConfiguration(BaseModel):
    mappings: dict[str, PlatformMapping]
    conditions: dict[str, list[Condition]]


def _load_json(filename: str) -> VLOPSEConfiguration:
    path = _VLOPSE_CONFIG_DIR / filename
    data = path.read_text()
    return VLOPSEConfiguration.model_validate_json(data)


def _write_json(filename: str, value: VLOPSEConfiguration) -> None:
    path = _VLOPSE_CONFIG_DIR / filename
    serialized = value.model_dump_json()
    with path.open("w") as f:
        f.write(serialized)


def get_vlopse_configuration_for(platform_name: str) -> VLOPSEConfiguration:
    return _load_json(f"{platform_name}.json")


def write_vlopse_configuration_for(
    platform_name: str,
    config: VLOPSEConfiguration,
) -> None:
    return _write_json(f"{platform_name}.json", config)
