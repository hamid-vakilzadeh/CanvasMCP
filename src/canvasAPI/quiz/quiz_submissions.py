from typing import List, Dict, Union, Optional, TypedDict, Literal
from ..base import _make_request


class QuestionScoreComment(TypedDict, total=False):
    score: Optional[float]
    comment: Optional[str]


class QuizSubmissionUpdate(TypedDict, total=False):
    attempt: int
    fudge_points: Optional[float]
    questions: Dict[str, QuestionScoreComment]


class QuizSubmission(TypedDict, total=False):
    id: int
    quiz_id: int
    user_id: int
    submission_id: int
    started_at: Optional[str]
    finished_at: Optional[str]
    end_at: Optional[str]
    attempt: int
    extra_attempts: int
    extra_time: int
    manually_unlocked: bool
    time_spent: Optional[int]
    score: Optional[float]
    score_before_regrade: Optional[float]
    kept_score: Optional[float]
    fudge_points: Optional[float]
    has_seen_results: bool
    workflow_state: Literal[
        "untaken", "pending_review", "complete", "settings_only", "preview"
    ]
    overdue_and_needs_submission: bool


class QuizSubmissionTimes(TypedDict):
    end_at: Optional[str]
    time_left: Optional[int]


def get_all_quiz_submissions(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    include: Optional[List[Literal["submission", "quiz", "user"]]] = None,
) -> List[QuizSubmission]:
    """
    Get all quiz submissions.

    Get a list of all submissions for this quiz. Users who can view or manage grades
    for a course will have submissions from multiple users returned. A user who can
    only submit will have only their own submissions returned. When a user has an
    in-progress submission, only that submission is returned. When there isn't an
    in-progress quiz_submission, all completed submissions, including previous attempts,
    are returned.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        include: Associations to include with the quiz submission.
                Allowed values: ["submission", "quiz", "user"]

    Returns:
        List of quiz submission dictionaries
    """
    params = {}
    if include:
        # Validate include values
        valid_include_values = {"submission", "quiz", "user"}
        for value in include:
            if value not in valid_include_values:
                raise ValueError(
                    f"Invalid include value '{value}'. "
                    f"Allowed values: {', '.join(sorted(valid_include_values))}"
                )
        params["include[]"] = include

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions",
        params=params,
    )
    result = response.json()
    return result.get("quiz_submissions", [])


def get_current_user_quiz_submission(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    include: Optional[List[Literal["submission", "quiz", "user"]]] = None,
) -> List[QuizSubmission]:
    """
    Get the quiz submission for the current user.

    Get the submission for this quiz for the current user.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        include: Associations to include with the quiz submission.
                Allowed values: ["submission", "quiz", "user"]

    Returns:
        List of quiz submission dictionaries (typically one item)
    """
    params = {}
    if include:
        # Validate include values
        valid_include_values = {"submission", "quiz", "user"}
        for value in include:
            if value not in valid_include_values:
                raise ValueError(
                    f"Invalid include value '{value}'. "
                    f"Allowed values: {', '.join(sorted(valid_include_values))}"
                )
        params["include[]"] = include

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submission",
        params=params,
    )
    result = response.json()
    return result.get("quiz_submissions", [])


def get_quiz_submission(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    submission_id: Union[int, str],
    include: Optional[List[Literal["submission", "quiz", "user"]]] = None,
) -> List[QuizSubmission]:
    """
    Get a single quiz submission.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        submission_id: Quiz submission ID
        include: Associations to include with the quiz submission.
                Allowed values: ["submission", "quiz", "user"]

    Returns:
        List of quiz submission dictionaries (typically one item)
    """
    params = {}
    if include:
        # Validate include values
        valid_include_values = {"submission", "quiz", "user"}
        for value in include:
            if value not in valid_include_values:
                raise ValueError(
                    f"Invalid include value '{value}'. "
                    f"Allowed values: {', '.join(sorted(valid_include_values))}"
                )
        params["include[]"] = include

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/{submission_id}",
        params=params,
    )
    result = response.json()
    return result.get("quiz_submissions", [])


def create_quiz_submission(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    access_code: Optional[str] = None,
    preview: bool = False,
) -> List[QuizSubmission]:
    """
    Create the quiz submission (start a quiz-taking session).

    Start taking a Quiz by creating a QuizSubmission which you can use to answer
    questions and submit your answers.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        access_code: Access code for the Quiz, if any
        preview: Whether this should be a preview QuizSubmission and not count
                towards the user's course record. Teachers only.

    Returns:
        List of quiz submission dictionaries (typically one item)

    Raises:
        RequestError: Various HTTP errors based on conditions:
            - 400 Bad Request if the quiz is locked
            - 403 Forbidden if an invalid access code is specified
            - 403 Forbidden if the Quiz's IP filter restriction does not pass
            - 409 Conflict if a QuizSubmission already exists for this user and quiz
    """
    data = {"preview": preview}

    if access_code is not None:
        data["access_code"] = access_code

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions",
        data=data,
    )
    result = response.json()
    return result.get("quiz_submissions", [])


