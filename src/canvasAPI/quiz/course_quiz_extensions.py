from typing import List, Dict, Union, Optional, TypedDict
from ..base import CanvasAPIBase


class QuizExtension(TypedDict, total=False):
    """Quiz extension object for Canvas API."""

    user_id: int
    extra_attempts: Optional[int]
    extra_time: Optional[int]
    manually_unlocked: Optional[bool]
    extend_from_now: Optional[int]
    extend_from_end_at: Optional[int]


class CourseQuizExtensionsAPI(CanvasAPIBase):
    """Canvas LMS Course Quiz Extensions API client for managing student quiz extensions."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Course Quiz Extensions API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def set_quiz_extensions(
        self,
        course_id: Union[int, str],
        quiz_extensions: List[QuizExtension],
    ) -> Dict:
        """
        Set extensions for student quiz submissions.

        Args:
            course_id: Course ID
            quiz_extensions: List of quiz extension objects

        Returns:
            Dictionary containing list of CourseQuizExtension objects

        Raises:
            ValueError: If quiz_extensions is invalid or contains invalid extension objects

        Example:
            extensions = [
                {
                    "user_id": 3,
                    "extra_attempts": 2,
                    "extra_time": 20,
                    "manually_unlocked": True
                },
                {
                    "user_id": 2,
                    "extend_from_now": 60
                }
            ]
            result = api.set_quiz_extensions(123, extensions)

        Note:
            - extra_attempts is limited to 1000 or less
            - extra_time is limited to 10080 minutes (1 week)
            - extend_from_now is limited to 1440 minutes (24 hours)
            - extend_from_end_at is limited to 1440 minutes (24 hours)
            - extend_from_now and extend_from_end_at are mutually exclusive
        """
        if not quiz_extensions:
            raise ValueError("Quiz extensions list cannot be empty")

        # Validate each quiz extension object
        for i, extension in enumerate(quiz_extensions):
            if not isinstance(extension, dict):
                raise ValueError(f"Extension at index {i} must be a dictionary")

            # Validate required user_id
            if "user_id" not in extension:
                raise ValueError(f"Extension at index {i} must include 'user_id'")

            user_id = extension["user_id"]
            if not isinstance(user_id, int) or user_id <= 0:
                raise ValueError(
                    f"Extension at index {i}: 'user_id' must be a positive integer"
                )

            # Validate extra_attempts limit (1000 max)
            if "extra_attempts" in extension:
                extra_attempts = extension["extra_attempts"]
                if not isinstance(extra_attempts, int) or extra_attempts < 0:
                    raise ValueError(
                        f"Extension at index {i}: 'extra_attempts' must be a non-negative integer"
                    )
                if extra_attempts > 1000:
                    raise ValueError(
                        f"Extension at index {i}: 'extra_attempts' cannot exceed 1000"
                    )

            # Validate extra_time limit (10080 minutes = 1 week max)
            if "extra_time" in extension:
                extra_time = extension["extra_time"]
                if not isinstance(extra_time, int) or extra_time < 0:
                    raise ValueError(
                        f"Extension at index {i}: 'extra_time' must be a non-negative integer"
                    )
                if extra_time > 10080:
                    raise ValueError(
                        f"Extension at index {i}: 'extra_time' cannot exceed 10080 minutes (1 week)"
                    )

            # Validate manually_unlocked
            if "manually_unlocked" in extension:
                manually_unlocked = extension["manually_unlocked"]
                if not isinstance(manually_unlocked, bool):
                    raise ValueError(
                        f"Extension at index {i}: 'manually_unlocked' must be a boolean"
                    )

            # Validate extend_from_now limit (1440 minutes = 24 hours max)
            if "extend_from_now" in extension:
                extend_from_now = extension["extend_from_now"]
                if not isinstance(extend_from_now, int) or extend_from_now < 0:
                    raise ValueError(
                        f"Extension at index {i}: 'extend_from_now' must be a non-negative integer"
                    )
                if extend_from_now > 1440:
                    raise ValueError(
                        f"Extension at index {i}: 'extend_from_now' cannot exceed 1440 minutes (24 hours)"
                    )

            # Validate extend_from_end_at limit (1440 minutes = 24 hours max)
            if "extend_from_end_at" in extension:
                extend_from_end_at = extension["extend_from_end_at"]
                if not isinstance(extend_from_end_at, int) or extend_from_end_at < 0:
                    raise ValueError(
                        f"Extension at index {i}: 'extend_from_end_at' must be a non-negative integer"
                    )
                if extend_from_end_at > 1440:
                    raise ValueError(
                        f"Extension at index {i}: 'extend_from_end_at' cannot exceed 1440 minutes (24 hours)"
                    )

            # Validate mutual exclusivity of extend_from_now and extend_from_end_at
            if "extend_from_now" in extension and "extend_from_end_at" in extension:
                raise ValueError(
                    f"Extension at index {i}: 'extend_from_now' and 'extend_from_end_at' are mutually exclusive"
                )

            # Validate that at least one extension parameter is provided
            extension_params = [
                "extra_attempts",
                "extra_time",
                "manually_unlocked",
                "extend_from_now",
                "extend_from_end_at",
            ]
            if not any(param in extension for param in extension_params):
                raise ValueError(
                    f"Extension at index {i}: must include at least one extension parameter: {', '.join(extension_params)}"
                )

        # Format data for Canvas API
        json_data = {"quiz_extensions": quiz_extensions}

        response = self._make_request(
            "POST",
            f"/api/v1/courses/{course_id}/quiz_extensions",
            json_data=json_data,
        )
        return response.json()

    def set_single_student_quiz_extension(
        self,
        course_id: Union[int, str],
        user_id: int,
        extra_attempts: Optional[int] = None,
        extra_time: Optional[int] = None,
        manually_unlocked: Optional[bool] = None,
        extend_from_now: Optional[int] = None,
        extend_from_end_at: Optional[int] = None,
    ) -> Dict:
        """
        Set quiz extension for a single student.

        Args:
            course_id: Course ID
            user_id: Student user ID
            extra_attempts: Number of extra attempts (max 1000)
            extra_time: Extra time in minutes (max 10080 = 1 week)
            manually_unlocked: Allow student to take quiz even if locked
            extend_from_now: Minutes to extend from current time (max 1440 = 24 hours)
            extend_from_end_at: Minutes to extend from quiz end time (max 1440 = 24 hours)

        Returns:
            Dictionary containing list of CourseQuizExtension objects

        Raises:
            ValueError: If parameters are invalid or mutually exclusive options are used

        Example:
            # Extend with extra attempts and time
            result = api.set_single_quiz_extension(123, 456, extra_attempts=2, extra_time=30)

            # Extend from current time
            result = api.set_single_quiz_extension(123, 456, extend_from_now=60)

        Note:
            extend_from_now and extend_from_end_at are mutually exclusive.
        """
        # Validate that at least one extension parameter is provided
        extension_params = [
            extra_attempts,
            extra_time,
            manually_unlocked,
            extend_from_now,
            extend_from_end_at,
        ]
        if all(param is None for param in extension_params):
            raise ValueError("At least one extension parameter must be provided")

        # Build extension object
        extension = {"user_id": user_id}

        if extra_attempts is not None:
            extension["extra_attempts"] = extra_attempts
        if extra_time is not None:
            extension["extra_time"] = extra_time
        if manually_unlocked is not None:
            extension["manually_unlocked"] = manually_unlocked
        if extend_from_now is not None:
            extension["extend_from_now"] = extend_from_now
        if extend_from_end_at is not None:
            extension["extend_from_end_at"] = extend_from_end_at

        return self.set_quiz_extensions(course_id, [extension])


# Convenience instance using environment variables
course_quiz_extensions = CourseQuizExtensionsAPI()
