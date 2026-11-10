from django.urls import path

from idat.dsa40_wizard import views

app_name = "dsa40_wizard"
urlpatterns = [
    path("create/", view=views.WizardFormView.as_view(), name="create"),
    path("create/<slug:step>/", view=views.route_wizard_step, name="wizard_step"),
]
