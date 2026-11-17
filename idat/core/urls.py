from django.http import Http404
from django.urls import path


def _404(request, *args, **kwargs):  # noqa: ANN202, ANN001
    """Temporary helper to return 404 page"""
    raise Http404


app_name = "core"
urlpatterns = [
    path("terms-of-service/", view=_404, name="terms-of-service"),
    path("privacy-policy/", view=_404, name="privacy-policy"),
]
