from pathlib import Path

from pydantic import BaseModel

from idat.dsa40_form_handler.schema import Condition, PlatformMapping  # noqa: TC001

_VLOPSE_CONFIG_DIR = Path(__file__).parent.parent / "fixtures" / "vlopses"


class VLOPSEConfiguration(BaseModel):
    mappings: dict[str, PlatformMapping]
    conditions: dict[str, list[Condition]]


# parsed configs by file name, with the file's modification time when parsed
_loaded: dict[str, tuple[int, VLOPSEConfiguration]] = {}


def _load_json(filename: str) -> VLOPSEConfiguration:
    """The parsed config file. Parsed once and reused until the file changes
    (modification time), so callers share it and must not modify it. Raises
    FileNotFoundError if the file doesn't exist."""
    path = _VLOPSE_CONFIG_DIR / filename
    modified = path.stat().st_mtime_ns
    if (loaded := _loaded.get(filename)) and loaded[0] == modified:
        return loaded[1]
    config = VLOPSEConfiguration.model_validate_json(path.read_text())
    _loaded[filename] = (modified, config)
    return config


def _write_json(filename: str, value: VLOPSEConfiguration) -> None:
    _loaded.pop(filename, None)
    path = _VLOPSE_CONFIG_DIR / filename
    serialized = value.model_dump_json()
    with path.open("w") as f:
        f.write(serialized)


def _config_filename(platform_name: str) -> str:
    """The config file of a VLOPSE: its name in lowercase ("TikTok" -> tiktok.json),
    as the files are named, so the lookup also works on case-sensitive filesystems."""
    return f"{platform_name.lower()}.json"


def get_vlopse_configuration_for(platform_name: str) -> VLOPSEConfiguration:
    return _load_json(_config_filename(platform_name))


def write_vlopse_configuration_for(
    platform_name: str,
    config: VLOPSEConfiguration,
) -> None:
    return _write_json(_config_filename(platform_name), config)
