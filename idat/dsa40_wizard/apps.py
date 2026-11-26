from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DSA40Wizard(AppConfig):
    name = "idat.dsa40_wizard"
    verbose_name = _("DSA40 Application Wizard")

    def ready(self) -> None:
        # connects the receivers
        from idat.dsa40_wizard import signals  # noqa: F401, PLC0415
