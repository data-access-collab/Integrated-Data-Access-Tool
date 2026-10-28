from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class VlopseConfig(AppConfig):
    name = "idat.vlopse"
    verbose_name = _("VLOPSE")

    def ready(self) -> None:
        """
        Override this method in subclasses to run code when Django starts.
        """
