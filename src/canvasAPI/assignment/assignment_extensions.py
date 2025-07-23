from typing import List, Dict, Union, TypedDict
from ..base import _make_request


class AssignmentExtension(TypedDict, total=False):
    "Assignment Extension Object"

    assignment_id: int
    user_id: int
    extra_attempts: int


class AssignmentExtensions(Dict):
    "Response of the AssignmentExtensionsAPI"

    assignment_extensions: AssignmentExtension


def set_assignment_extensions(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    assignment_id: Union[int, str],
    extensions: List[Dict[str, int]],
) -> Dict:
    """
    Set extensions for student assignment submissions.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        assignment_id: Assignment ID
        extensions: List of extension objects with 'user_id' and 'extra_attempts' keys

    Returns:
        Dictionary containing list of AssignmentExtension objects

    Raises:
        ValueError: If extensions list is empty or contains invalid extension objects
        requests.exceptions.RequestException: For HTTP errors (403 Forbidden, 400 Bad Request)

    Example:
        extensions = [
            {"user_id": 3, "extra_attempts": 2},
            {"user_id": 2, "extra_attempts": 1}
        ]
        result = set_assignment_extensions(base_url, access_token, 123, 456, extensions)
    """
    if not extensions:
        raise ValueError("Extensions list cannot be empty")

    # Validate each extension object
    for i, extension in enumerate(extensions):
        if not isinstance(extension, dict):
            raise ValueError(f"Extension at index {i} must be a dictionary")

        if "user_id" not in extension:
            raise ValueError(f"Extension at index {i} must include 'user_id'")

        if "extra_attempts" not in extension:
            raise ValueError(
                f"Extension at index {i} must include 'extra_attempts'"
            )

        if not isinstance(extension["user_id"], int) or extension["user_id"] <= 0:
            raise ValueError(
                f"Extension at index {i}: 'user_id' must be a positive integer"
            )

        if (
            not isinstance(extension["extra_attempts"], int)
            or extension["extra_attempts"] < 0
        ):
            raise ValueError(
                f"Extension at index {i}: 'extra_attempts' must be a non-negative integer"
            )

    # Format data for Canvas API
    json_data = {"assignment_extensions": extensions}

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/assignments/{assignment_id}/extensions",
        json_data=json_data,
    )
    return response.json()


def set_single_student_assignment_extension(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    assignment_id: Union[int, str],
    user_id: int,
    extra_attempts: int,
) -> Dict:
    """
    Set extension for a single student assignment submission.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        assignment_id: Assignment ID
        user_id: Student user ID
        extra_attempts: Number of extra attempts to allow

    Returns:
        Dictionary containing list of AssignmentExtension objects

    Raises:
        ValueError: If user_id or extra_attempts are invalid
        requests.exceptions.RequestException: For HTTP errors

    Example:
        result = set_single_student_assignment_extension(base_url, access_token, 123, 456, 789, 2)
    """
    extension = {"user_id": user_id, "extra_attempts": extra_attempts}
    return set_assignment_extensions(base_url, access_token, course_id, assignment_id, [extension])
