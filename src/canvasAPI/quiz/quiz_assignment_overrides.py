from typing import List, Dict, Union, Optional
from ..base import CanvasAPIBase


class QuizAssignmentOverridesAPI(CanvasAPIBase):
    """Canvas LMS Quiz Assignment Overrides API client for managing quiz assignment overrides."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Quiz Assignment Overrides API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def get_classic_quiz_assignment_overrides(
        self,
        course_id: Union[int, str],
        quiz_ids: Optional[List[Union[int, str]]] = None,
    ) -> Dict:
        """
        Retrieve assignment-overridden dates for Classic Quizzes.

        Args:
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

        response = self._make_request(
            "GET", f"/api/v1/courses/{course_id}/quizzes/assignment_overrides", params=params
        )
        return response.json()

    def get_new_quiz_assignment_overrides(
        self,
        course_id: Union[int, str],
        quiz_ids: Optional[List[Union[int, str]]] = None,
    ) -> Dict:
        """
        Retrieve assignment-overridden dates for New Quizzes.

        Args:
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

        response = self._make_request(
            "GET", f"/api/v1/courses/{course_id}/new_quizzes/assignment_overrides", params=params
        )
        return response.json()


# Lazy-loaded convenience instance
def get_quiz_assignment_overrides():
    from ..base import access_token, url
    return QuizAssignmentOverridesAPI(access_token, url)

class _LazyQuizAssignmentOverridesAPI:
    def __getattr__(self, name):
        return getattr(get_quiz_assignment_overrides(), name)

quiz_assignment_overrides = _LazyQuizAssignmentOverridesAPI()