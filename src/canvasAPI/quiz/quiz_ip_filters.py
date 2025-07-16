from typing import List, Union, TypedDict
from ..base import CanvasAPIBase


class QuizIPFilter(TypedDict):
    name: str
    account: str
    filter: str


class QuizIPFiltersAPI(CanvasAPIBase):
    """Canvas LMS Quiz IP Filters API client for accessing quiz IP filters."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas Quiz IP Filters API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def get_quiz_ip_filters(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
    ) -> List[QuizIPFilter]:
        """
        Get available quiz IP filters.

        Get a list of available IP filters for this Quiz.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID

        Returns:
            List of quiz IP filter dictionaries containing:
            - name: A unique name for the filter
            - account: Name of the Account (or Quiz) the IP filter is defined in
            - filter: An IP address (or range mask) this filter embodies
        """
        response = self._make_request(
            "GET", f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/ip_filters"
        )
        result = response.json()
        return result.get("quiz_ip_filters", [])


# Convenience instance using environment variables
quiz_ip_filters = QuizIPFiltersAPI()
