from django.urls import path

from idat.users.views import (
    user_account_view,
    user_affiliations_view,
    user_detail_view,
    user_update_view,
)

app_name = "users"
urlpatterns = [
    path("my-account/edit/", view=user_update_view, name="update"),
    path("my-account/affiliations/", view=user_affiliations_view, name="affiliations"),
    path("my-account/account/", view=user_account_view, name="account"),
    path("my-account/", view=user_detail_view, name="detail"),
]
