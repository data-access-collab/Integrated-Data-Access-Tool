from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = "idat.core"
    verbose_name = _("IDAT Core App")

    def ready(self) -> None:
        """
        Override this method in subclasses to run code when Django starts.
        """
