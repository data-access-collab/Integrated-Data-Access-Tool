from django.core.management.base import BaseCommand

from idat.dsa40.loaders import load_questions


class Command(BaseCommand):
    help = "Load questions from fixture file"

    def handle(self, *args, **options) -> None:
        num_loaded = load_questions()

        self.stdout.write(self.style.SUCCESS(f"Loaded {num_loaded} questions"))
