from typing import List, Dict, Union, Optional
from ..base import _make_request


def get_classic_quiz_assignment_overrides(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_ids: Optional[List[Union[int, str]]] = None,
) -> Dict:
    """
    Retrieve assignment-overridden dates for Classic Quizzes.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_ids: Array of quiz IDs. If omitted, overrides for all quizzes
                    available to the operating user will be returned

    Returns:
        QuizAssignmentOverrideSetContainer dictionary containing quiz assignment overrides
    """
    params = {}

    if quiz_ids is not None:
        # Format as nested array parameter according to Canvas API specification
        for i, quiz_id in enumerate(quiz_ids):
            params[f"quiz_assignment_overrides[][quiz_ids][{i}]"] = quiz_id

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/quizzes/assignment_overrides",
        params=params,
    )
    return response.json()


def get_new_quiz_assignment_overrides(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_ids: Optional[List[Union[int, str]]] = None,
) -> Dict:
    """
    Retrieve assignment-overridden dates for New Quizzes.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_ids: Array of quiz IDs. If omitted, overrides for all quizzes
                    available to the operating user will be returned

    Returns:
        QuizAssignmentOverrideSetContainer dictionary containing quiz assignment overrides
    """
    params = {}

    if quiz_ids is not None:
        # Format as nested array parameter according to Canvas API specification
        for i, quiz_id in enumerate(quiz_ids):
            params[f"quiz_assignment_overrides[][quiz_ids][{i}]"] = quiz_id

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/new_quizzes/assignment_overrides",
        params=params,
    )
    return response.json()
