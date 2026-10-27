from __future__ import annotations

from django.test import SimpleTestCase

from idat.dsa40.models import InputType
from idat.dsa40.tests.factories import DsaQuestionFactory
from idat.dsa40_applications.forms import QuestionsForm


class QuestionsFormTests(SimpleTestCase):
    def test_questions_form_requires_only_required_questions(self):
        required = DsaQuestionFactory.build(key="email", input_type=InputType.TEXT)
        optional = DsaQuestionFactory.build(key="nickname", input_type=InputType.TEXT)
        config = [(True, required), (False, optional)]

        with_required = QuestionsForm(
            data={"email": "a@example.org"}, question_config=config, answers={}
        )
        without_required = QuestionsForm(
            data={"nickname": "ada"}, question_config=config, answers={}
        )

        self.assertTrue(with_required.is_valid())
        self.assertFalse(without_required.is_valid())
        self.assertIn("email", without_required.errors)

    def test_questions_form_prefills_stored_answers(self):
        question = DsaQuestionFactory.build(key="email", input_type=InputType.TEXT)

        form = QuestionsForm(
            question_config=[(True, question)], answers={"email": "a@example.org"}
        )

        self.assertEqual(form["email"].value(), "a@example.org")

    def test_selection_question_accepts_flat_option_list(self):
        question = DsaQuestionFactory.build(
            key="prev-experience",
            input_type=InputType.SELECTION,
            config={"type": "selection", "options": ["Yes", "No"]},
        )
        config = [(True, question)]

        valid = QuestionsForm(
            data={"prev-experience": "No"}, question_config=config, answers={}
        )
        invalid = QuestionsForm(
            data={"prev-experience": "Maybe"}, question_config=config, answers={}
        )

        self.assertTrue(valid.is_valid())
        self.assertFalse(invalid.is_valid())
