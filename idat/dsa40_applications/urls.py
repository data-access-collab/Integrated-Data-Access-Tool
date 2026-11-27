from django.urls import path

from idat.dsa40_applications import views

app_name = "dsa40_applications"
urlpatterns = [
    path(
        "project/<int:pk>",
        view=views.ProjectOverview.as_view(),
        name="project_overview",
    ),
    path(
        "case/<int:pk>", view=views.AccessCaseOverview.as_view(), name="case_overview"
    ),
]
