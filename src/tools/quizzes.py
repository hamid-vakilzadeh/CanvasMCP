"""Quiz-related tools for Canvas MCP."""

from typing import Annotated, Literal
from pydantic import Field

from .base import ToolProvider
from canvasAPI.quiz import quizzes, quiz_questions, quiz_question_groups
from tools.getToken import get_user_token


class QuizTools(ToolProvider):
    """Tools for managing Canvas quizzes."""

    def _register_tools(self):
        """Register all quiz-related tools."""
        self.mcp.tool(self.list_quizzes, tags={"quiz"})
        self.mcp.tool(self.get_quiz, tags={"quiz"})
        self.mcp.tool(self.create_quiz, tags={"quiz"})
        self.mcp.tool(self.update_quiz, tags={"quiz"})
        self.mcp.tool(self.delete_quiz, tags={"quiz"})
        self.mcp.tool(self.validate_quiz_access_code, tags={"quiz"})

    async def list_quizzes(
        self,
        course_id: Annotated[
            str | int, Field(description="The course ID to list quizzes from")
        ],
        search_term: Annotated[
            str | None,
            Field(description="The partial title of the quizzes to match and return"),
        ] = None,
    ) -> list[dict]:
        """List quizzes in a course."""
        params = self._validate_params(
            course_id=course_id,
            search_term=search_term,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quizzes.list_quizzes(**params)

    async def get_quiz(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID to get")],
    ) -> dict:
        """Get a single quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quizzes.get_quiz(**params)

    async def create_quiz(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        title: Annotated[str, Field(description="The quiz title")],
        description: Annotated[
            str | None, Field(description="A description of the quiz")
        ] = None,
        quiz_type: Annotated[
            Literal["practice_quiz", "assignment", "graded_survey", "survey"] | None,
            Field(description="The type of quiz"),
        ] = "assignment",
        assignment_group_id: Annotated[
            int | str | None,
            Field(description="The assignment group id to put the assignment in"),
        ] = None,
        time_limit: Annotated[
            int | str | None,
            Field(description="Time limit to take this quiz, in minutes"),
        ] = None,
        shuffle_answers: Annotated[
            bool | str | None,
            Field(
                description="If true, quiz answers for multiple choice questions will be randomized"
            ),
        ] = False,
        hide_results: Annotated[
            Literal["always", "until_after_last_attempt"] | None,
            Field(description="Dictates whether quiz results are hidden from students"),
        ] = None,
        show_correct_answers: Annotated[
            bool | str | None,
            Field(description="If false, hides correct answers from students"),
        ] = True,
        show_correct_answers_last_attempt: Annotated[
            bool | str | None,
            Field(description="Hides correct answers until last attempt"),
        ] = False,
        show_correct_answers_at: Annotated[
            str | None,
            Field(description="When correct answers become visible (ISO format)"),
        ] = None,
        hide_correct_answers_at: Annotated[
            str | None,
            Field(description="When correct answers stop being visible (ISO format)"),
        ] = None,
        allowed_attempts: Annotated[
            int | str | None,
            Field(description="Number of times a student is allowed to take a quiz"),
        ] = 1,
        scoring_policy: Annotated[
            Literal["keep_highest", "keep_latest"] | None,
            Field(description="Scoring policy for multiple attempts"),
        ] = "keep_highest",
        one_question_at_a_time: Annotated[
            bool | str | None,
            Field(description="If true, shows quiz to student one question at a time"),
        ] = False,
        cant_go_back: Annotated[
            bool | str | None,
            Field(description="If true, questions are locked after answering"),
        ] = False,
        access_code: Annotated[
            str | None,
            Field(description="Restricts access to the quiz with a password"),
        ] = None,
        ip_filter: Annotated[
            str | None,
            Field(
                description="Restricts access to the quiz to computers in a specified IP range"
            ),
        ] = None,
        due_at: Annotated[
            str | None,
            Field(description="The day/time the quiz is due (ISO format)"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="The day/time the quiz is locked for students (ISO format)"),
        ] = None,
        unlock_at: Annotated[
            str | None,
            Field(description="The day/time the quiz is unlocked for students (ISO format)"),
        ] = None,
        published: Annotated[
            bool | str | None,
            Field(description="Whether the quiz should be published or unpublished"),
        ] = True,
        one_time_results: Annotated[
            bool | str | None,
            Field(
                description="Whether students should be prevented from viewing results past first time"
            ),
        ] = False,
        only_visible_to_overrides: Annotated[
            bool | str | None,
            Field(description="Whether this quiz is only visible to overrides"),
        ] = False,
    ) -> dict:
        """Create a new quiz for this course."""
        params = self._validate_params(
            course_id=course_id,
            title=title,
            description=description,
            quiz_type=quiz_type,
            assignment_group_id=assignment_group_id,
            time_limit=time_limit,
            shuffle_answers=shuffle_answers,
            hide_results=hide_results,
            show_correct_answers=show_correct_answers,
            show_correct_answers_last_attempt=show_correct_answers_last_attempt,
            show_correct_answers_at=show_correct_answers_at,
            hide_correct_answers_at=hide_correct_answers_at,
            allowed_attempts=allowed_attempts,
            scoring_policy=scoring_policy,
            one_question_at_a_time=one_question_at_a_time,
            cant_go_back=cant_go_back,
            access_code=access_code,
            ip_filter=ip_filter,
            due_at=due_at,
            lock_at=lock_at,
            unlock_at=unlock_at,
            published=published,
            one_time_results=one_time_results,
            only_visible_to_overrides=only_visible_to_overrides,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quizzes.create_quiz(**params)

    async def update_quiz(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID to update")],
        title: Annotated[str | None, Field(description="The quiz title")] = None,
        description: Annotated[
            str | None, Field(description="A description of the quiz")
        ] = None,
        quiz_type: Annotated[
            Literal["practice_quiz", "assignment", "graded_survey", "survey"] | None,
            Field(description="The type of quiz"),
        ] = None,
        assignment_group_id: Annotated[
            int | str | None,
            Field(description="The assignment group id to put the assignment in"),
        ] = None,
        time_limit: Annotated[
            int | str | None,
            Field(description="Time limit to take this quiz, in minutes"),
        ] = None,
        shuffle_answers: Annotated[
            bool | str | None,
            Field(
                description="If true, quiz answers for multiple choice questions will be randomized"
            ),
        ] = None,
        hide_results: Annotated[
            Literal["always", "until_after_last_attempt"] | None,
            Field(description="Dictates whether quiz results are hidden from students"),
        ] = None,
        show_correct_answers: Annotated[
            bool | str | None,
            Field(description="If false, hides correct answers from students"),
        ] = None,
        show_correct_answers_last_attempt: Annotated[
            bool | str | None,
            Field(description="Hides correct answers until last attempt"),
        ] = None,
        show_correct_answers_at: Annotated[
            str | None,
            Field(description="When correct answers become visible (ISO format)"),
        ] = None,
        hide_correct_answers_at: Annotated[
            str | None,
            Field(description="When correct answers stop being visible (ISO format)"),
        ] = None,
        allowed_attempts: Annotated[
            int | str | None,
            Field(description="Number of times a student is allowed to take a quiz"),
        ] = None,
        scoring_policy: Annotated[
            Literal["keep_highest", "keep_latest"] | None,
            Field(description="Scoring policy for multiple attempts"),
        ] = None,
        one_question_at_a_time: Annotated[
            bool | str | None,
            Field(description="If true, shows quiz to student one question at a time"),
        ] = None,
        cant_go_back: Annotated[
            bool | str | None,
            Field(description="If true, questions are locked after answering"),
        ] = None,
        access_code: Annotated[
            str | None,
            Field(description="Restricts access to the quiz with a password"),
        ] = None,
        ip_filter: Annotated[
            str | None,
            Field(
                description="Restricts access to the quiz to computers in a specified IP range"
            ),
        ] = None,
        due_at: Annotated[
            str | None,
            Field(description="The day/time the quiz is due (ISO format)"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="The day/time the quiz is locked for students (ISO format)"),
        ] = None,
        unlock_at: Annotated[
            str | None,
            Field(description="The day/time the quiz is unlocked for students (ISO format)"),
        ] = None,
        published: Annotated[
            bool | str | None,
            Field(description="Whether the quiz should be published or unpublished"),
        ] = None,
        one_time_results: Annotated[
            bool | str | None,
            Field(
                description="Whether students should be prevented from viewing results past first time"
            ),
        ] = None,
        only_visible_to_overrides: Annotated[
            bool | str | None,
            Field(description="Whether this quiz is only visible to overrides"),
        ] = None,
        notify_of_update: Annotated[
            bool | str | None,
            Field(description="If true, notifies users that the quiz has changed"),
        ] = True,
    ) -> dict:
        """Update an existing quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            title=title,
            description=description,
            quiz_type=quiz_type,
            assignment_group_id=assignment_group_id,
            time_limit=time_limit,
            shuffle_answers=shuffle_answers,
            hide_results=hide_results,
            show_correct_answers=show_correct_answers,
            show_correct_answers_last_attempt=show_correct_answers_last_attempt,
            show_correct_answers_at=show_correct_answers_at,
            hide_correct_answers_at=hide_correct_answers_at,
            allowed_attempts=allowed_attempts,
            scoring_policy=scoring_policy,
            one_question_at_a_time=one_question_at_a_time,
            cant_go_back=cant_go_back,
            access_code=access_code,
            ip_filter=ip_filter,
            due_at=due_at,
            lock_at=lock_at,
            unlock_at=unlock_at,
            published=published,
            one_time_results=one_time_results,
            only_visible_to_overrides=only_visible_to_overrides,
            notify_of_update=notify_of_update,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quizzes.update_quiz(**params)

    async def delete_quiz(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID to delete")],
    ) -> dict:
        """Delete a quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quizzes.delete_quiz(**params)

    async def validate_quiz_access_code(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        access_code: Annotated[
            str, Field(description="The access code being validated")
        ],
    ) -> dict:
        """Validate quiz access code."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            access_code=access_code,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quizzes.validate_access_code(**params)


class QuizQuestionTools(ToolProvider):
    """Tools for managing Canvas quiz questions."""

    def _register_tools(self):
        """Register all quiz question-related tools."""
        self.mcp.tool(self.list_quiz_questions, tags={"quiz", "question"})
        self.mcp.tool(self.get_quiz_question, tags={"quiz", "question"})
        self.mcp.tool(self.create_quiz_question, tags={"quiz", "question"})
        self.mcp.tool(self.update_quiz_question, tags={"quiz", "question"})
        self.mcp.tool(self.delete_quiz_question, tags={"quiz", "question"})

    async def list_quiz_questions(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        quiz_submission_id: Annotated[
            int | str | None,
            Field(description="If specified, return questions for that submission"),
        ] = None,
        quiz_submission_attempt: Annotated[
            int | str | None,
            Field(description="The attempt of the submission you want questions for"),
        ] = None,
    ) -> list[dict]:
        """List questions in a quiz or a submission."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            quiz_submission_id=quiz_submission_id,
            quiz_submission_attempt=quiz_submission_attempt,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quiz_questions.list_quiz_questions(**params)

    async def get_quiz_question(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        question_id: Annotated[str | int, Field(description="The question ID")],
    ) -> dict:
        """Get a single quiz question."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            question_id=question_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quiz_questions.get_quiz_question(**params)

    async def create_quiz_question(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        question_name: Annotated[
            str | None, Field(description="The name of the question")
        ] = None,
        question_text: Annotated[
            str | None, Field(description="The text of the question")
        ] = None,
        question_type: Annotated[
            Literal[
                "calculated_question",
                "essay_question",
                "file_upload_question",
                "fill_in_multiple_blanks_question",
                "matching_question",
                "multiple_answers_question",
                "multiple_choice_question",
                "multiple_dropdowns_question",
                "numerical_question",
                "short_answer_question",
                "text_only_question",
                "true_false_question",
            ]
            | None,
            Field(description="The type of question"),
        ] = None,
        position: Annotated[
            int | str | None,
            Field(description="The order in which the question will be displayed"),
        ] = None,
        points_possible: Annotated[
            int | str | None,
            Field(
                description="The maximum amount of points received for answering correctly"
            ),
        ] = None,
        correct_comments: Annotated[
            str | None,
            Field(
                description="The comment to display if the student answers correctly"
            ),
        ] = None,
        incorrect_comments: Annotated[
            str | None,
            Field(
                description="The comment to display if the student answers incorrectly"
            ),
        ] = None,
        neutral_comments: Annotated[
            str | None,
            Field(
                description="The comment to display regardless of how the student answered"
            ),
        ] = None,
        text_after_answers: Annotated[
            str | None,
            Field(
                description="Text to follow answers (used in missing word questions)"
            ),
        ] = None,
        quiz_group_id: Annotated[
            int | str | None,
            Field(description="The id of the quiz group to assign the question to"),
        ] = None,
        answers: Annotated[
            list[dict] | str | None,
            Field(description="The answers"),
        ] = None,
    ) -> dict:
        """Create a new quiz question for this quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            question_name=question_name,
            question_text=question_text,
            question_type=question_type,
            position=position,
            points_possible=points_possible,
            correct_comments=correct_comments,
            incorrect_comments=incorrect_comments,
            neutral_comments=neutral_comments,
            text_after_answers=text_after_answers,
            quiz_group_id=quiz_group_id,
            answers=answers,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quiz_questions.create_quiz_question(**params)

    async def update_quiz_question(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        question_id: Annotated[str | int, Field(description="The question ID")],
        question_name: Annotated[
            str | None, Field(description="The name of the question")
        ] = None,
        question_text: Annotated[
            str | None, Field(description="The text of the question")
        ] = None,
        question_type: Annotated[
            Literal[
                "calculated_question",
                "essay_question",
                "file_upload_question",
                "fill_in_multiple_blanks_question",
                "matching_question",
                "multiple_answers_question",
                "multiple_choice_question",
                "multiple_dropdowns_question",
                "numerical_question",
                "short_answer_question",
                "text_only_question",
                "true_false_question",
            ]
            | None,
            Field(description="The type of question"),
        ] = None,
        position: Annotated[
            int | str | None,
            Field(description="The order in which the question will be displayed"),
        ] = None,
        points_possible: Annotated[
            int | str | None,
            Field(
                description="The maximum amount of points received for answering correctly"
            ),
        ] = None,
        correct_comments: Annotated[
            str | None,
            Field(
                description="The comment to display if the student answers correctly"
            ),
        ] = None,
        incorrect_comments: Annotated[
            str | None,
            Field(
                description="The comment to display if the student answers incorrectly"
            ),
        ] = None,
        neutral_comments: Annotated[
            str | None,
            Field(
                description="The comment to display regardless of how the student answered"
            ),
        ] = None,
        text_after_answers: Annotated[
            str | None,
            Field(
                description="Text to follow answers (used in missing word questions)"
            ),
        ] = None,
        quiz_group_id: Annotated[
            int | str | None,
            Field(description="The id of the quiz group to assign the question to"),
        ] = None,
        answers: Annotated[
            list[dict] | str | None,
            Field(description="The answers"),
        ] = None,
    ) -> dict:
        """Update an existing quiz question for this quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            question_id=question_id,
            question_name=question_name,
            question_text=question_text,
            question_type=question_type,
            position=position,
            points_possible=points_possible,
            correct_comments=correct_comments,
            incorrect_comments=incorrect_comments,
            neutral_comments=neutral_comments,
            text_after_answers=text_after_answers,
            quiz_group_id=quiz_group_id,
            answers=answers,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quiz_questions.update_quiz_question(**params)

    async def delete_quiz_question(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        question_id: Annotated[str | int, Field(description="The question ID")],
    ) -> dict:
        """Delete a quiz question."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            question_id=question_id,
        )
        params["base_url"], params["access_token"] = get_user_token()
        quiz_questions.delete_quiz_question(**params)
        return {"success": True, "message": "Question deleted successfully"}


class QuizQuestionGroupTools(ToolProvider):
    """Tools for managing Canvas quiz question groups."""

    def _register_tools(self):
        """Register all quiz question group-related tools."""
        self.mcp.tool(self.get_quiz_question_group, tags={"quiz", "question_group"})
        self.mcp.tool(self.create_quiz_question_group, tags={"quiz", "question_group"})
        self.mcp.tool(self.update_quiz_question_group, tags={"quiz", "question_group"})
        self.mcp.tool(self.delete_quiz_question_group, tags={"quiz", "question_group"})
        self.mcp.tool(
            self.reorder_quiz_question_group_questions, tags={"quiz", "question_group"}
        )

    async def get_quiz_question_group(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        group_id: Annotated[str | int, Field(description="The quiz question group ID")],
    ) -> dict:
        """Get a single quiz question group."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            group_id=group_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quiz_question_groups.get_quiz_group(**params)

    async def create_quiz_question_group(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        name: Annotated[str, Field(description="The name of the question group")],
        pick_count: Annotated[
            int,
            Field(
                description="The number of questions to randomly select for this group"
            ),
        ],
        question_points: Annotated[
            int,
            Field(
                description="The number of points to assign to each question in the group"
            ),
        ],
        assessment_question_bank_id: Annotated[
            int | None,
            Field(
                description="The id of the assessment question bank to pull questions from"
            ),
        ] = None,
    ) -> dict:
        """Create a new question group for a quiz."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            name=name,
            pick_count=pick_count,
            question_points=question_points,
            assessment_question_bank_id=assessment_question_bank_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quiz_question_groups.create_quiz_group(**params)

    async def update_quiz_question_group(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        group_id: Annotated[str | int, Field(description="The quiz question group ID")],
        name: Annotated[
            str | None, Field(description="The name of the question group")
        ] = None,
        pick_count: Annotated[
            int | None,
            Field(
                description="The number of questions to randomly select for this group"
            ),
        ] = None,
        question_points: Annotated[
            int | None,
            Field(
                description="The number of points to assign to each question in the group"
            ),
        ] = None,
    ) -> dict:
        """Update a question group."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            group_id=group_id,
            name=name,
            pick_count=pick_count,
            question_points=question_points,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return quiz_question_groups.update_quiz_group(**params)

    async def delete_quiz_question_group(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        group_id: Annotated[str | int, Field(description="The quiz question group ID")],
    ) -> dict:
        """Delete a question group."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            group_id=group_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        quiz_question_groups.delete_quiz_group(**params)
        return {"success": True, "message": "Question group deleted successfully"}

    async def reorder_quiz_question_group_questions(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        quiz_id: Annotated[str | int, Field(description="The quiz ID")],
        group_id: Annotated[str | int, Field(description="The quiz question group ID")],
        order: Annotated[
            list[dict],
            Field(
                description="List of order items with 'id' and 'type' (always 'question')"
            ),
        ],
    ) -> dict:
        """Change the order of quiz questions within the group."""
        params = self._validate_params(
            course_id=course_id,
            quiz_id=quiz_id,
            group_id=group_id,
            order=order,
        )
        params["base_url"], params["access_token"] = get_user_token()

        quiz_question_groups.reorder_quiz_group_questions(**params)
        return {"success": True, "message": "Questions reordered successfully"}
