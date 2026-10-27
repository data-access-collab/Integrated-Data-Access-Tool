from django.urls import path

from idat.dsa40_applications import views

app_name = "dsa40_applications"
urlpatterns = [
    path("create/", view=views.ApplicationFormView.as_view(), name="create"),
    path("create/step/<int:step>/", view=views.wizard_step, name="wizard_step"),
]
