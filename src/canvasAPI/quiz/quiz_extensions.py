"""Quiz Extensions API for Canvas MCP."""

from typing import Annotated, Optional
from pydantic import Field

from ..base import ToolProvider
from canvasAPI.quiz.course_quiz_extensions import course_quiz_extensions


class QuizExtensionsTools(ToolProvider):
    """Tools for managing Canvas quiz extensions."""

    def _register_tools(self):
        """Register all quiz extension-related tools."""
        self.mcp.tool(self.set_quiz_extensions, tags={"quiz", "extensions"})

    async def set_quiz_extensions(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID to set extensions for"),
        ],
        user_id: Annotated[
            int,
            Field(description="The ID of the user to add quiz extensions for"),
        ],
        extra_attempts: Annotated[
            int | None,
            Field(
                description="Number of times the student is allowed to re-take the quiz over the multiple-attempt limit (max 1000)"
            ),
        ] = None,
        extra_time: Annotated[
            int | None,
            Field(
                description="The number of extra minutes to allow for all attempts (max 10080 minutes = 1 week)"
            ),
        ] = None,
        manually_unlocked: Annotated[
            bool | None,
            Field(
                description="Allow the student to take the quiz even if it's locked for everyone else"
            ),
        ] = None,
        extend_from_now: Annotated[
            int | None,
            Field(
                description="The number of minutes to extend the quiz from the current time (max 1440 minutes = 24 hours, mutually exclusive with extend_from_end_at)"
            ),
        ] = None,
        extend_from_end_at: Annotated[
            int | None,
            Field(
                description="The number of minutes to extend the quiz beyond the quiz's current ending time (max 1440 minutes = 24 hours, mutually exclusive with extend_from_now)"
            ),
        ] = None,
    ) -> dict:
        """Set extensions for a student's quiz submission."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            user_id=user_id,
            extra_attempts=extra_attempts,
            extra_time=extra_time,
            manually_unlocked=manually_unlocked,
            extend_from_now=extend_from_now,
            extend_from_end_at=extend_from_end_at,
        )
        return course_quiz_extensions.set_single_student_quiz_extension(**params)