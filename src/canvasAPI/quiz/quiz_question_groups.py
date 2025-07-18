from typing import List, Dict, Union, Optional, TypedDict
from ..base import _make_request


class QuizGroupData(TypedDict, total=False):
    """Quiz group data for create/update operations."""

    name: str
    pick_count: int
    question_points: int
    assessment_question_bank_id: Optional[int]


class ReorderItem(TypedDict):
    """Item for reorder operations."""

    id: int
    type: str


def get_quiz_group(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    group_id: Union[int, str],
) -> Dict:
    """
    Get a single quiz group.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        group_id: Quiz group ID

    Returns:
        QuizGroup dictionary
    """
    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/groups/{group_id}",
    )
    return response.json()


def create_quiz_group(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    name: str,
    pick_count: int,
    question_points: int,
    assessment_question_bank_id: Optional[int] = None,
) -> Dict:
    """
    Create a new question group for a quiz.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        name: The name of the question group
        pick_count: The number of questions to randomly select for this group
        question_points: The number of points to assign to each question in the group
        assessment_question_bank_id: The id of the assessment question bank to pull questions from

    Returns:
        Response dictionary containing the created quiz group

    Raises:
        ValueError: If name is empty or pick_count/question_points are invalid
    """
    if not name or not name.strip():
        raise ValueError("Quiz group name cannot be empty")

    if pick_count < 1:
        raise ValueError("Pick count must be 1 or greater")

    if question_points < 0:
        raise ValueError("Question points cannot be negative")

    data = {
        "quiz_groups[][name]": name.strip(),
        "quiz_groups[][pick_count]": pick_count,
        "quiz_groups[][question_points]": question_points,
    }

    if assessment_question_bank_id is not None:
        data["quiz_groups[][assessment_question_bank_id]"] = assessment_question_bank_id

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/groups",
        data=data,
    )
    return response.json()


def update_quiz_group(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    group_id: Union[int, str],
    name: Optional[str] = None,
    pick_count: Optional[int] = None,
    question_points: Optional[int] = None,
) -> Dict:
    """
    Update a question group.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        group_id: Quiz group ID
        name: The name of the question group
        pick_count: The number of questions to randomly select for this group
        question_points: The number of points to assign to each question in the group

    Returns:
        Response dictionary containing the updated quiz group

    Raises:
        ValueError: If name is empty or pick_count/question_points are invalid
    """
    if name is not None and (not name or not name.strip()):
        raise ValueError("Quiz group name cannot be empty")

    if pick_count is not None and pick_count < 1:
        raise ValueError("Pick count must be 1 or greater")

    if question_points is not None and question_points < 0:
        raise ValueError("Question points cannot be negative")

    data = {}

    if name is not None:
        data["quiz_groups[][name]"] = name.strip()
    if pick_count is not None:
        data["quiz_groups[][pick_count]"] = pick_count
    if question_points is not None:
        data["quiz_groups[][question_points]"] = question_points

    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/groups/{group_id}",
        data=data,
    )
    return response.json()


def delete_quiz_group(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    group_id: Union[int, str],
) -> None:
    """
    Delete a question group.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        group_id: Quiz group ID

    Returns:
        None (204 No Content response)
    """
    _make_request(
        base_url,
        access_token,
        "DELETE",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/groups/{group_id}",
    )
    return None


def reorder_quiz_group_questions(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    group_id: Union[int, str],
    order: List[ReorderItem],
) -> None:
    """
    Change the order of the quiz questions within the group.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        group_id: Quiz group ID
        order: List of order items with id and type (always 'question')

    Returns:
        None (204 No Content response)

    Raises:
        ValueError: If order format is invalid
    """
    # Validate order items
    for i, item in enumerate(order):
        if not isinstance(item, dict):
            raise ValueError(f"Order item at index {i} must be a dictionary")

        if "id" not in item:
            raise ValueError(f"Order item at index {i} must include 'id'")

        if "type" in item and item["type"] != "question":
            raise ValueError(
                f"Order item type must be 'question', got '{item['type']}'"
            )

    # Format data according to API specification
    data = {}
    for i, item in enumerate(order):
        data[f"order[{i}][id]"] = item["id"]
        data[f"order[{i}][type]"] = item.get("type", "question")

    _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/groups/{group_id}/reorder",
        data=data,
    )
    return None
