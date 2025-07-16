"""Quiz Submissions API for Canvas MCP."""

from typing import Annotated, Literal
from pydantic import Field

from ..base import ToolProvider
from canvasAPI.quiz import quiz_submissions


class QuizSubmissionsTools(ToolProvider):
    """Tools for managing Canvas quiz submissions."""

    def _register_tools(self):
        """Register all quiz submissions-related tools."""
        self.mcp.tool(self.get_all_quiz_submissions, tags={"quiz", "submissions"})
        self.mcp.tool(self.get_current_user_quiz_submission, tags={"quiz", "submissions"})
        self.mcp.tool(self.get_quiz_submission, tags={"quiz", "submissions"})
        self.mcp.tool(self.create_quiz_submission, tags={"quiz", "submissions"})
        self.mcp.tool(self.update_quiz_submission, tags={"quiz", "submissions"})
        self.mcp.tool(self.complete_quiz_submission, tags={"quiz", "submissions"})
        self.mcp.tool(self.get_quiz_submission_time, tags={"quiz", "submissions"})

    async def get_all_quiz_submissions(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID"),
        ],
        include: Annotated[
            list[Literal["submission", "quiz", "user"]] | None,
            Field(description="Associations to include with the quiz submission"),
        ] = None,
    ) -> dict:
        """Get all quiz submissions for a quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            include=include,
        )
        return quiz_submissions.get_all_quiz_submissions(**params)

    async def get_current_user_quiz_submission(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID"),
        ],
        include: Annotated[
            list[Literal["submission", "quiz", "user"]] | None,
            Field(description="Associations to include with the quiz submission"),
        ] = None,
    ) -> dict:
        """Get the current user's quiz submission."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            include=include,
        )
        return quiz_submissions.get_current_user_quiz_submission(**params)

    async def get_quiz_submission(
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
        include: Annotated[
            list[Literal["submission", "quiz", "user"]] | None,
            Field(description="Associations to include with the quiz submission"),
        ] = None,
    ) -> dict:
        """Get a single quiz submission."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            submission_id=submission_id,
            include=include,
        )
        return quiz_submissions.get_quiz_submission(**params)

    async def create_quiz_submission(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the quiz is located"),
        ],
        quiz_id: Annotated[
            str | int,
            Field(description="The quiz ID"),
        ],
        access_code: Annotated[
            str | None,
            Field(description="Access code for the Quiz, if any"),
        ] = None,
        preview: Annotated[
            bool | None,
            Field(description="Whether this should be a preview submission (teachers only)"),
        ] = None,
    ) -> dict:
        """Create a quiz submission (start a quiz-taking session)."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            access_code=access_code,
            preview=preview,
        )
        return quiz_submissions.create_quiz_submission(**params)

    async def update_quiz_submission(
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
            int,
            Field(description="The attempt number of the quiz submission to update (must be completed)"),
        ],
        fudge_points: Annotated[
            float | None,
            Field(description="Amount of positive or negative points to fudge the total score by"),
        ] = None,
        questions: Annotated[
            dict | None,
            Field(description="Scores and comments for each question. Keys are question IDs, values are dicts with 'score' and 'comment' entries"),
        ] = None,
    ) -> dict:
        """Update student question scores and comments."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            submission_id=submission_id,
            attempt=attempt,
            fudge_points=fudge_points,
            questions=questions,
        )
        return quiz_submissions.update_quiz_submission(**params)

    async def complete_quiz_submission(
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
            int,
            Field(description="The attempt number of the quiz submission to complete (must be latest attempt)"),
        ],
        validation_token: Annotated[
            str,
            Field(description="The unique validation token received when the Quiz Submission was created"),
        ],
        access_code: Annotated[
            str | None,
            Field(description="Access code for the Quiz, if any"),
        ] = None,
    ) -> dict:
        """Complete the quiz submission (turn it in)."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            submission_id=submission_id,
            attempt=attempt,
            validation_token=validation_token,
            access_code=access_code,
        )
        return quiz_submissions.complete_quiz_submission(**params)

    async def get_quiz_submission_time(
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
    ) -> dict:
        """Get current quiz submission timing data."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            submission_id=submission_id,
        )
        return quiz_submissions.get_quiz_submission_time(**params)