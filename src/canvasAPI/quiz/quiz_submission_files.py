"""Quiz Submission Files API for Canvas MCP."""

from typing import Annotated
from pydantic import Field

from ..base import ToolProvider
from canvasAPI.quiz import quiz_submission_files


class QuizSubmissionFilesTools(ToolProvider):
    """Tools for managing Canvas quiz submission files."""

    def _register_tools(self):
        """Register all quiz submission files-related tools."""
        self.mcp.tool(self.upload_quiz_submission_file, tags={"quiz", "submission", "files"})

    async def upload_quiz_submission_file(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID"),
        ],
        name: Annotated[
            str,
            Field(description="The name of the quiz submission file"),
        ],
        on_duplicate: Annotated[
            str | None,
            Field(description="How to handle duplicate names"),
        ] = None,
    ) -> dict:
        """Upload a file for a quiz submission."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            name=name,
            on_duplicate=on_duplicate,
        )
        return quiz_submission_files.upload_quiz_submission_file(**params)