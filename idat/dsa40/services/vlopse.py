from pathlib import Path

from idat.dsa40.lib.config import (
    PlatformInformation,
    VLOPSEConfiguration,
    get_vlopse_configuration_for,
    write_vlopse_configuration_for,
)

_DATA_DIR = Path(__file__).parent.parent / "data" / "vlopses"


class VlopseExistsException(BaseException):
    pass


class VlopseDoesNotExistException(BaseException):
    pass


class VlopseConfigService:
    def add(self, name: str, info: PlatformInformation) -> None:
        current = self.get(name)
        if current:
            raise VlopseExistsException
        empty = VLOPSEConfiguration(info=info, mappings={}, conditions={})
        write_vlopse_configuration_for(name, empty)

    def get(self, name: str) -> VLOPSEConfiguration | None:
        try:
            return get_vlopse_configuration_for(name)
        except FileNotFoundError:
            return None

    def get_all(self) -> list[str]:
        return [p.stem for p in _DATA_DIR.glob("*.json")]

    def delete(self, name: str) -> None:
        path = [p for p in _DATA_DIR.glob("*json") if p.stem == name]

        if not path:
            raise VlopseDoesNotExistException
        path[0].unlink()

    def rename(self, old_name: str, new_name: str) -> None:
        current = self.get(old_name)
        if current is None:
            raise VlopseDoesNotExistException
        new = self.get(new_name)
        if new:
            raise VlopseExistsException

        self.delete(old_name)
        self.add(new_name, current.info)
        self.update(new_name, current)

    def update(self, name: str, value: VLOPSEConfiguration) -> None:
        if self.get(name) is None:
            raise VlopseDoesNotExistException
        write_vlopse_configuration_for(name, value)
