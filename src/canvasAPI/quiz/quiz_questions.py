from typing import List, Dict, Union, Literal, Optional
from ..base import CanvasAPIBase


class QuizQuestionsAPI(CanvasAPIBase):
    """Canvas LMS Quiz Questions API client with reusable methods for all quiz question endpoints."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas Quiz Questions API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    # Quiz Question Listing Methods

    def list_quiz_questions(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        quiz_submission_id: int = None,
        quiz_submission_attempt: int = None,
        all_pages: bool = False,
    ) -> List[Dict]:
        """
        List questions in a quiz or a submission.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            quiz_submission_id: If specified, return questions for that submission
            quiz_submission_attempt: The attempt of the submission you want questions for
            all_pages: If True, fetch all pages automatically. If False, return only first page

        Returns:
            List of quiz question dictionaries

        Raises:
            ValueError: If quiz_submission_id is provided without quiz_submission_attempt
        """
        if quiz_submission_id is not None and quiz_submission_attempt is None:
            raise ValueError(
                "quiz_submission_attempt must be specified when quiz_submission_id is provided"
            )

        params = {}
        if quiz_submission_id is not None:
            params["quiz_submission_id"] = quiz_submission_id
        if quiz_submission_attempt is not None:
            params["quiz_submission_attempt"] = quiz_submission_attempt

        endpoint = f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions"
        
        if all_pages:
            return self._get_all_pages("GET", endpoint, params=params)
        else:
            response = self._make_request("GET", endpoint, params=params)
            return response.json()

    def get_quiz_question(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        question_id: Union[int, str],
    ) -> Dict:
        """
        Get a single quiz question.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            question_id: Question ID

        Returns:
            Quiz question dictionary
        """
        endpoint = f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions/{question_id}"
        response = self._make_request("GET", endpoint)
        return response.json()

    # Quiz Question Management Methods

    def create_quiz_question(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        question_name: str = None,
        question_text: str = None,
        question_type: Literal[
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
        ] = None,
        position: int = None,
        points_possible: int = None,
        correct_comments: str = None,
        incorrect_comments: str = None,
        neutral_comments: str = None,
        text_after_answers: str = None,
        quiz_group_id: int = None,
        answers: List[Dict] = None,
    ) -> Dict:
        """
        Create a new quiz question for this quiz.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            question_name: The name of the question
            question_text: The text of the question
            question_type: The type of question
            position: The order in which the question will be displayed
            points_possible: The maximum amount of points received for answering correctly
            correct_comments: The comment to display if the student answers correctly
            incorrect_comments: The comment to display if the student answers incorrectly
            neutral_comments: The comment to display regardless of how the student answered
            text_after_answers: Text to follow answers (used in missing word questions)
            quiz_group_id: The id of the quiz group to assign the question to
            answers: List of answer dictionaries

        Returns:
            Created quiz question dictionary

        Raises:
            ValueError: If question_type is invalid
        """
        if question_type is not None:
            valid_question_types = {
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
            }
            if question_type not in valid_question_types:
                raise ValueError(
                    f"Invalid question_type '{question_type}'. "
                    f"Allowed values: {', '.join(sorted(valid_question_types))}"
                )

        data = {}
        
        if question_name is not None:
            data["question[question_name]"] = question_name
        if question_text is not None:
            data["question[question_text]"] = question_text
        if question_type is not None:
            data["question[question_type]"] = question_type
        if position is not None:
            data["question[position]"] = position
        if points_possible is not None:
            data["question[points_possible]"] = points_possible
        if correct_comments is not None:
            data["question[correct_comments]"] = correct_comments
        if incorrect_comments is not None:
            data["question[incorrect_comments]"] = incorrect_comments
        if neutral_comments is not None:
            data["question[neutral_comments]"] = neutral_comments
        if text_after_answers is not None:
            data["question[text_after_answers]"] = text_after_answers
        if quiz_group_id is not None:
            data["question[quiz_group_id]"] = quiz_group_id
        if answers is not None:
            data["question[answers]"] = answers

        endpoint = f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions"
        response = self._make_request("POST", endpoint, json_data=data)
        return response.json()

    def update_quiz_question(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        question_id: Union[int, str],
        question_name: str = None,
        question_text: str = None,
        question_type: Literal[
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
        ] = None,
        position: int = None,
        points_possible: int = None,
        correct_comments: str = None,
        incorrect_comments: str = None,
        neutral_comments: str = None,
        text_after_answers: str = None,
        quiz_group_id: int = None,
        answers: List[Dict] = None,
    ) -> Dict:
        """
        Update an existing quiz question for this quiz.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            question_id: Question ID
            question_name: The name of the question
            question_text: The text of the question
            question_type: The type of question
            position: The order in which the question will be displayed
            points_possible: The maximum amount of points received for answering correctly
            correct_comments: The comment to display if the student answers correctly
            incorrect_comments: The comment to display if the student answers incorrectly
            neutral_comments: The comment to display regardless of how the student answered
            text_after_answers: Text to follow answers (used in missing word questions)
            quiz_group_id: The id of the quiz group to assign the question to
            answers: List of answer dictionaries

        Returns:
            Updated quiz question dictionary

        Raises:
            ValueError: If question_type is invalid
        """
        if question_type is not None:
            valid_question_types = {
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
            }
            if question_type not in valid_question_types:
                raise ValueError(
                    f"Invalid question_type '{question_type}'. "
                    f"Allowed values: {', '.join(sorted(valid_question_types))}"
                )

        data = {}
        
        if question_name is not None:
            data["question[question_name]"] = question_name
        if question_text is not None:
            data["question[question_text]"] = question_text
        if question_type is not None:
            data["question[question_type]"] = question_type
        if position is not None:
            data["question[position]"] = position
        if points_possible is not None:
            data["question[points_possible]"] = points_possible
        if correct_comments is not None:
            data["question[correct_comments]"] = correct_comments
        if incorrect_comments is not None:
            data["question[incorrect_comments]"] = incorrect_comments
        if neutral_comments is not None:
            data["question[neutral_comments]"] = neutral_comments
        if text_after_answers is not None:
            data["question[text_after_answers]"] = text_after_answers
        if quiz_group_id is not None:
            data["question[quiz_group_id]"] = quiz_group_id
        if answers is not None:
            data["question[answers]"] = answers

        endpoint = f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions/{question_id}"
        response = self._make_request("PUT", endpoint, json_data=data)
        return response.json()

    def delete_quiz_question(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        question_id: Union[int, str],
    ) -> None:
        """
        Delete a quiz question.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            question_id: Question ID

        Note:
            Returns 204 No Content response code if the deletion was successful.
        """
        endpoint = f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions/{question_id}"
        self._make_request("DELETE", endpoint)

    # Helper Methods for Answer Creation

    def create_multiple_choice_answer(
        self,
        answer_text: str,
        answer_weight: int = 0,
        answer_comments: str = None,
        answer_id: int = None,
    ) -> Dict:
        """
        Create a multiple choice answer dictionary.

        Args:
            answer_text: The text of the answer
            answer_weight: Integer to determine correctness (0 = incorrect, 100 = correct)
            answer_comments: Specific contextual comments for this answer
            answer_id: The unique identifier for the answer (omit for new answers)

        Returns:
            Answer dictionary for multiple choice questions
        """
        answer = {
            "answer_text": answer_text,
            "answer_weight": answer_weight,
        }
        
        if answer_comments is not None:
            answer["answer_comments"] = answer_comments
        if answer_id is not None:
            answer["id"] = answer_id
            
        return answer

    def create_matching_answer(
        self,
        answer_match_left: str,
        answer_match_right: str,
        matching_answer_incorrect_matches: str = None,
        answer_id: int = None,
    ) -> Dict:
        """
        Create a matching answer dictionary.

        Args:
            answer_match_left: The static value displayed on the left for students to match
            answer_match_right: The correct match for the left value
            matching_answer_incorrect_matches: List of distractors, delimited by newlines
            answer_id: The unique identifier for the answer (omit for new answers)

        Returns:
            Answer dictionary for matching questions
        """
        answer = {
            "answer_match_left": answer_match_left,
            "answer_match_right": answer_match_right,
        }
        
        if matching_answer_incorrect_matches is not None:
            answer["matching_answer_incorrect_matches"] = matching_answer_incorrect_matches
        if answer_id is not None:
            answer["id"] = answer_id
            
        return answer

    def create_numerical_answer(
        self,
        numerical_answer_type: Literal["exact_answer", "range_answer", "precision_answer"],
        exact: float = None,
        margin: float = None,
        approximate: float = None,
        precision: int = None,
        start: float = None,
        end: float = None,
        answer_id: int = None,
    ) -> Dict:
        """
        Create a numerical answer dictionary.

        Args:
            numerical_answer_type: Type of numerical answer (exact_answer, range_answer, precision_answer)
            exact: Value for exact_answer type
            margin: Margin of error for exact_answer type
            approximate: Value for precision_answer type
            precision: Numerical precision for precision_answer type
            start: Start of range for range_answer type (inclusive)
            end: End of range for range_answer type (inclusive)
            answer_id: The unique identifier for the answer (omit for new answers)

        Returns:
            Answer dictionary for numerical questions

        Raises:
            ValueError: If numerical_answer_type is invalid or required fields are missing
        """
        valid_types = {"exact_answer", "range_answer", "precision_answer"}
        if numerical_answer_type not in valid_types:
            raise ValueError(
                f"Invalid numerical_answer_type '{numerical_answer_type}'. "
                f"Allowed values: {', '.join(sorted(valid_types))}"
            )

        answer = {
            "numerical_answer_type": numerical_answer_type,
        }

        if numerical_answer_type == "exact_answer":
            if exact is None:
                raise ValueError("exact value is required for exact_answer type")
            answer["exact"] = exact
            if margin is not None:
                answer["margin"] = margin
                
        elif numerical_answer_type == "range_answer":
            if start is None or end is None:
                raise ValueError("start and end values are required for range_answer type")
            answer["start"] = start
            answer["end"] = end
            
        elif numerical_answer_type == "precision_answer":
            if approximate is None or precision is None:
                raise ValueError("approximate and precision values are required for precision_answer type")
            answer["approximate"] = approximate
            answer["precision"] = precision

        if answer_id is not None:
            answer["id"] = answer_id
            
        return answer

    def create_fill_in_blank_answer(
        self,
        answer_text: str,
        blank_id: int,
        answer_weight: int = 100,
        answer_id: int = None,
    ) -> Dict:
        """
        Create a fill-in-the-blank answer dictionary.

        Args:
            answer_text: The text of the answer
            blank_id: Used in fill in multiple blank and multiple dropdowns questions
            answer_weight: Integer to determine correctness (0 = incorrect, 100 = correct)
            answer_id: The unique identifier for the answer (omit for new answers)

        Returns:
            Answer dictionary for fill-in-the-blank questions
        """
        answer = {
            "answer_text": answer_text,
            "blank_id": blank_id,
            "answer_weight": answer_weight,
        }
        
        if answer_id is not None:
            answer["id"] = answer_id
            
        return answer

    def create_missing_word_answer(
        self,
        answer_text: str,
        text_after_answers: str,
        answer_weight: int = 100,
        answer_id: int = None,
    ) -> Dict:
        """
        Create a missing word answer dictionary.

        Args:
            answer_text: The text of the answer
            text_after_answers: The text to follow the missing word
            answer_weight: Integer to determine correctness (0 = incorrect, 100 = correct)
            answer_id: The unique identifier for the answer (omit for new answers)

        Returns:
            Answer dictionary for missing word questions
        """
        answer = {
            "answer_text": answer_text,
            "text_after_answers": text_after_answers,
            "answer_weight": answer_weight,
        }
        
        if answer_id is not None:
            answer["id"] = answer_id
            
        return answer


# Convenience instance using environment variables
quiz_questions = QuizQuestionsAPI()