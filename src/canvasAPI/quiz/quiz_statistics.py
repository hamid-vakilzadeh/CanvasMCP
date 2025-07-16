"""Quiz Statistics API for Canvas MCP."""

from typing import Annotated
from pydantic import Field

from ..base import ToolProvider
from canvasAPI.quiz import quiz_statistics


class QuizStatisticsTools(ToolProvider):
    """Tools for managing Canvas quiz statistics."""

    def _register_tools(self):
        """Register all quiz statistics-related tools."""
        self.mcp.tool(self.get_quiz_statistics, tags={"quiz", "statistics"})

    async def get_quiz_statistics(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID to get statistics for"),
        ],
        all_versions: Annotated[
            bool | None,
            Field(
                description="Whether the statistics report should include all submission attempts"
            ),
        ] = None,
    ) -> dict:
        """Fetch the latest quiz statistics for a quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            all_versions=all_versions,
        )
        return quiz_statistics.get_quiz_statistics(**params)