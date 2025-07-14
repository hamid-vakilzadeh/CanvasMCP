"""Quiz-related Canvas API modules

Provides APIs for managing quizzes, quiz extensions, and quiz submissions.
"""

from .course_quiz_extensions import CourseQuizExtensionsAPI, course_quiz_extensions
from .quizzes import QuizzesAPI, quizzes
from .quiz_questions import QuizQuestionsAPI, quiz_questions

__all__ = [
    "CourseQuizExtensionsAPI",
    "course_quiz_extensions",
    "QuizzesAPI",
    "quizzes",
    "QuizQuestionsAPI",
    "quiz_questions",
]
