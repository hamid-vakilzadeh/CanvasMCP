"""Quiz Reports API for Canvas MCP."""

from typing import Annotated, Literal, Optional
from pydantic import Field

from ..base import ToolProvider
from canvasAPI.quiz import quiz_reports


class QuizReportsTools(ToolProvider):
    """Tools for managing Canvas quiz reports."""

    def _register_tools(self):
        """Register all quiz report-related tools."""
        self.mcp.tool(self.list_quiz_reports, tags={"quiz", "reports"})
        self.mcp.tool(self.create_quiz_report, tags={"quiz", "reports"})
        self.mcp.tool(self.get_quiz_report, tags={"quiz", "reports"})
        self.mcp.tool(self.abort_quiz_report, tags={"quiz", "reports"})

    async def list_quiz_reports(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID to list reports for"),
        ],
        includes_all_versions: Annotated[
            bool | None,
            Field(
                description="Whether to retrieve reports that consider all submissions or only the most recent (defaults to false, ignored for item_analysis reports)"
            ),
        ] = None,
    ) -> list[dict]:
        """Retrieve all quiz reports for a quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            includes_all_versions=includes_all_versions,
        )
        return quiz_reports.list_quiz_reports(**params)

    async def create_quiz_report(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID to create a report for"),
        ],
        report_type: Annotated[
            Literal["student_analysis", "item_analysis"],
            Field(description="The type of report to generate"),
        ],
        includes_all_versions: Annotated[
            bool | None,
            Field(
                description="Whether the report should consider all submissions or only the most recent (defaults to false, ignored for item_analysis)"
            ),
        ] = None,
        include: Annotated[
            list[Literal["file", "progress"]] | None,
            Field(
                description="Whether to include documents for the file and/or progress objects (JSON-API only)"
            ),
        ] = None,
    ) -> dict:
        """Create and return a new report for a quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            report_type=report_type,
            includes_all_versions=includes_all_versions,
            include=include,
        )
        return quiz_reports.create_quiz_report(**params)

    async def get_quiz_report(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID that the report belongs to"),
        ],
        report_id: Annotated[
            str | int,
            Field(description="The ID of the quiz report to retrieve"),
        ],
        include: Annotated[
            list[Literal["file", "progress"]] | None,
            Field(
                description="Whether to include documents for the file and/or progress objects (JSON-API only)"
            ),
        ] = None,
    ) -> dict:
        """Get data for a single quiz report."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            report_id=report_id,
            include=include,
        )
        return quiz_reports.get_quiz_report(**params)

    async def abort_quiz_report(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID that the report belongs to"),
        ],
        report_id: Annotated[
            str | int,
            Field(description="The ID of the quiz report to abort or remove"),
        ],
    ) -> dict:
        """Abort the generation of a report or remove a previously generated one."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            report_id=report_id,
        )
        return quiz_reports.abort_quiz_report(**params)