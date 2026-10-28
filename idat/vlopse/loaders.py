from pathlib import Path

from idat.vlopse.schema import PlatformInformation

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_VLOPSE_CONFIG_DIR = _FIXTURES_DIR / "vlopses"


def list_all_vlopse_files() -> list[Path]:
    return list(_VLOPSE_CONFIG_DIR.glob("*.json"))


def _load_json(filename: str) -> PlatformInformation:
    path = _VLOPSE_CONFIG_DIR / filename
    data = path.read_text()
    return PlatformInformation.model_validate_json(data)


def get_platform_information_for(platform_name: str) -> PlatformInformation:
    return _load_json(f"{platform_name}.json")
