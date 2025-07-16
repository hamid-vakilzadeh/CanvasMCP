"""Quiz Submission User List API for Canvas MCP."""

from typing import Annotated, Literal
from pydantic import Field

from ..base import ToolProvider
from canvasAPI.quiz import quiz_submission_user_list


class QuizSubmissionUserListTools(ToolProvider):
    """Tools for managing Canvas quiz submission user lists."""

    def _register_tools(self):
        """Register all quiz submission user list-related tools."""
        self.mcp.tool(self.send_message_to_quiz_users, tags={"quiz", "submission", "users", "message"})

    async def send_message_to_quiz_users(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID"),
        ],
        body: Annotated[
            str,
            Field(description="Message body of the conversation to be created"),
        ],
        recipients: Annotated[
            Literal["submitted", "unsubmitted"],
            Field(description="Who to send the message to: 'submitted' or 'unsubmitted' users"),
        ],
        subject: Annotated[
            str,
            Field(description="Subject of the new conversation created"),
        ],
    ) -> dict:
        """Send a message to submitted or unsubmitted users for the quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            body=body,
            recipients=recipients,
            subject=subject,
        )
        return quiz_submission_user_list.send_message_to_quiz_users(**params)