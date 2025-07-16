from typing import Dict, Union, List, TypedDict, Literal, Any
from ..base import CanvasAPIBase


class JSONAPIPagination(TypedDict, total=False):
    per_page: int
    page: int
    template: str
    page_count: int
    count: int


class QuizSubmissionUserListMeta(TypedDict):
    pagination: JSONAPIPagination


class QuizSubmissionUserList(TypedDict):
    meta: QuizSubmissionUserListMeta
    users: List[Dict[str, Any]]


class QuizUserConversation(TypedDict):
    body: str
    recipients: Literal["submitted", "unsubmitted"]
    subject: str


class QuizSubmissionUserListAPI(CanvasAPIBase):
    """Canvas LMS Quiz Submission User List API client for managing users who have or haven't submitted for a quiz."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas Quiz Submission User List API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def send_message_to_users(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        body: str,
        recipients: Literal["submitted", "unsubmitted"],
        subject: str,
    ) -> None:
        """
        Send a message to unsubmitted or submitted users for the quiz.

        Send a message to users who have either submitted or not submitted the quiz.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            body: Message body of the conversation to be created
            recipients: Who to send the message to ("submitted" or "unsubmitted")
            subject: Subject of the new Conversation created

        Raises:
            ValueError: If recipients value is invalid
        """
        # Validate recipients
        valid_recipients = {"submitted", "unsubmitted"}
        if recipients not in valid_recipients:
            raise ValueError(
                f"Invalid recipients '{recipients}'. "
                f"Allowed values: {', '.join(sorted(valid_recipients))}"
            )

        data = {
            "conversations[body]": body,
            "conversations[recipients]": recipients,
            "conversations[subject]": subject,
        }

        self._make_request(
            "POST",
            f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submission_users/message",
            data=data,
        )


# Convenience instance using environment variables
quiz_submission_user_list = QuizSubmissionUserListAPI()
