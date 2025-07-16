from typing import List, Dict, Union, Optional, TypedDict, Any
from ..base import CanvasAPIBase


class QuizSubmissionEventInput(TypedDict, total=False):
    client_timestamp: str
    event_type: str
    event_data: Optional[Dict[str, Any]]


class QuizSubmissionEvent(TypedDict, total=False):
    id: Optional[str]
    created_at: str
    event_type: str
    event_data: Optional[Dict[str, Any]]


class QuizSubmissionEventsAPI(CanvasAPIBase):
    """Canvas LMS Quiz Submission Events API client for managing quiz submission events."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas Quiz Submission Events API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def submit_quiz_submission_events(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        submission_id: Union[int, str],
        quiz_submission_events: List[QuizSubmissionEventInput],
    ) -> None:
        """
        Submit captured events.

        Store a set of events which were captured during a quiz taking session.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            submission_id: Quiz submission ID
            quiz_submission_events: List of submission events to be recorded. Each event should contain:
                - client_timestamp: A timestamp record of when the event occurred
                - event_type: The type of event being sent (e.g., "question_answered", "question_flagged")
                - event_data: Custom contextual data for the specific event type (optional)

        Raises:
            ValueError: If quiz_submission_events is empty
        """
        if not quiz_submission_events:
            raise ValueError("quiz_submission_events cannot be empty")

        # Validate event structure
        for i, event in enumerate(quiz_submission_events):
            if "client_timestamp" not in event:
                raise ValueError(f"Event at index {i} must have a 'client_timestamp'")
            if "event_type" not in event:
                raise ValueError(f"Event at index {i} must have an 'event_type'")

        # Build request data
        data = {}
        for i, event in enumerate(quiz_submission_events):
            data[f"quiz_submission_events[{i}][client_timestamp]"] = event[
                "client_timestamp"
            ]
            data[f"quiz_submission_events[{i}][event_type]"] = event["event_type"]

            if "event_data" in event and event["event_data"] is not None:
                # Handle nested event_data structure
                event_data = event["event_data"]
                for key, value in event_data.items():
                    data[f"quiz_submission_events[{i}][event_data][{key}]"] = value

        self._make_request(
            "POST",
            f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/{submission_id}/events",
            data=data,
        )

    def get_quiz_submission_events(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        submission_id: Union[int, str],
        attempt: Optional[int] = None,
    ) -> List[QuizSubmissionEvent]:
        """
        Retrieve captured events.

        Retrieve the set of events captured during a specific submission attempt.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            submission_id: Quiz submission ID
            attempt: The specific submission attempt to look up the events for.
                    If unspecified, the latest attempt will be used.

        Returns:
            List of quiz submission event dictionaries containing:
            - id: Unique identifier for the event
            - created_at: Timestamp record of creation time
            - event_type: The type of event (e.g., "page_blurred", "page_focused")
            - event_data: Custom contextual data for the specific event type
        """
        params = {}
        if attempt is not None:
            params["attempt"] = attempt

        response = self._make_request(
            "GET",
            f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/{submission_id}/events",
            params=params,
        )
        result = response.json()
        return result.get("quiz_submission_events", [])


# Convenience instance using environment variables
quiz_submission_events = QuizSubmissionEventsAPI()
