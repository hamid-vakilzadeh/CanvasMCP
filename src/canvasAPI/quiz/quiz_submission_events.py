"""Quiz Submission Events API for Canvas MCP."""

from typing import Annotated
from pydantic import Field

from ..base import ToolProvider
from canvasAPI.quiz import quiz_submission_events


class QuizSubmissionEventsTools(ToolProvider):
    """Tools for managing Canvas quiz submission events."""

    def _register_tools(self):
        """Register all quiz submission events-related tools."""
        self.mcp.tool(self.submit_quiz_submission_events, tags={"quiz", "submission", "events"})
        self.mcp.tool(self.get_quiz_submission_events, tags={"quiz", "submission", "events"})

    async def submit_quiz_submission_events(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID"),
        ],
        submission_id: Annotated[
            str | int,
            Field(description="The quiz submission ID"),
        ],
        quiz_submission_events: Annotated[
            list[dict],
            Field(
                description="Array of submission events to be recorded. Each event should have client_timestamp, event_type, and event_data fields"
            ),
        ],
    ) -> dict:
        """Submit captured events for a quiz submission."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            submission_id=submission_id,
            quiz_submission_events=quiz_submission_events,
        )
        return quiz_submission_events.submit_quiz_submission_events(**params)

    async def get_quiz_submission_events(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID"),
        ],
        submission_id: Annotated[
            str | int,
            Field(description="The quiz submission ID"),
        ],
        attempt: Annotated[
            int | None,
            Field(
                description="The specific submission attempt to look up events for. If unspecified, the latest attempt will be used"
            ),
        ] = None,
    ) -> dict:
        """Retrieve captured events for a specific quiz submission attempt."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            submission_id=submission_id,
            attempt=attempt,
        )
        return quiz_submission_events.get_quiz_submission_events(**params)