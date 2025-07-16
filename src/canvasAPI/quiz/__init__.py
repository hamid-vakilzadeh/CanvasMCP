"""Quiz-related Canvas API modules

Provides APIs for managing quizzes, quiz extensions, quiz submissions, and quiz reports.
"""

from .course_quiz_extensions import CourseQuizExtensionsAPI, course_quiz_extensions
from .quizzes import QuizzesAPI, quizzes
from .quiz_questions import QuizQuestionsAPI, quiz_questions
from .quiz_question_groups import QuizQuestionGroupsAPI, quiz_question_groups
from .quiz_assignment_overrides import QuizAssignmentOverridesAPI, quiz_assignment_overrides
from .quiz_extensions import QuizExtensionsTools
from .quiz_reports import QuizReportsTools
from .quiz_statistics import QuizStatisticsTools
from .quiz_submission_events import QuizSubmissionEventsTools
from .quiz_submission_files import QuizSubmissionFilesTools
from .quiz_submission_questions import QuizSubmissionQuestionsTools
from .quiz_submission_user_list import QuizSubmissionUserListTools
from .quiz_submissions import QuizSubmissionsTools

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
    "QuizExtensionsTools",
    "QuizReportsTools",
    "QuizStatisticsTools",
    "QuizSubmissionEventsTools",
    "QuizSubmissionFilesTools",
    "QuizSubmissionQuestionsTools",
    "QuizSubmissionUserListTools",
    "QuizSubmissionsTools",
]
