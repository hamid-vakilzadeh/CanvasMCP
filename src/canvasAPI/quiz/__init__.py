"""Quiz-related Canvas API modules

Provides APIs for managing quizzes, quiz extensions, quiz submissions, and quiz reports.
"""

from .course_quiz_extensions import CourseQuizExtensionsAPI, course_quiz_extensions
from .quizzes import QuizzesAPI, quizzes
from .quiz_questions import QuizQuestionsAPI, quiz_questions
from .quiz_question_groups import QuizQuestionGroupsAPI, quiz_question_groups
from .quiz_assignment_overrides import (
    QuizAssignmentOverridesAPI,
    quiz_assignment_overrides,
)
from .quiz_extensions import QuizExtensionsAPI, quiz_extensions
from .quiz_ip_filters import QuizIPFiltersAPI, quiz_ip_filters
from .quiz_reports import QuizReportsAPI, quiz_reports
from .quiz_statistics import QuizStatisticsAPI, quiz_statistics
from .quiz_submission_events import QuizSubmissionEventsAPI, quiz_submission_events
from .quiz_submission_files import QuizSubmissionFilesAPI, quiz_submission_files
from .quiz_submission_questions import (
    QuizSubmissionQuestionsAPI,
    quiz_submission_questions,
)
from .quiz_submission_user_list import (
    QuizSubmissionUserListAPI,
    quiz_submission_user_list,
)
from .quiz_submissions import QuizSubmissionsAPI, quiz_submissions

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
    "QuizExtensionsAPI",
    "quiz_extensions",
    "QuizIPFiltersAPI",
    "quiz_ip_filters",
    "QuizReportsAPI",
    "quiz_reports",
    "QuizStatisticsAPI",
    "quiz_statistics",
    "QuizSubmissionEventsAPI",
    "quiz_submission_events",
    "QuizSubmissionFilesAPI",
    "quiz_submission_files",
    "QuizSubmissionQuestionsAPI",
    "quiz_submission_questions",
    "QuizSubmissionUserListAPI",
    "quiz_submission_user_list",
    "QuizSubmissionsAPI",
    "quiz_submissions",
]
