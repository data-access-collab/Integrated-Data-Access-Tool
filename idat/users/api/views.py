from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import get_object_or_404
from ninja import Router

from idat.users.api.schema import UpdateUserSchema, UserSchema
from idat.users.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

router = Router(tags=["users"])


def _get_users_queryset(request: HttpRequest) -> QuerySet[User]:
    return User.objects.filter(pk=request.user.pk)


@router.get("/", response=list[UserSchema])
def list_users(request: HttpRequest) -> QuerySet[User, User]:
    return _get_users_queryset(request)


@router.get("/me/", response=UserSchema)
def retrieve_current_user(request: HttpRequest) -> User:
    return request.user


@router.get("/{username}/", response=UserSchema)
def retrieve_user(request: HttpRequest, username: str) -> User:
    users_qs = _get_users_queryset(request)
    return get_object_or_404(users_qs, username=username)


@router.patch("/me/", response=UserSchema)
def update_current_user(request: HttpRequest, data: UpdateUserSchema) -> User:
    user = request.user
    user.name = data.name
    user.username = data.username
    user.save()
    return user


@router.patch("/{username}/", response=UserSchema)
def update_user(request: HttpRequest, username: str, data: UpdateUserSchema) -> User:
    users_qs = _get_users_queryset(request)
    user = get_object_or_404(users_qs, username=username)
    user.name = data.name
    user.username = data.username
    user.save()
    return user
