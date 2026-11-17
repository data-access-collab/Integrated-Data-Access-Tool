from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from idat.users.validators import validate_orcid


class IdatUserManager(UserManager):
    """Custom user model manager where email is the unique identifier for
    authentication."""

    def _create_user(
        self, email: str | None = None, password: str | None = None, **extra_fields
    ) -> User:
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self, email: str | None = None, password: str | None = None, **extra_fields
    ) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self, email: str | None = None, password: str | None = None, **extra_fields
    ) -> User:
        return self._create_user(
            email, password, is_staff=True, is_superuser=True, **extra_fields
        )


class User(AbstractUser):
    """
    Custom user model for Integrated Data Access Tool. Users log in with their
    e-mail.
    If adding fields that need to be filled at user signup, check forms.UserSignupForm.
    """

    username = None  # e-mail address is used as ID
    email = models.EmailField(_("institutional e-mail"), unique=True)
    orcid = models.CharField(
        _("ORCID iD"),
        max_length=19,
        unique=True,
        null=True,  # many users may not have one
        blank=True,
        validators=[validate_orcid],
        help_text=_("Format: 0000-0000-0000-0000"),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # AbstractUser puts "email" here

    objects = IdatUserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_unique"),
        ]

    def get_absolute_url(self) -> str:
        return reverse("users:detail")

    @property
    def display_name(self) -> str:
        """Short name for the app sidebar: "Jana D.", else the e-mail."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name[:1]}."
        return self.first_name or self.email

    @property
    def initials(self) -> str:
        """For the avatar: first letters of first and last name, else of the e-mail."""
        initials = (self.first_name[:1] + self.last_name[:1]).upper()
        return initials or self.email[:1].upper()
