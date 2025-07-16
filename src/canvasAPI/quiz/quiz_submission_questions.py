from typing import List, Dict, Union, Optional, TypedDict, Any, Literal
from ..base import CanvasAPIBase


class QuizQuestionAnswer(TypedDict, total=False):
    id: Union[int, str]
    answer: Any


class QuizSubmissionQuestion(TypedDict, total=False):
    id: int
    flagged: bool
    answer: Any
    answers: Optional[List[Dict[str, Any]]]


class FormattedAnswerResponse(TypedDict):
    formatted_answer: float


class QuizSubmissionQuestionsAPI(CanvasAPIBase):
    """Canvas LMS Quiz Submission Questions API client for answering and flagging questions in a quiz-taking session."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas Quiz Submission Questions API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def get_quiz_submission_questions(
        self,
        quiz_submission_id: Union[int, str],
        include: Optional[List[Literal["quiz_question"]]] = None,
    ) -> List[QuizSubmissionQuestion]:
        """
        Get all quiz submission questions.

        Get a list of all the question records for this quiz submission.

        Args:
            quiz_submission_id: Quiz submission ID
            include: Associations to include with the quiz submission question.
                   Allowed values: ["quiz_question"]

        Returns:
            List of quiz submission question dictionaries containing:
            - id: The ID of the QuizQuestion this answer is for
            - flagged: Whether this question is flagged
            - answer: The provided answer (if any) for this question
            - answers: The possible answers for this question when necessary
        """
        params = {}
        if include:
            # Validate include values
            valid_include_values = {"quiz_question"}
            for value in include:
                if value not in valid_include_values:
                    raise ValueError(
                        f"Invalid include value '{value}'. "
                        f"Allowed values: {', '.join(sorted(valid_include_values))}"
                    )
            params["include[]"] = include

        response = self._make_request(
            "GET",
            f"/api/v1/quiz_submissions/{quiz_submission_id}/questions",
            params=params,
        )
        result = response.json()
        return result.get("quiz_submission_questions", [])

    def answer_questions(
        self,
        quiz_submission_id: Union[int, str],
        attempt: int,
        validation_token: str,
        quiz_questions: List[QuizQuestionAnswer],
        access_code: Optional[str] = None,
    ) -> List[QuizSubmissionQuestion]:
        """
        Answer questions.

        Provide or update an answer to one or more QuizQuestions.

        Args:
            quiz_submission_id: Quiz submission ID
            attempt: The attempt number of the quiz submission being taken.
                    Note that this must be the latest attempt index, as questions
                    for earlier attempts cannot be modified.
            validation_token: The unique validation token you received when the Quiz Submission was created
            quiz_questions: List of question IDs and answer values. Each question should contain:
                          - id: The question ID
                          - answer: The answer value (format depends on question type)
            access_code: Access code for the Quiz, if any

        Returns:
            List of quiz submission question dictionaries

        Raises:
            ValueError: If quiz_questions is empty or validation fails

        Note:
            See the API documentation appendix for the accepted answer formats for each question type:
            - Essay Questions: String text
            - Fill In Multiple Blanks: Dict mapping variables to answer strings
            - Fill In The Blank: String text
            - Formula Questions: Decimal number
            - Matching Questions: List of dicts with answer_id and match_id
            - Multiple Choice: Integer answer ID
            - Multiple Dropdowns: Dict mapping variables to answer IDs
            - Multiple Answers: List of integer answer IDs
            - Numerical Questions: Decimal number
            - True/False: Integer answer ID
        """
        if not quiz_questions:
            raise ValueError("quiz_questions cannot be empty")

        # Validate question structure
        for i, question in enumerate(quiz_questions):
            if "id" not in question:
                raise ValueError(f"Question at index {i} must have an 'id'")
            if "answer" not in question:
                raise ValueError(f"Question at index {i} must have an 'answer'")

        data = {
            "attempt": attempt,
            "validation_token": validation_token,
        }

        if access_code is not None:
            data["access_code"] = access_code

        # Build quiz_questions data
        for i, question in enumerate(quiz_questions):
            data[f"quiz_questions[{i}][id]"] = question["id"]
            data[f"quiz_questions[{i}][answer]"] = question["answer"]

        response = self._make_request(
            "POST",
            f"/api/v1/quiz_submissions/{quiz_submission_id}/questions",
            data=data,
        )
        return response.json()

    def get_formatted_answer(
        self,
        quiz_submission_id: Union[int, str],
        question_id: Union[int, str],
        answer: Union[int, float, str],
    ) -> FormattedAnswerResponse:
        """
        Get a formatted student numerical answer.

        Matches the intended behavior of the UI when a numerical answer is entered
        and returns the resulting formatted number.

        Args:
            quiz_submission_id: Quiz submission ID
            question_id: Question ID
            answer: The numerical answer to format

        Returns:
            Dictionary containing the formatted answer:
            - formatted_answer: The formatted numerical value
        """
        params = {"answer": answer}

        response = self._make_request(
            "GET",
            f"/api/v1/quiz_submissions/{quiz_submission_id}/questions/{question_id}/formatted_answer",
            params=params,
        )
        return response.json()

    def flag_question(
        self,
        quiz_submission_id: Union[int, str],
        question_id: Union[int, str],
        attempt: int,
        validation_token: str,
        access_code: Optional[str] = None,
    ) -> None:
        """
        Flag a question.

        Set a flag on a quiz question to indicate that you want to return to it later.

        Args:
            quiz_submission_id: Quiz submission ID
            question_id: Question ID
            attempt: The attempt number of the quiz submission being taken.
                    Note that this must be the latest attempt index, as questions
                    for earlier attempts cannot be modified.
            validation_token: The unique validation token you received when the Quiz Submission was created
            access_code: Access code for the Quiz, if any
        """
        data = {
            "attempt": attempt,
            "validation_token": validation_token,
        }

        if access_code is not None:
            data["access_code"] = access_code

        self._make_request(
            "PUT",
            f"/api/v1/quiz_submissions/{quiz_submission_id}/questions/{question_id}/flag",
            data=data,
        )

    def unflag_question(
        self,
        quiz_submission_id: Union[int, str],
        question_id: Union[int, str],
        attempt: int,
        validation_token: str,
        access_code: Optional[str] = None,
    ) -> None:
        """
        Unflag a question.

        Remove the flag that you previously set on a quiz question after you've returned to it.

        Args:
            quiz_submission_id: Quiz submission ID
            question_id: Question ID
            attempt: The attempt number of the quiz submission being taken.
                    Note that this must be the latest attempt index, as questions
                    for earlier attempts cannot be modified.
            validation_token: The unique validation token you received when the Quiz Submission was created
            access_code: Access code for the Quiz, if any
        """
        data = {
            "attempt": attempt,
            "validation_token": validation_token,
        }

        if access_code is not None:
            data["access_code"] = access_code

        self._make_request(
            "PUT",
            f"/api/v1/quiz_submissions/{quiz_submission_id}/questions/{question_id}/unflag",
            data=data,
        )


# Convenience instance using environment variables
quiz_submission_questions = QuizSubmissionQuestionsAPI()
