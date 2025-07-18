from typing import List, Union, TypedDict
from ..base import _make_request


class QuizIPFilter(TypedDict):
    name: str
    account: str
    filter: str


def get_quiz_ip_filters(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
) -> List[QuizIPFilter]:
    """
    Get available quiz IP filters.

    Get a list of available IP filters for this Quiz.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID

    Returns:
        List of quiz IP filter dictionaries containing:
        - name: A unique name for the filter
        - account: Name of the Account (or Quiz) the IP filter is defined in
        - filter: An IP address (or range mask) this filter embodies
    """
    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/ip_filters",
    )
    result = response.json()
    return result.get("quiz_ip_filters", [])
