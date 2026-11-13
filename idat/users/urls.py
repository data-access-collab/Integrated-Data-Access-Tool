from django.urls import path

from idat.users.views import user_detail_view, user_update_view

app_name = "users"
urlpatterns = [
    path("my-account/edit/", view=user_update_view, name="update"),
    path("my-account/", view=user_detail_view, name="detail"),
]
