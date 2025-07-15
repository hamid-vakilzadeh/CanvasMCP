"""Quiz-related Canvas API modules

Provides APIs for managing quizzes, quiz extensions, and quiz submissions.
"""

from .course_quiz_extensions import CourseQuizExtensionsAPI, course_quiz_extensions
from .quizzes import QuizzesAPI, quizzes
from .quiz_questions import QuizQuestionsAPI, quiz_questions
from .quiz_question_groups import QuizQuestionGroupsAPI, quiz_question_groups
from .quiz_assignment_overrides import QuizAssignmentOverridesAPI, quiz_assignment_overrides

__all__ = [
    "CourseQuizExtensionsAPI",
    "course_quiz_extensions",
    "QuizzesAPI",
    "quizzes",
    "QuizQuestionsAPI",
    "quiz_questions",
    "QuizQuestionGroupsAPI",
    "quiz_question_groups",
    "QuizAssignmentOverridesAPI",
    "quiz_assignment_overrides",
]
