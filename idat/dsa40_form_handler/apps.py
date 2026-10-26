from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DSA40FormHandlerConfig(AppConfig):
    name = "idat.dsa40_form_handler"
    verbose_name = _("DSA40 Form Handler")

    def ready(self) -> None:
        """
        Override this method in subclasses to run code when Django starts.
        """
