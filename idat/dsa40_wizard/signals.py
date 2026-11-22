"""Clear the cached help index (help.py) whenever a WizardInfo or its question
targets change."""

from __future__ import annotations

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from idat.dsa40_wizard.help import clear_help_index
from idat.dsa40_wizard.models import WizardInfo


@receiver(post_save, sender=WizardInfo)
@receiver(post_delete, sender=WizardInfo)
@receiver(m2m_changed, sender=WizardInfo.dsa_questions.through)
@receiver(m2m_changed, sender=WizardInfo.vlopse_questions.through)
def wizard_info_changed(**kwargs: object) -> None:
    transaction.on_commit(clear_help_index)
