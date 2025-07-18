from typing import List, Dict, Union, Literal, Optional
from datetime import datetime
from ..base import CanvasAPIBase


class QuizzesAPI(CanvasAPIBase):
    """Canvas LMS Quizzes API client with reusable methods for all quiz endpoints."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas Quizzes API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    # Quiz Listing Methods

    def list_quizzes(
        self,
        course_id: Union[int, str],
        search_term: str = None,
        all_pages: bool = False,
    ) -> List[Dict]:
        """
        List quizzes in a course.

        Args:
            course_id: Course ID
            search_term: The partial title of the quizzes to match and return
            all_pages: If True, fetch all pages automatically. If False, return only first page

        Returns:
            List of quiz dictionaries
        """
        params = {}
        if search_term:
            params["search_term"] = search_term

        if all_pages:
            return self._get_all_pages("GET", f"/api/v1/courses/{course_id}/quizzes", params=params)
        else:
            response = self._make_request("GET", f"/api/v1/courses/{course_id}/quizzes", params=params)
            return response.json()

    def get_quiz(self, course_id: Union[int, str], quiz_id: Union[int, str]) -> Dict:
        """
        Get a single quiz.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID

        Returns:
            Quiz dictionary
        """
        response = self._make_request("GET", f"/api/v1/courses/{course_id}/quizzes/{quiz_id}")
        return response.json()

    # Quiz Management Methods

    def create_quiz(
        self,
        course_id: Union[int, str],
        title: str,
        description: str = None,
        quiz_type: Literal["practice_quiz", "assignment", "graded_survey", "survey"] = "assignment",
        assignment_group_id: int = None,
        time_limit: int = None,
        shuffle_answers: bool = False,
        hide_results: Optional[Literal["always", "until_after_last_attempt"]] = None,
        show_correct_answers: bool = True,
        show_correct_answers_last_attempt: bool = False,
        show_correct_answers_at: datetime = None,
        hide_correct_answers_at: datetime = None,
        allowed_attempts: int = 1,
        scoring_policy: Literal["keep_highest", "keep_latest"] = "keep_highest",
        one_question_at_a_time: bool = False,
        cant_go_back: bool = False,
        access_code: str = None,
        ip_filter: str = None,
        due_at: datetime = None,
        lock_at: datetime = None,
        unlock_at: datetime = None,
        published: bool = True,
        one_time_results: bool = False,
        only_visible_to_overrides: bool = False,
    ) -> Dict:
        """
        Create a new quiz for this course.

        Args:
            course_id: Course ID
            title: The quiz title
            description: A description of the quiz
            quiz_type: The type of quiz (practice_quiz, assignment, graded_survey, survey)
            assignment_group_id: The assignment group id to put the assignment in
            time_limit: Time limit to take this quiz, in minutes
            shuffle_answers: If true, quiz answers for multiple choice questions will be randomized
            hide_results: Dictates whether quiz results are hidden from students
            show_correct_answers: If false, hides correct answers from students
            show_correct_answers_last_attempt: Hides correct answers until last attempt
            show_correct_answers_at: When correct answers become visible
            hide_correct_answers_at: When correct answers stop being visible
            allowed_attempts: Number of times a student is allowed to take a quiz
            scoring_policy: Scoring policy for multiple attempts
            one_question_at_a_time: If true, shows quiz to student one question at a time
            cant_go_back: If true, questions are locked after answering
            access_code: Restricts access to the quiz with a password
            ip_filter: Restricts access to the quiz to computers in a specified IP range
            due_at: The day/time the quiz is due
            lock_at: The day/time the quiz is locked for students
            unlock_at: The day/time the quiz is unlocked for students
            published: Whether the quiz should have a draft state of published or unpublished
            one_time_results: Whether students should be prevented from viewing results past first time
            only_visible_to_overrides: Whether this quiz is only visible to overrides

        Returns:
            Created quiz dictionary

        Raises:
            ValueError: If quiz_type, hide_results, or scoring_policy values are invalid
        """
        # Validate quiz_type
        valid_quiz_types = {"practice_quiz", "assignment", "graded_survey", "survey"}
        if quiz_type not in valid_quiz_types:
            raise ValueError(
                f"Invalid quiz_type '{quiz_type}'. "
                f"Allowed values: {', '.join(sorted(valid_quiz_types))}"
            )

        # Validate hide_results
        if hide_results is not None:
            valid_hide_results = {"always", "until_after_last_attempt"}
            if hide_results not in valid_hide_results:
                raise ValueError(
                    f"Invalid hide_results '{hide_results}'. "
                    f"Allowed values: {', '.join(sorted(valid_hide_results))}"
                )

        # Validate scoring_policy
        if allowed_attempts > 1:
            valid_scoring_policies = {"keep_highest", "keep_latest"}
            if scoring_policy not in valid_scoring_policies:
                raise ValueError(
                    f"Invalid scoring_policy '{scoring_policy}'. "
                    f"Allowed values: {', '.join(sorted(valid_scoring_policies))}"
                )

        data = {
            "quiz[title]": title,
            "quiz[quiz_type]": quiz_type,
            "quiz[shuffle_answers]": shuffle_answers,
            "quiz[show_correct_answers]": show_correct_answers,
            "quiz[show_correct_answers_last_attempt]": show_correct_answers_last_attempt,
            "quiz[allowed_attempts]": allowed_attempts,
            "quiz[one_question_at_a_time]": one_question_at_a_time,
            "quiz[cant_go_back]": cant_go_back,
            "quiz[published]": published,
            "quiz[one_time_results]": one_time_results,
            "quiz[only_visible_to_overrides]": only_visible_to_overrides,
        }

        if description:
            data["quiz[description]"] = description
        if assignment_group_id:
            data["quiz[assignment_group_id]"] = assignment_group_id
        if time_limit:
            data["quiz[time_limit]"] = time_limit
        if hide_results:
            data["quiz[hide_results]"] = hide_results
        if show_correct_answers_at:
            data["quiz[show_correct_answers_at]"] = show_correct_answers_at.isoformat()
        if hide_correct_answers_at:
            data["quiz[hide_correct_answers_at]"] = hide_correct_answers_at.isoformat()
        if allowed_attempts > 1:
            data["quiz[scoring_policy]"] = scoring_policy
        if access_code:
            data["quiz[access_code]"] = access_code
        if ip_filter:
            data["quiz[ip_filter]"] = ip_filter
        if due_at:
            data["quiz[due_at]"] = due_at.isoformat()
        if lock_at:
            data["quiz[lock_at]"] = lock_at.isoformat()
        if unlock_at:
            data["quiz[unlock_at]"] = unlock_at.isoformat()

        response = self._make_request("POST", f"/api/v1/courses/{course_id}/quizzes", data=data)
        return response.json()

    def update_quiz(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        title: str = None,
        description: str = None,
        quiz_type: Literal["practice_quiz", "assignment", "graded_survey", "survey"] = None,
        assignment_group_id: int = None,
        time_limit: int = None,
        shuffle_answers: bool = None,
        hide_results: Optional[Literal["always", "until_after_last_attempt"]] = None,
        show_correct_answers: bool = None,
        show_correct_answers_last_attempt: bool = None,
        show_correct_answers_at: datetime = None,
        hide_correct_answers_at: datetime = None,
        allowed_attempts: int = None,
        scoring_policy: Literal["keep_highest", "keep_latest"] = None,
        one_question_at_a_time: bool = None,
        cant_go_back: bool = None,
        access_code: str = None,
        ip_filter: str = None,
        due_at: datetime = None,
        lock_at: datetime = None,
        unlock_at: datetime = None,
        published: bool = None,
        one_time_results: bool = None,
        only_visible_to_overrides: bool = None,
        notify_of_update: bool = True,
    ) -> Dict:
        """
        Update an existing quiz.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            title: The quiz title
            description: A description of the quiz
            quiz_type: The type of quiz (practice_quiz, assignment, graded_survey, survey)
            assignment_group_id: The assignment group id to put the assignment in
            time_limit: Time limit to take this quiz, in minutes
            shuffle_answers: If true, quiz answers for multiple choice questions will be randomized
            hide_results: Dictates whether quiz results are hidden from students
            show_correct_answers: If false, hides correct answers from students
            show_correct_answers_last_attempt: Hides correct answers until last attempt
            show_correct_answers_at: When correct answers become visible
            hide_correct_answers_at: When correct answers stop being visible
            allowed_attempts: Number of times a student is allowed to take a quiz
            scoring_policy: Scoring policy for multiple attempts
            one_question_at_a_time: If true, shows quiz to student one question at a time
            cant_go_back: If true, questions are locked after answering
            access_code: Restricts access to the quiz with a password
            ip_filter: Restricts access to the quiz to computers in a specified IP range
            due_at: The day/time the quiz is due
            lock_at: The day/time the quiz is locked for students
            unlock_at: The day/time the quiz is unlocked for students
            published: Whether the quiz should have a draft state of published or unpublished
            one_time_results: Whether students should be prevented from viewing results past first time
            only_visible_to_overrides: Whether this quiz is only visible to overrides
            notify_of_update: If true, notifies users that the quiz has changed

        Returns:
            Updated quiz dictionary

        Raises:
            ValueError: If quiz_type, hide_results, or scoring_policy values are invalid
        """
        # Validate quiz_type
        if quiz_type is not None:
            valid_quiz_types = {"practice_quiz", "assignment", "graded_survey", "survey"}
            if quiz_type not in valid_quiz_types:
                raise ValueError(
                    f"Invalid quiz_type '{quiz_type}'. "
                    f"Allowed values: {', '.join(sorted(valid_quiz_types))}"
                )

        # Validate hide_results
        if hide_results is not None:
            valid_hide_results = {"always", "until_after_last_attempt"}
            if hide_results not in valid_hide_results:
                raise ValueError(
                    f"Invalid hide_results '{hide_results}'. "
                    f"Allowed values: {', '.join(sorted(valid_hide_results))}"
                )

        # Validate scoring_policy
        if scoring_policy is not None:
            valid_scoring_policies = {"keep_highest", "keep_latest"}
            if scoring_policy not in valid_scoring_policies:
                raise ValueError(
                    f"Invalid scoring_policy '{scoring_policy}'. "
                    f"Allowed values: {', '.join(sorted(valid_scoring_policies))}"
                )

        data = {"quiz[notify_of_update]": notify_of_update}

        if title is not None:
            data["quiz[title]"] = title
        if description is not None:
            data["quiz[description]"] = description
        if quiz_type is not None:
            data["quiz[quiz_type]"] = quiz_type
        if assignment_group_id is not None:
            data["quiz[assignment_group_id]"] = assignment_group_id
        if time_limit is not None:
            data["quiz[time_limit]"] = time_limit
        if shuffle_answers is not None:
            data["quiz[shuffle_answers]"] = shuffle_answers
        if hide_results is not None:
            data["quiz[hide_results]"] = hide_results
        if show_correct_answers is not None:
            data["quiz[show_correct_answers]"] = show_correct_answers
        if show_correct_answers_last_attempt is not None:
            data["quiz[show_correct_answers_last_attempt]"] = show_correct_answers_last_attempt
        if show_correct_answers_at is not None:
            data["quiz[show_correct_answers_at]"] = show_correct_answers_at.isoformat()
        if hide_correct_answers_at is not None:
            data["quiz[hide_correct_answers_at]"] = hide_correct_answers_at.isoformat()
        if allowed_attempts is not None:
            data["quiz[allowed_attempts]"] = allowed_attempts
        if scoring_policy is not None:
            data["quiz[scoring_policy]"] = scoring_policy
        if one_question_at_a_time is not None:
            data["quiz[one_question_at_a_time]"] = one_question_at_a_time
        if cant_go_back is not None:
            data["quiz[cant_go_back]"] = cant_go_back
        if access_code is not None:
            data["quiz[access_code]"] = access_code
        if ip_filter is not None:
            data["quiz[ip_filter]"] = ip_filter
        if due_at is not None:
            data["quiz[due_at]"] = due_at.isoformat()
        if lock_at is not None:
            data["quiz[lock_at]"] = lock_at.isoformat()
        if unlock_at is not None:
            data["quiz[unlock_at]"] = unlock_at.isoformat()
        if published is not None:
            data["quiz[published]"] = published
        if one_time_results is not None:
            data["quiz[one_time_results]"] = one_time_results
        if only_visible_to_overrides is not None:
            data["quiz[only_visible_to_overrides]"] = only_visible_to_overrides

        response = self._make_request("PUT", f"/api/v1/courses/{course_id}/quizzes/{quiz_id}", data=data)
        return response.json()

    def delete_quiz(self, course_id: Union[int, str], quiz_id: Union[int, str]) -> Dict:
        """
        Delete a quiz.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID

        Returns:
            Deleted quiz dictionary
        """
        response = self._make_request("DELETE", f"/api/v1/courses/{course_id}/quizzes/{quiz_id}")
        return response.json()

    # Quiz Ordering Methods

    def reorder_quiz_items(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        order: List[Dict[str, Union[int, str]]],
    ) -> None:
        """
        Change order of the quiz questions or groups within the quiz.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            order: List of dictionaries with 'id' and 'type' keys.
                   Each dict should have:
                   - id: The associated item's unique identifier
                   - type: The type of item ('question' or 'group')

        Raises:
            ValueError: If order items don't have required keys or have invalid types
        """
        # Validate order structure
        for i, item in enumerate(order):
            if not isinstance(item, dict):
                raise ValueError(f"Order item at index {i} must be a dictionary")
            
            if "id" not in item:
                raise ValueError(f"Order item at index {i} must have an 'id' key")
            
            if "type" in item:
                valid_types = {"question", "group"}
                if item["type"] not in valid_types:
                    raise ValueError(
                        f"Invalid type '{item['type']}' at index {i}. "
                        f"Allowed values: {', '.join(sorted(valid_types))}"
                    )

        data = {}
        for i, item in enumerate(order):
            data[f"order[{i}][id]"] = item["id"]
            if "type" in item:
                data[f"order[{i}][type]"] = item["type"]

        self._make_request("POST", f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/reorder", data=data)

    # Quiz Access Methods

    def validate_access_code(
        self,
        course_id: Union[int, str],
        quiz_id: Union[int, str],
        access_code: str,
    ) -> Dict:
        """
        Validate quiz access code.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            access_code: The access code being validated

        Returns:
            Dictionary with validation result
        """
        data = {"access_code": access_code}
        response = self._make_request(
            "POST", f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/validate_access_code", data=data
        )
        return response.json()


# Lazy-loaded convenience instance
def get_quizzes():
    from ..base import access_token, url
    return QuizzesAPI(access_token, url)

class _LazyQuizzesAPI:
    def __getattr__(self, name):
        return getattr(get_quizzes(), name)

quizzes = _LazyQuizzesAPI()