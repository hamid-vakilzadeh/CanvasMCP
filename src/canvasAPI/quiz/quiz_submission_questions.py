"""Quiz Submission Questions API for Canvas MCP."""

from typing import Annotated, Literal
from pydantic import Field

from ..base import ToolProvider
from canvasAPI.quiz import quiz_submission_questions


class QuizSubmissionQuestionsTools(ToolProvider):
    """Tools for managing Canvas quiz submission questions."""

    def _register_tools(self):
        """Register all quiz submission questions-related tools."""
        self.mcp.tool(self.get_quiz_submission_questions, tags={"quiz", "submission", "questions"})
        self.mcp.tool(self.answer_quiz_questions, tags={"quiz", "submission", "questions"})
        self.mcp.tool(self.get_formatted_answer, tags={"quiz", "submission", "questions"})
        self.mcp.tool(self.flag_question, tags={"quiz", "submission", "questions"})
        self.mcp.tool(self.unflag_question, tags={"quiz", "submission", "questions"})

    async def get_quiz_submission_questions(
        self,
        quiz_submission_id: Annotated[
            str | int,
            Field(description="The quiz submission ID"),
        ],
        include: Annotated[
            list[Literal["quiz_question"]] | None,
            Field(description="Associations to include with the quiz submission question"),
        ] = None,
    ) -> dict:
        """Get all quiz submission questions."""
        params = self._validate_params(
            quiz_submission_id=quiz_submission_id,
            include=include,
        )
        return quiz_submission_questions.get_quiz_submission_questions(**params)

    async def answer_quiz_questions(
        self,
        quiz_submission_id: Annotated[
            str | int,
            Field(description="The quiz submission ID"),
        ],
        attempt: Annotated[
            int,
            Field(description="The attempt number of the quiz submission being taken (must be latest attempt)"),
        ],
        validation_token: Annotated[
            str,
            Field(description="The unique validation token received when the Quiz Submission was created"),
        ],
        quiz_questions: Annotated[
            list[dict],
            Field(description="Set of question IDs and answer values. Format depends on question type"),
        ],
        access_code: Annotated[
            str | None,
            Field(description="Access code for the Quiz, if any"),
        ] = None,
    ) -> dict:
        """Provide or update answers to one or more quiz questions."""
        params = self._validate_params(
            quiz_submission_id=quiz_submission_id,
            attempt=attempt,
            validation_token=validation_token,
            quiz_questions=quiz_questions,
            access_code=access_code,
        )
        return quiz_submission_questions.answer_quiz_questions(**params)

    async def get_formatted_answer(
        self,
        quiz_submission_id: Annotated[
            str | int,
            Field(description="The quiz submission ID"),
        ],
        question_id: Annotated[
            str | int,
            Field(description="The question ID"),
        ],
        answer: Annotated[
            float | int,
            Field(description="The numerical answer to format"),
        ],
    ) -> dict:
        """Get a formatted student numerical answer."""
        params = self._validate_params(
            quiz_submission_id=quiz_submission_id,
            question_id=question_id,
            answer=answer,
        )
        return quiz_submission_questions.get_formatted_answer(**params)

    async def flag_question(
        self,
        quiz_submission_id: Annotated[
            str | int,
            Field(description="The quiz submission ID"),
        ],
        question_id: Annotated[
            str | int,
            Field(description="The question ID to flag"),
        ],
        attempt: Annotated[
            int,
            Field(description="The attempt number of the quiz submission being taken (must be latest attempt)"),
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
        """Flag a quiz question to indicate you want to return to it later."""
        params = self._validate_params(
            quiz_submission_id=quiz_submission_id,
            question_id=question_id,
            attempt=attempt,
            validation_token=validation_token,
            access_code=access_code,
        )
        return quiz_submission_questions.flag_question(**params)

    async def unflag_question(
        self,
        quiz_submission_id: Annotated[
            str | int,
            Field(description="The quiz submission ID"),
        ],
        question_id: Annotated[
            str | int,
            Field(description="The question ID to unflag"),
        ],
        attempt: Annotated[
            int,
            Field(description="The attempt number of the quiz submission being taken (must be latest attempt)"),
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
        """Remove the flag from a quiz question."""
        params = self._validate_params(
            quiz_submission_id=quiz_submission_id,
            question_id=question_id,
            attempt=attempt,
            validation_token=validation_token,
            access_code=access_code,
        )
        return quiz_submission_questions.unflag_question(**params)