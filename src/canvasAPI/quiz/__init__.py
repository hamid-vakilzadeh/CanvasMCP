"""Quiz-related Canvas API modules

Provides APIs for managing quizzes, quiz extensions, and quiz submissions.
"""

from .course_quiz_extensions import CourseQuizExtensionsAPI, course_quiz_extensions

__all__ = [
    "CourseQuizExtensionsAPI",
    "course_quiz_extensions",
]
