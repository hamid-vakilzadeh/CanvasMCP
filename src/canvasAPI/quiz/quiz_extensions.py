from typing import List, Dict, Union, Optional, TypedDict
from ..base import _make_request


class QuizExtension(TypedDict, total=False):
    user_id: int
    extra_attempts: Optional[int]
    extra_time: Optional[int]
    manually_unlocked: Optional[bool]
    extend_from_now: Optional[int]
    extend_from_end_at: Optional[int]


def set_quiz_extensions(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    quiz_extensions: List[QuizExtension],
) -> Dict:
    """
    Set extensions for student quiz submissions.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        quiz_extensions: List of quiz extension dictionaries. Each extension can contain:
            - user_id (required): The ID of the user to add quiz extensions for
            - extra_attempts (optional): Number of extra attempts (max 1000)
            - extra_time (optional): Extra minutes for all attempts (max 10080)
            - manually_unlocked (optional): Allow student to take quiz even if locked
            - extend_from_now (optional): Minutes to extend from current time (max 1440)
            - extend_from_end_at (optional): Minutes to extend beyond quiz end time (max 1440)

    Returns:
        Dictionary containing list of quiz extensions

    Raises:
        ValueError: If validation fails for any extension parameters
    """
    # Validate quiz_extensions structure and values
    if not quiz_extensions:
        raise ValueError("quiz_extensions cannot be empty")

    for i, extension in enumerate(quiz_extensions):
        # Validate required user_id
        if "user_id" not in extension:
            raise ValueError(f"Extension at index {i} must have a 'user_id'")

        # Validate extra_attempts limit
        if "extra_attempts" in extension:
            if extension["extra_attempts"] > 1000:
                raise ValueError(
                    f"Extension at index {i}: extra_attempts cannot exceed 1000"
                )

        # Validate extra_time limit
        if "extra_time" in extension:
            if extension["extra_time"] > 10080:
                raise ValueError(
                    f"Extension at index {i}: extra_time cannot exceed 10080 minutes (1 week)"
                )

        # Validate extend_from_now limit
        if "extend_from_now" in extension:
            if extension["extend_from_now"] > 1440:
                raise ValueError(
                    f"Extension at index {i}: extend_from_now cannot exceed 1440 minutes (24 hours)"
                )

        # Validate extend_from_end_at limit
        if "extend_from_end_at" in extension:
            if extension["extend_from_end_at"] > 1440:
                raise ValueError(
                    f"Extension at index {i}: extend_from_end_at cannot exceed 1440 minutes (24 hours)"
                )

        # Validate mutual exclusivity of extend_from_now and extend_from_end_at
        if "extend_from_now" in extension and "extend_from_end_at" in extension:
            raise ValueError(
                f"Extension at index {i}: extend_from_now and extend_from_end_at are mutually exclusive"
            )

    # Build request data
    data = {}
    for i, extension in enumerate(quiz_extensions):
        data[f"quiz_extensions[{i}][user_id]"] = extension["user_id"]

        if "extra_attempts" in extension:
            data[f"quiz_extensions[{i}][extra_attempts]"] = extension["extra_attempts"]

        if "extra_time" in extension:
            data[f"quiz_extensions[{i}][extra_time]"] = extension["extra_time"]

        if "manually_unlocked" in extension:
            data[f"quiz_extensions[{i}][manually_unlocked]"] = extension[
                "manually_unlocked"
            ]

        if "extend_from_now" in extension:
            data[f"quiz_extensions[{i}][extend_from_now]"] = extension[
                "extend_from_now"
            ]

        if "extend_from_end_at" in extension:
            data[f"quiz_extensions[{i}][extend_from_end_at]"] = extension[
                "extend_from_end_at"
            ]

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/extensions",
        data=data,
    )
    return response.json()