def update_quiz_submission(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    submission_id: Union[int, str],
    quiz_submissions: List[QuizSubmissionUpdate],
) -> List[QuizSubmission]:
    """
    Update student question scores and comments.

    Update the amount of points a student has scored for questions they've answered,
    provide comments for the student about their answer(s), or simply fudge the total
    score by a specific amount of points.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        submission_id: Quiz submission ID
        quiz_submissions: List of quiz submission updates. Each update should contain:
            - attempt: The attempt number that should be updated (must be completed)
            - fudge_points: Amount of positive or negative points to fudge total score by (optional)
            - questions: Dict mapping question IDs to score/comment objects (optional)

    Returns:
        List of updated quiz submission dictionaries

    Raises:
        ValueError: If quiz_submissions is empty or validation fails
        RequestError: Various HTTP errors:
            - 403 Forbidden if you are not a teacher in this course
            - 400 Bad Request if the attempt parameter is missing or invalid
            - 400 Bad Request if the specified QS attempt is not yet complete
    """
    if not quiz_submissions:
        raise ValueError("quiz_submissions cannot be empty")

    # Validate submission structure
    for i, submission in enumerate(quiz_submissions):
        if "attempt" not in submission:
            raise ValueError(f"Submission at index {i} must have an 'attempt'")

    # Build request data
    data = {}
    for i, submission in enumerate(quiz_submissions):
        data[f"quiz_submissions[{i}][attempt]"] = submission["attempt"]

        if "fudge_points" in submission and submission["fudge_points"] is not None:
            data[f"quiz_submissions[{i}][fudge_points]"] = submission["fudge_points"]

        if "questions" in submission:
            questions = submission["questions"]
            for question_id, question_data in questions.items():
                if "score" in question_data and question_data["score"] is not None:
                    data[f"quiz_submissions[{i}][questions][{question_id}][score]"] = (
                        question_data["score"]
                    )
                if "comment" in question_data and question_data["comment"] is not None:
                    data[
                        f"quiz_submissions[{i}][questions][{question_id}][comment]"
                    ] = question_data["comment"]

    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/{submission_id}",
        data=data,
    )
    result = response.json()
    return result.get("quiz_submissions", [])


def complete_quiz_submission(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    submission_id: Union[int, str],
    attempt: int,
    validation_token: str,
    access_code: Optional[str] = None,
) -> List[QuizSubmission]:
    """
    Complete the quiz submission (turn it in).

    Complete the quiz submission by marking it as complete and grading it. When the
    quiz submission has been marked as complete, no further modifications will be allowed.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        submission_id: Quiz submission ID
        attempt: The attempt number of the quiz submission that should be completed.
                Note that this must be the latest attempt index, as earlier attempts
                cannot be modified.
        validation_token: The unique validation token you received when this Quiz
                        Submission was created
        access_code: Access code for the Quiz, if any

    Returns:
        List of quiz submission dictionaries (typically one item)

    Raises:
        RequestError: Various HTTP errors:
            - 403 Forbidden if an invalid access code is specified
            - 403 Forbidden if the Quiz's IP filter restriction does not pass
            - 403 Forbidden if an invalid token is specified
            - 400 Bad Request if the QS is already complete
            - 400 Bad Request if the attempt parameter is missing
            - 400 Bad Request if the attempt parameter is not the latest attempt
    """
    data = {
        "attempt": attempt,
        "validation_token": validation_token,
    }

    if access_code is not None:
        data["access_code"] = access_code

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/{submission_id}/complete",
        data=data,
    )
    result = response.json()
    return result.get("quiz_submissions", [])


def get_quiz_submission_times(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    submission_id: Union[int, str],
) -> QuizSubmissionTimes:
    """
    Get current quiz submission times.

    Get the current timing data for the quiz attempt, both the end_at timestamp
    and the time_left parameter.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        submission_id: Quiz submission ID

    Returns:
        Dictionary containing timing information:
        - end_at: The end timestamp for the quiz attempt
        - time_left: Time remaining in seconds
    """
    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/{submission_id}/time",
    )
    return response.json()
