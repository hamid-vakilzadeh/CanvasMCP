from typing import List, Dict, Union, Optional, TypedDict, Any
from ..base import CanvasAPIBase


class QuizStatisticsAnswerStatistics(TypedDict, total=False):
    id: Union[int, str]
    text: str
    weight: Optional[int]
    responses: int
    correct: Optional[bool]


class QuizStatisticsAnswerPointBiserial(TypedDict, total=False):
    answer_id: Union[int, str]
    point_biserial: Optional[float]
    correct: bool
    distractor: bool


class QuizStatisticsQuestionStatistics(TypedDict, total=False):
    responses: int
    answers: Optional[List[QuizStatisticsAnswerStatistics]]
    answered_student_count: Optional[int]
    top_student_count: Optional[int]
    middle_student_count: Optional[int]
    bottom_student_count: Optional[int]
    correct_student_count: Optional[int]
    incorrect_student_count: Optional[int]
    correct_student_ratio: Optional[float]
    incorrect_student_ratio: Optional[float]
    correct_top_student_count: Optional[int]
    correct_middle_student_count: Optional[int]
    correct_bottom_student_count: Optional[int]
    variance: Optional[float]
    stdev: Optional[float]
    difficulty_index: Optional[float]
    alpha: Optional[float]
    point_biserials: Optional[List[QuizStatisticsAnswerPointBiserial]]
    answered: Optional[int]
    correct: Optional[int]
    partially_correct: Optional[int]
    incorrect: Optional[int]
    answer_sets: Optional[List[Dict[str, Any]]]
    graded: Optional[int]
    full_credit: Optional[int]
    point_distribution: Optional[List[Dict[str, Union[int, float]]]]


class QuizStatisticsSubmissionStatistics(TypedDict, total=False):
    unique_count: int
    score_average: float
    score_high: float
    score_low: float
    score_stdev: float
    scores: Dict[str, int]
    correct_count_average: float
    incorrect_count_average: float
    duration_average: float


class QuizStatisticsLinks(TypedDict, total=False):
    quiz: str


class QuizStatistics(TypedDict, total=False):
    id: int
    quiz_id: Optional[int]
    multiple_attempts_exist: bool
    includes_all_versions: bool
    generated_at: str
    url: str
    html_url: str
    question_statistics: Optional[List[QuizStatisticsQuestionStatistics]]
    submission_statistics: Optional[QuizStatisticsSubmissionStatistics]
    links: Optional[QuizStatisticsLinks]


class QuizStatisticsAPI(CanvasAPIBase):
    """Canvas LMS Quiz Statistics API client for accessing quiz submission statistics."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas Quiz Statistics API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def get_quiz_statistics(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        all_versions: bool = False,
    ) -> List[QuizStatistics]:
        """
        Fetch the latest quiz statistics.

        This endpoint provides statistics for all quiz versions, or for a specific quiz version,
        in which case the output is guaranteed to represent the latest and most current version of the quiz.

        The statistics provided by this interface are an aggregate of what is known as Student and
        Item Analysis for a quiz. These statistics are extracted (and composed) from graded
        (manually or, when viable, automatically) submissions for a quiz and provide an insight
        into how the participant students had responded to each question, as well as insights
        into the reception of each question answer individually.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            all_versions: Whether the statistics report should include all submissions attempts

        Returns:
            List of quiz statistics dictionaries containing:
            - id: The ID of the quiz statistics report
            - quiz_id: The ID of the Quiz the statistics report is for (non-JSON-API only)
            - multiple_attempts_exist: Whether there are any students that have made multiple submissions
            - includes_all_versions: Whether statistics describe all submission attempts or only latest
            - generated_at: The time at which the statistics were generated
            - url: The API HTTP/HTTPS URL to this quiz statistics
            - html_url: The HTTP/HTTPS URL to the page where statistics can be seen visually
            - question_statistics: Question-specific statistics for each question and its answers
            - submission_statistics: Generic statistics for all submissions for a quiz
            - links: JSON-API construct with links to media related to this quiz statistics object
        """
        params = {"all_versions": all_versions}

        response = self._make_request(
            "GET",
            f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/statistics",
            params=params,
        )
        result = response.json()
        return result.get("quiz_statistics", [])


# Lazy-loaded convenience instance
def get_quiz_statistics():
    from ..base import access_token, url
    return QuizStatisticsAPI(access_token, url)

class _LazyQuizStatisticsAPI:
    def __getattr__(self, name):
        return getattr(get_quiz_statistics(), name)

quiz_statistics = _LazyQuizStatisticsAPI()
