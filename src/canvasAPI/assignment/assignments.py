from typing import List, Dict, Union, Literal, Optional
from datetime import datetime
from ..base import CanvasAPIBase


class AssignmentsAPI(CanvasAPIBase):
    """Canvas LMS Assignments API client for managing assignments and overrides."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Assignments API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def delete_assignment(self, course_id: Union[int, str], assignment_id: Union[int, str]) -> Dict:
        """
        Delete an assignment.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID

        Returns:
            Deleted Assignment dictionary
        """
        response = self._make_request(
            "DELETE", f"/api/v1/courses/{course_id}/assignments/{assignment_id}"
        )
        return response.json()

    def list_assignments(
        self,
        course_id: Union[int, str],
        assignment_group_id: Optional[Union[int, str]] = None,
        include: Optional[
            List[
                Literal[
                    "submission",
                    "assignment_visibility",
                    "all_dates",
                    "overrides",
                    "observed_users",
                    "can_edit",
                    "score_statistics",
                    "ab_guid",
                ]
            ]
        ] = None,
        search_term: Optional[str] = None,
        override_assignment_dates: bool = True,
        needs_grading_count_by_section: bool = False,
        bucket: Optional[
            Literal["past", "overdue", "undated", "ungraded", "unsubmitted", "upcoming", "future"]
        ] = None,
        assignment_ids: Optional[List[Union[int, str]]] = None,
        order_by: Literal["position", "name", "due_at"] = "position",
        post_to_sis: Optional[bool] = None,
        new_quizzes: Optional[bool] = None,
    ) -> List[Dict]:
        """
        List assignments for a course or assignment group.

        Args:
            course_id: Course ID
            assignment_group_id: If provided, list assignments for this specific assignment group
            include: Optional information to include with each assignment
            search_term: Partial title of assignments to match and return
            override_assignment_dates: Apply assignment overrides for each assignment
            needs_grading_count_by_section: Split up needs_grading_count by sections
            bucket: Filter assignments by due date and submission status
            assignment_ids: Return only specified assignments
            order_by: Determines the order of assignments
            post_to_sis: Return only assignments that have post_to_sis set or not set
            new_quizzes: Return only New Quizzes assignments

        Returns:
            List of Assignment dictionaries

        Raises:
            ValueError: If invalid include values, bucket, or order_by values are provided
        """
        # Validate include values
        if include is not None:
            valid_include_values = {
                "submission",
                "assignment_visibility",
                "all_dates",
                "overrides",
                "observed_users",
                "can_edit",
                "score_statistics",
                "ab_guid",
            }
            invalid_includes = [i for i in include if i not in valid_include_values]
            if invalid_includes:
                raise ValueError(
                    f"Invalid include values: {', '.join(invalid_includes)}. "
                    f"Allowed values: {', '.join(sorted(valid_include_values))}"
                )

        # Validate bucket
        if bucket is not None:
            valid_buckets = {"past", "overdue", "undated", "ungraded", "unsubmitted", "upcoming", "future"}
            if bucket not in valid_buckets:
                raise ValueError(
                    f"Invalid bucket '{bucket}'. "
                    f"Allowed values: {', '.join(sorted(valid_buckets))}"
                )

        # Validate order_by
        valid_order_by = {"position", "name", "due_at"}
        if order_by not in valid_order_by:
            raise ValueError(
                f"Invalid order_by '{order_by}'. "
                f"Allowed values: {', '.join(sorted(valid_order_by))}"
            )

        params = {}

        if include:
            params["include[]"] = include
        if search_term:
            params["search_term"] = search_term
        if override_assignment_dates is not None:
            params["override_assignment_dates"] = override_assignment_dates
        if needs_grading_count_by_section:
            params["needs_grading_count_by_section"] = needs_grading_count_by_section
        if bucket:
            params["bucket"] = bucket
        if assignment_ids:
            params["assignment_ids[]"] = assignment_ids
        if order_by != "position":  # Default is position
            params["order_by"] = order_by
        if post_to_sis is not None:
            params["post_to_sis"] = post_to_sis
        if new_quizzes is not None:
            params["new_quizzes"] = new_quizzes

        # Determine endpoint based on whether assignment_group_id is provided
        if assignment_group_id is not None:
            endpoint = f"/api/v1/courses/{course_id}/assignment_groups/{assignment_group_id}/assignments"
        else:
            endpoint = f"/api/v1/courses/{course_id}/assignments"

        response = self._make_request("GET", endpoint, params=params)
        return response.json()

    def list_assignments_for_user(
        self,
        user_id: Union[int, str],
        course_id: Union[int, str],
        **kwargs
    ) -> List[Dict]:
        """
        List assignments for a specific user if the current user has rights to view.

        Args:
            user_id: User ID
            course_id: Course ID
            **kwargs: Same arguments as list_assignments

        Returns:
            List of Assignment dictionaries
        """
        params = kwargs

        response = self._make_request(
            "GET", f"/api/v1/users/{user_id}/courses/{course_id}/assignments", params=params
        )
        return response.json()

    def duplicate_assignment(
        self,
        course_id: Union[int, str],
        assignment_id: Union[int, str],
        result_type: Optional[Literal["Quiz"]] = None,
    ) -> Dict:
        """
        Duplicate an assignment.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID to duplicate
            result_type: If "Quiz", response will be serialized into quiz format

        Returns:
            Duplicated Assignment or Quiz dictionary
        """
        params = {}
        if result_type:
            params["result_type"] = result_type

        response = self._make_request(
            "POST", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/duplicate", params=params
        )
        return response.json()

    def list_group_members(
        self,
        course_id: Union[int, str],
        assignment_id: Union[int, str],
        user_id: Union[int, str],
    ) -> List[Dict]:
        """
        List group members for a student on an assignment.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            user_id: User ID

        Returns:
            List of BasicUser dictionaries
        """
        response = self._make_request(
            "GET", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/users/{user_id}/group_members"
        )
        return response.json()

    def get_assignment(
        self,
        course_id: Union[int, str],
        assignment_id: Union[int, str],
        include: Optional[
            List[
                Literal[
                    "submission",
                    "assignment_visibility",
                    "overrides",
                    "observed_users",
                    "can_edit",
                    "score_statistics",
                    "ab_guid",
                ]
            ]
        ] = None,
        override_assignment_dates: bool = True,
        needs_grading_count_by_section: bool = False,
        all_dates: bool = False,
    ) -> Dict:
        """
        Get a single assignment.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            include: Associations to include with the assignment
            override_assignment_dates: Apply assignment overrides to the assignment
            needs_grading_count_by_section: Split up needs_grading_count by sections
            all_dates: All dates associated with the assignment

        Returns:
            Assignment dictionary

        Raises:
            ValueError: If invalid include values are provided
        """
        # Validate include values
        if include is not None:
            valid_include_values = {
                "submission",
                "assignment_visibility",
                "overrides",
                "observed_users",
                "can_edit",
                "score_statistics",
                "ab_guid",
            }
            invalid_includes = [i for i in include if i not in valid_include_values]
            if invalid_includes:
                raise ValueError(
                    f"Invalid include values: {', '.join(invalid_includes)}. "
                    f"Allowed values: {', '.join(sorted(valid_include_values))}"
                )

        params = {}

        if include:
            params["include[]"] = include
        if override_assignment_dates is not None:
            params["override_assignment_dates"] = override_assignment_dates
        if needs_grading_count_by_section:
            params["needs_grading_count_by_section"] = needs_grading_count_by_section
        if all_dates:
            params["all_dates"] = all_dates

        response = self._make_request(
            "GET", f"/api/v1/courses/{course_id}/assignments/{assignment_id}", params=params
        )
        return response.json()

    def create_assignment(
        self,
        course_id: Union[int, str],
        name: str,
        submission_types: List[
            Literal[
                "online_quiz",
                "none",
                "on_paper",
                "discussion_topic",
                "external_tool",
                "online_upload",
                "online_text_entry",
                "online_url",
                "media_recording",
                "student_annotation",
            ]
        ],
        position: Optional[int] = None,
        allowed_extensions: Optional[List[str]] = None,
        turnitin_enabled: Optional[bool] = None,
        vericite_enabled: Optional[bool] = None,
        turnitin_settings: Optional[Dict] = None,
        integration_data: Optional[str] = None,
        integration_id: Optional[str] = None,
        peer_reviews: Optional[bool] = None,
        automatic_peer_reviews: Optional[bool] = None,
        notify_of_update: Optional[bool] = None,
        group_category_id: Optional[int] = None,
        grade_group_students_individually: Optional[bool] = None,
        external_tool_tag_attributes: Optional[Dict] = None,
        points_possible: Optional[float] = None,
        grading_type: Literal["pass_fail", "percent", "letter_grade", "gpa_scale", "points", "not_graded"] = "points",
        due_at: Optional[datetime] = None,
        lock_at: Optional[datetime] = None,
        unlock_at: Optional[datetime] = None,
        description: Optional[str] = None,
        assignment_group_id: Optional[int] = None,
        assignment_overrides: Optional[List[Dict]] = None,
        only_visible_to_overrides: Optional[bool] = None,
        published: Optional[bool] = None,
        grading_standard_id: Optional[int] = None,
        omit_from_final_grade: Optional[bool] = None,
        hide_in_gradebook: Optional[bool] = None,
        quiz_lti: Optional[bool] = None,
        moderated_grading: Optional[bool] = None,
        grader_count: Optional[int] = None,
        final_grader_id: Optional[int] = None,
        grader_comments_visible_to_graders: Optional[bool] = None,
        graders_anonymous_to_graders: Optional[bool] = None,
        graders_names_visible_to_final_grader: Optional[bool] = None,
        anonymous_grading: Optional[bool] = None,
        allowed_attempts: Optional[int] = None,
        annotatable_attachment_id: Optional[int] = None,
    ) -> Dict:
        """
        Create a new assignment.

        Args:
            course_id: Course ID
            name: Assignment name
            submission_types: List of supported submission types
            position: Position in assignment group
            allowed_extensions: Allowed file extensions for online_upload
            turnitin_enabled: Enable Turnitin submissions
            vericite_enabled: Enable VeriCite submissions
            turnitin_settings: Turnitin configuration settings
            integration_data: SIS integration data (JSON string)
            integration_id: Third party integration ID
            peer_reviews: Enable peer reviews
            automatic_peer_reviews: Automatically assign peer reviews
            notify_of_update: Send notification to students
            group_category_id: Group assignment category ID
            grade_group_students_individually: Grade group members individually
            external_tool_tag_attributes: External tool parameters
            points_possible: Maximum points possible
            grading_type: Grading strategy
            due_at: Due date/time
            lock_at: Lock date/time
            unlock_at: Unlock date/time
            description: Assignment description (HTML supported)
            assignment_group_id: Assignment group ID
            assignment_overrides: List of assignment overrides
            only_visible_to_overrides: Only visible to overrides
            published: Whether assignment is published
            grading_standard_id: Grading standard ID
            omit_from_final_grade: Exclude from final grade
            hide_in_gradebook: Hide in gradebook
            quiz_lti: Use Quizzes 2 LTI tool
            moderated_grading: Enable moderated grading
            grader_count: Number of provisional graders
            final_grader_id: Final grader user ID
            grader_comments_visible_to_graders: Show grader comments to other graders
            graders_anonymous_to_graders: Hide grader identities from other graders
            graders_names_visible_to_final_grader: Show grader names to final grader
            anonymous_grading: Enable anonymous grading
            allowed_attempts: Number of submission attempts (-1 for unlimited)
            annotatable_attachment_id: Attachment ID for student annotation

        Returns:
            Created Assignment dictionary

        Raises:
            ValueError: If validation fails for submission types, grading type, or other parameters
        """
        if not name or not name.strip():
            raise ValueError("Assignment name cannot be empty")

        # Validate submission_types
        valid_submission_types = {
            "online_quiz", "none", "on_paper", "discussion_topic", "external_tool",
            "online_upload", "online_text_entry", "online_url", "media_recording", "student_annotation"
        }
        invalid_types = [t for t in submission_types if t not in valid_submission_types]
        if invalid_types:
            raise ValueError(
                f"Invalid submission types: {', '.join(invalid_types)}. "
                f"Allowed values: {', '.join(sorted(valid_submission_types))}"
            )

        # Validate grading_type
        valid_grading_types = {"pass_fail", "percent", "letter_grade", "gpa_scale", "points", "not_graded"}
        if grading_type not in valid_grading_types:
            raise ValueError(
                f"Invalid grading_type '{grading_type}'. "
                f"Allowed values: {', '.join(sorted(valid_grading_types))}"
            )

        # Validate points_possible
        if points_possible is not None and points_possible < 0:
            raise ValueError("Points possible must be non-negative")

        # Validate grader_count for moderated grading
        if moderated_grading and grader_count is not None:
            if grader_count < 1:
                raise ValueError("Grader count must be at least 1 for moderated assignments")

        data = {
            "assignment[name]": name.strip(),
            "assignment[submission_types][]": submission_types,
            "assignment[grading_type]": grading_type,
        }

        # Add optional parameters
        if position is not None:
            data["assignment[position]"] = position
        if allowed_extensions:
            data["assignment[allowed_extensions][]"] = allowed_extensions
        if turnitin_enabled is not None:
            data["assignment[turnitin_enabled]"] = turnitin_enabled
        if vericite_enabled is not None:
            data["assignment[vericite_enabled]"] = vericite_enabled
        if turnitin_settings:
            data["assignment[turnitin_settings]"] = turnitin_settings
        if integration_data:
            data["assignment[integration_data]"] = integration_data
        if integration_id:
            data["assignment[integration_id]"] = integration_id
        if peer_reviews is not None:
            data["assignment[peer_reviews]"] = peer_reviews
        if automatic_peer_reviews is not None:
            data["assignment[automatic_peer_reviews]"] = automatic_peer_reviews
        if notify_of_update is not None:
            data["assignment[notify_of_update]"] = notify_of_update
        if group_category_id is not None:
            data["assignment[group_category_id]"] = group_category_id
        if grade_group_students_individually is not None:
            data["assignment[grade_group_students_individually]"] = grade_group_students_individually
        if external_tool_tag_attributes:
            data["assignment[external_tool_tag_attributes]"] = external_tool_tag_attributes
        if points_possible is not None:
            data["assignment[points_possible]"] = points_possible
        if due_at is not None:
            data["assignment[due_at]"] = due_at.isoformat()
        if lock_at is not None:
            data["assignment[lock_at]"] = lock_at.isoformat()
        if unlock_at is not None:
            data["assignment[unlock_at]"] = unlock_at.isoformat()
        if description:
            data["assignment[description]"] = description
        if assignment_group_id is not None:
            data["assignment[assignment_group_id]"] = assignment_group_id
        if assignment_overrides:
            data["assignment[assignment_overrides][]"] = assignment_overrides
        if only_visible_to_overrides is not None:
            data["assignment[only_visible_to_overrides]"] = only_visible_to_overrides
        if published is not None:
            data["assignment[published]"] = published
        if grading_standard_id is not None:
            data["assignment[grading_standard_id]"] = grading_standard_id
        if omit_from_final_grade is not None:
            data["assignment[omit_from_final_grade]"] = omit_from_final_grade
        if hide_in_gradebook is not None:
            data["assignment[hide_in_gradebook]"] = hide_in_gradebook
        if quiz_lti is not None:
            data["assignment[quiz_lti]"] = quiz_lti
        if moderated_grading is not None:
            data["assignment[moderated_grading]"] = moderated_grading
        if grader_count is not None:
            data["assignment[grader_count]"] = grader_count
        if final_grader_id is not None:
            data["assignment[final_grader_id]"] = final_grader_id
        if grader_comments_visible_to_graders is not None:
            data["assignment[grader_comments_visible_to_graders]"] = grader_comments_visible_to_graders
        if graders_anonymous_to_graders is not None:
            data["assignment[graders_anonymous_to_graders]"] = graders_anonymous_to_graders
        if graders_names_visible_to_final_grader is not None:
            data["assignment[graders_names_visible_to_final_grader]"] = graders_names_visible_to_final_grader
        if anonymous_grading is not None:
            data["assignment[anonymous_grading]"] = anonymous_grading
        if allowed_attempts is not None:
            data["assignment[allowed_attempts]"] = allowed_attempts
        if annotatable_attachment_id is not None:
            data["assignment[annotatable_attachment_id]"] = annotatable_attachment_id

        response = self._make_request("POST", f"/api/v1/courses/{course_id}/assignments", data=data)
        return response.json()

    def update_assignment(
        self,
        course_id: Union[int, str],
        assignment_id: Union[int, str],
        name: Optional[str] = None,
        position: Optional[int] = None,
        submission_types: Optional[
            List[
                Literal[
                    "online_quiz",
                    "none",
                    "on_paper",
                    "discussion_topic",
                    "external_tool",
                    "online_upload",
                    "online_text_entry",
                    "online_url",
                    "media_recording",
                    "student_annotation",
                ]
            ]
        ] = None,
        allowed_extensions: Optional[List[str]] = None,
        turnitin_enabled: Optional[bool] = None,
        vericite_enabled: Optional[bool] = None,
        turnitin_settings: Optional[Dict] = None,
        sis_assignment_id: Optional[str] = None,
        integration_data: Optional[str] = None,
        integration_id: Optional[str] = None,
        peer_reviews: Optional[bool] = None,
        automatic_peer_reviews: Optional[bool] = None,
        notify_of_update: Optional[bool] = None,
        group_category_id: Optional[int] = None,
        grade_group_students_individually: Optional[bool] = None,
        external_tool_tag_attributes: Optional[Dict] = None,
        points_possible: Optional[float] = None,
        grading_type: Optional[
            Literal["pass_fail", "percent", "letter_grade", "gpa_scale", "points", "not_graded"]
        ] = None,
        due_at: Optional[datetime] = None,
        lock_at: Optional[datetime] = None,
        unlock_at: Optional[datetime] = None,
        description: Optional[str] = None,
        assignment_group_id: Optional[int] = None,
        assignment_overrides: Optional[List[Dict]] = None,
        only_visible_to_overrides: Optional[bool] = None,
        published: Optional[bool] = None,
        grading_standard_id: Optional[int] = None,
        omit_from_final_grade: Optional[bool] = None,
        hide_in_gradebook: Optional[bool] = None,
        moderated_grading: Optional[bool] = None,
        grader_count: Optional[int] = None,
        final_grader_id: Optional[int] = None,
        grader_comments_visible_to_graders: Optional[bool] = None,
        graders_anonymous_to_graders: Optional[bool] = None,
        graders_names_visible_to_final_grader: Optional[bool] = None,
        anonymous_grading: Optional[bool] = None,
        allowed_attempts: Optional[int] = None,
        annotatable_attachment_id: Optional[int] = None,
        force_updated_at: Optional[bool] = None,
    ) -> Dict:
        """
        Update an existing assignment.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            name: Assignment name
            position: Position in assignment group
            submission_types: List of supported submission types (only if no student submissions)
            allowed_extensions: Allowed file extensions for online_upload
            turnitin_enabled: Enable Turnitin submissions
            vericite_enabled: Enable VeriCite submissions
            turnitin_settings: Turnitin configuration settings
            sis_assignment_id: SIS assignment ID
            integration_data: SIS integration data (JSON string)
            integration_id: Third party integration ID
            peer_reviews: Enable peer reviews
            automatic_peer_reviews: Automatically assign peer reviews
            notify_of_update: Send notification to students
            group_category_id: Group assignment category ID
            grade_group_students_individually: Grade group members individually
            external_tool_tag_attributes: External tool parameters
            points_possible: Maximum points possible
            grading_type: Grading strategy
            due_at: Due date/time
            lock_at: Lock date/time
            unlock_at: Unlock date/time
            description: Assignment description (HTML supported)
            assignment_group_id: Assignment group ID
            assignment_overrides: List of assignment overrides
            only_visible_to_overrides: Only visible to overrides
            published: Whether assignment is published
            grading_standard_id: Grading standard ID
            omit_from_final_grade: Exclude from final grade
            hide_in_gradebook: Hide in gradebook
            moderated_grading: Enable moderated grading
            grader_count: Number of provisional graders
            final_grader_id: Final grader user ID
            grader_comments_visible_to_graders: Show grader comments to other graders
            graders_anonymous_to_graders: Hide grader identities from other graders
            graders_names_visible_to_final_grader: Show grader names to final grader
            anonymous_grading: Enable anonymous grading
            allowed_attempts: Number of submission attempts (-1 or null for unlimited)
            annotatable_attachment_id: Attachment ID for student annotation
            force_updated_at: Force updated_at to be set even if no changes

        Returns:
            Updated Assignment dictionary

        Raises:
            ValueError: If validation fails for submission types, grading type, or other parameters
        """
        data = {}

        if name is not None:
            if not name.strip():
                raise ValueError("Assignment name cannot be empty")
            data["assignment[name]"] = name.strip()

        # Validate submission_types if provided
        if submission_types is not None:
            valid_submission_types = {
                "online_quiz", "none", "on_paper", "discussion_topic", "external_tool",
                "online_upload", "online_text_entry", "online_url", "media_recording", "student_annotation"
            }
            invalid_types = [t for t in submission_types if t not in valid_submission_types]
            if invalid_types:
                raise ValueError(
                    f"Invalid submission types: {', '.join(invalid_types)}. "
                    f"Allowed values: {', '.join(sorted(valid_submission_types))}"
                )
            data["assignment[submission_types][]"] = submission_types

        # Validate grading_type if provided
        if grading_type is not None:
            valid_grading_types = {"pass_fail", "percent", "letter_grade", "gpa_scale", "points", "not_graded"}
            if grading_type not in valid_grading_types:
                raise ValueError(
                    f"Invalid grading_type '{grading_type}'. "
                    f"Allowed values: {', '.join(sorted(valid_grading_types))}"
                )
            data["assignment[grading_type]"] = grading_type

        # Validate points_possible if provided
        if points_possible is not None and points_possible < 0:
            raise ValueError("Points possible must be non-negative")

        # Add all optional parameters
        if position is not None:
            data["assignment[position]"] = position
        if allowed_extensions is not None:
            data["assignment[allowed_extensions][]"] = allowed_extensions
        if turnitin_enabled is not None:
            data["assignment[turnitin_enabled]"] = turnitin_enabled
        if vericite_enabled is not None:
            data["assignment[vericite_enabled]"] = vericite_enabled
        if turnitin_settings is not None:
            data["assignment[turnitin_settings]"] = turnitin_settings
        if sis_assignment_id is not None:
            data["assignment[sis_assignment_id]"] = sis_assignment_id
        if integration_data is not None:
            data["assignment[integration_data]"] = integration_data
        if integration_id is not None:
            data["assignment[integration_id]"] = integration_id
        if peer_reviews is not None:
            data["assignment[peer_reviews]"] = peer_reviews
        if automatic_peer_reviews is not None:
            data["assignment[automatic_peer_reviews]"] = automatic_peer_reviews
        if notify_of_update is not None:
            data["assignment[notify_of_update]"] = notify_of_update
        if group_category_id is not None:
            data["assignment[group_category_id]"] = group_category_id
        if grade_group_students_individually is not None:
            data["assignment[grade_group_students_individually]"] = grade_group_students_individually
        if external_tool_tag_attributes is not None:
            data["assignment[external_tool_tag_attributes]"] = external_tool_tag_attributes
        if points_possible is not None:
            data["assignment[points_possible]"] = points_possible
        if due_at is not None:
            data["assignment[due_at]"] = due_at.isoformat()
        if lock_at is not None:
            data["assignment[lock_at]"] = lock_at.isoformat()
        if unlock_at is not None:
            data["assignment[unlock_at]"] = unlock_at.isoformat()
        if description is not None:
            data["assignment[description]"] = description
        if assignment_group_id is not None:
            data["assignment[assignment_group_id]"] = assignment_group_id
        if assignment_overrides is not None:
            data["assignment[assignment_overrides][]"] = assignment_overrides
        if only_visible_to_overrides is not None:
            data["assignment[only_visible_to_overrides]"] = only_visible_to_overrides
        if published is not None:
            data["assignment[published]"] = published
        if grading_standard_id is not None:
            data["assignment[grading_standard_id]"] = grading_standard_id
        if omit_from_final_grade is not None:
            data["assignment[omit_from_final_grade]"] = omit_from_final_grade
        if hide_in_gradebook is not None:
            data["assignment[hide_in_gradebook]"] = hide_in_gradebook
        if moderated_grading is not None:
            data["assignment[moderated_grading]"] = moderated_grading
        if grader_count is not None:
            data["assignment[grader_count]"] = grader_count
        if final_grader_id is not None:
            data["assignment[final_grader_id]"] = final_grader_id
        if grader_comments_visible_to_graders is not None:
            data["assignment[grader_comments_visible_to_graders]"] = grader_comments_visible_to_graders
        if graders_anonymous_to_graders is not None:
            data["assignment[graders_anonymous_to_graders]"] = graders_anonymous_to_graders
        if graders_names_visible_to_final_grader is not None:
            data["assignment[graders_names_visible_to_final_grader]"] = graders_names_visible_to_final_grader
        if anonymous_grading is not None:
            data["assignment[anonymous_grading]"] = anonymous_grading
        if allowed_attempts is not None:
            data["assignment[allowed_attempts]"] = allowed_attempts
        if annotatable_attachment_id is not None:
            data["assignment[annotatable_attachment_id]"] = annotatable_attachment_id
        if force_updated_at is not None:
            data["assignment[force_updated_at]"] = force_updated_at

        response = self._make_request(
            "PUT", f"/api/v1/courses/{course_id}/assignments/{assignment_id}", data=data
        )
        return response.json()

    def bulk_update_assignment_dates(
        self,
        course_id: Union[int, str],
        assignment_updates: List[Dict],
    ) -> Dict:
        """
        Update due dates and availability dates for multiple assignments.

        Args:
            course_id: Course ID
            assignment_updates: List of assignment update objects with 'id' and 'all_dates' keys

        Returns:
            Progress object for tracking the bulk update job

        Raises:
            ValueError: If assignment_updates is invalid

        Example:
            updates = [{
                "id": 1,
                "all_dates": [{
                    "base": True,
                    "due_at": "2020-08-29T23:59:00-06:00"
                }, {
                    "id": 2,
                    "due_at": "2020-08-30T23:59:00-06:00"
                }]
            }]
            result = api.bulk_update_assignment_dates(123, updates)
        """
        if not assignment_updates:
            raise ValueError("Assignment updates cannot be empty")

        for i, update in enumerate(assignment_updates):
            if not isinstance(update, dict):
                raise ValueError(f"Assignment update at index {i} must be a dictionary")
            if "id" not in update:
                raise ValueError(f"Assignment update at index {i} must include 'id'")
            if "all_dates" not in update:
                raise ValueError(f"Assignment update at index {i} must include 'all_dates'")

        response = self._make_request(
            "PUT", f"/api/v1/courses/{course_id}/assignments/bulk_update", json_data=assignment_updates
        )
        return response.json()

    # Assignment Override Methods

    def list_assignment_overrides(
        self,
        course_id: Union[int, str],
        assignment_id: Union[int, str],
    ) -> List[Dict]:
        """
        List assignment overrides for an assignment.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID

        Returns:
            List of AssignmentOverride dictionaries
        """
        response = self._make_request(
            "GET", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/overrides"
        )
        return response.json()

    def get_assignment_override(
        self,
        course_id: Union[int, str],
        assignment_id: Union[int, str],
        override_id: Union[int, str],
    ) -> Dict:
        """
        Get a single assignment override.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            override_id: Override ID

        Returns:
            AssignmentOverride dictionary
        """
        response = self._make_request(
            "GET", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/overrides/{override_id}"
        )
        return response.json()

    def get_group_override_redirect(
        self,
        group_id: Union[int, str],
        assignment_id: Union[int, str],
    ) -> Dict:
        """
        Redirect to the assignment override for a group.

        Args:
            group_id: Group ID
            assignment_id: Assignment ID

        Returns:
            Redirect response to the override
        """
        response = self._make_request(
            "GET", f"/api/v1/groups/{group_id}/assignments/{assignment_id}/override"
        )
        return response.json()

    def get_section_override_redirect(
        self,
        course_section_id: Union[int, str],
        assignment_id: Union[int, str],
    ) -> Dict:
        """
        Redirect to the assignment override for a section.

        Args:
            course_section_id: Course section ID
            assignment_id: Assignment ID

        Returns:
            Redirect response to the override
        """
        response = self._make_request(
            "GET", f"/api/v1/sections/{course_section_id}/assignments/{assignment_id}/override"
        )
        return response.json()

    def create_assignment_override(
        self,
        course_id: Union[int, str],
        assignment_id: Union[int, str],
        student_ids: Optional[List[int]] = None,
        title: Optional[str] = None,
        group_id: Optional[int] = None,
        course_section_id: Optional[int] = None,
        due_at: Optional[datetime] = None,
        unlock_at: Optional[datetime] = None,
        lock_at: Optional[datetime] = None,
    ) -> Dict:
        """
        Create an assignment override.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            student_ids: IDs of target students (for adhoc overrides)
            title: Title of adhoc override (required if student_ids provided)
            group_id: ID of target group (for group assignments)
            course_section_id: ID of target section
            due_at: Overridden due date
            unlock_at: Overridden unlock date
            lock_at: Overridden lock date

        Returns:
            Created AssignmentOverride dictionary

        Raises:
            ValueError: If validation fails for override parameters

        Note:
            One of student_ids, group_id, or course_section_id must be present.
            If multiple are present, only the most specific is used (student_ids > group_id > course_section_id).
        """
        # Validate that at least one target is specified
        targets = [student_ids, group_id, course_section_id]
        if not any(target is not None for target in targets):
            raise ValueError("One of student_ids, group_id, or course_section_id must be provided")

        # Validate title requirement for adhoc overrides
        if student_ids is not None and not title:
            raise ValueError("Title is required when student_ids is provided")

        # Validate student_ids
        if student_ids is not None:
            if not isinstance(student_ids, list) or not student_ids:
                raise ValueError("student_ids must be a non-empty list")
            if not all(isinstance(sid, int) and sid > 0 for sid in student_ids):
                raise ValueError("All student_ids must be positive integers")

        data = {}

        # Add target specification (most specific takes precedence)
        if student_ids is not None:
            data["assignment_override[student_ids][]"] = student_ids
            data["assignment_override[title]"] = title
        elif group_id is not None:
            data["assignment_override[group_id]"] = group_id
        elif course_section_id is not None:
            data["assignment_override[course_section_id]"] = course_section_id

        # Add date overrides
        if due_at is not None:
            data["assignment_override[due_at]"] = due_at.isoformat()
        if unlock_at is not None:
            data["assignment_override[unlock_at]"] = unlock_at.isoformat()
        if lock_at is not None:
            data["assignment_override[lock_at]"] = lock_at.isoformat()

        response = self._make_request(
            "POST", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/overrides", data=data
        )
        return response.json()

    def update_assignment_override(
        self,
        course_id: Union[int, str],
        assignment_id: Union[int, str],
        override_id: Union[int, str],
        student_ids: Optional[List[int]] = None,
        title: Optional[str] = None,
        due_at: Optional[datetime] = None,
        unlock_at: Optional[datetime] = None,
        lock_at: Optional[datetime] = None,
    ) -> Dict:
        """
        Update an assignment override.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            override_id: Override ID
            student_ids: IDs of target students (ignored unless override is adhoc)
            title: Title of adhoc override (ignored unless override is adhoc)
            due_at: Overridden due date (null to remove override)
            unlock_at: Overridden unlock date (null to remove override)
            lock_at: Overridden lock date (null to remove override)

        Returns:
            Updated AssignmentOverride dictionary

        Raises:
            ValueError: If validation fails for override parameters

        Note:
            All current overridden values must be supplied to be retained.
            Target override sets cannot be changed for group or section overrides.
        """
        # Validate student_ids if provided
        if student_ids is not None:
            if not isinstance(student_ids, list) or not student_ids:
                raise ValueError("student_ids must be a non-empty list")
            if not all(isinstance(sid, int) and sid > 0 for sid in student_ids):
                raise ValueError("All student_ids must be positive integers")

        data = {}

        # Add adhoc override updates
        if student_ids is not None:
            data["assignment_override[student_ids][]"] = student_ids
        if title is not None:
            data["assignment_override[title]"] = title

        # Add date overrides (explicit None handling for clearing dates)
        if due_at is not None:
            data["assignment_override[due_at]"] = due_at.isoformat()
        if unlock_at is not None:
            data["assignment_override[unlock_at]"] = unlock_at.isoformat()
        if lock_at is not None:
            data["assignment_override[lock_at]"] = lock_at.isoformat()

        response = self._make_request(
            "PUT", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/overrides/{override_id}", data=data
        )
        return response.json()

    def delete_assignment_override(
        self,
        course_id: Union[int, str],
        assignment_id: Union[int, str],
        override_id: Union[int, str],
    ) -> Dict:
        """
        Delete an assignment override.

        Args:
            course_id: Course ID
            assignment_id: Assignment ID
            override_id: Override ID

        Returns:
            Deleted AssignmentOverride dictionary
        """
        response = self._make_request(
            "DELETE", f"/api/v1/courses/{course_id}/assignments/{assignment_id}/overrides/{override_id}"
        )
        return response.json()

    def batch_retrieve_overrides(
        self,
        course_id: Union[int, str],
        assignment_overrides: List[Dict[str, Union[int, str]]],
    ) -> List[Dict]:
        """
        Batch retrieve assignment overrides in a course.

        Args:
            course_id: Course ID
            assignment_overrides: List of dicts with 'id' and 'assignment_id' keys

        Returns:
            List of AssignmentOverride dictionaries (null for not found)

        Raises:
            ValueError: If assignment_overrides format is invalid

        Example:
            overrides = [
                {"id": 109, "assignment_id": 122},
                {"id": 99, "assignment_id": 111}
            ]
            result = api.batch_retrieve_overrides(123, overrides)
        """
        if not assignment_overrides:
            raise ValueError("assignment_overrides cannot be empty")

        for i, override in enumerate(assignment_overrides):
            if not isinstance(override, dict):
                raise ValueError(f"Override at index {i} must be a dictionary")
            if "id" not in override or "assignment_id" not in override:
                raise ValueError(f"Override at index {i} must include both 'id' and 'assignment_id'")

        # Convert to query parameters format
        params = {}
        for i, override in enumerate(assignment_overrides):
            params["assignment_overrides[][id]"] = override["id"]
            params["assignment_overrides[][assignment_id]"] = override["assignment_id"]

        response = self._make_request(
            "GET", f"/api/v1/courses/{course_id}/assignments/overrides", params=params
        )
        return response.json()

    def batch_create_overrides(
        self,
        course_id: Union[int, str],
        assignment_overrides: List[Dict],
    ) -> List[Dict]:
        """
        Batch create assignment overrides in a course.

        Args:
            course_id: Course ID
            assignment_overrides: List of override objects (see create_assignment_override for attributes)

        Returns:
            List of created AssignmentOverride dictionaries

        Raises:
            ValueError: If assignment_overrides format is invalid

        Note:
            Creates all overrides in a transaction - all succeed or none are created.
            Errors are reported in an errors attribute array.

        Example:
            overrides = [
                {
                    "assignment_id": 109,
                    "student_ids": [8],
                    "title": "Student Override",
                    "due_at": "2012-10-08T21:00:00Z"
                },
                {
                    "assignment_id": 13,
                    "course_section_id": 200,
                    "due_at": "2012-10-08T21:00:00Z"
                }
            ]
            result = api.batch_create_overrides(123, overrides)
        """
        if not assignment_overrides:
            raise ValueError("assignment_overrides cannot be empty")

        for i, override in enumerate(assignment_overrides):
            if not isinstance(override, dict):
                raise ValueError(f"Override at index {i} must be a dictionary")
            if "assignment_id" not in override:
                raise ValueError(f"Override at index {i} must include 'assignment_id'")

            # Validate target specification
            targets = ["student_ids", "group_id", "course_section_id"]
            if not any(target in override for target in targets):
                raise ValueError(f"Override at index {i} must include one of: {', '.join(targets)}")

        data = {"assignment_overrides": assignment_overrides}

        response = self._make_request(
            "POST", f"/api/v1/courses/{course_id}/assignments/overrides", json_data=data
        )
        return response.json()

    def batch_update_overrides(
        self,
        course_id: Union[int, str],
        assignment_overrides: List[Dict],
    ) -> List[Dict]:
        """
        Batch update assignment overrides in a course.

        Args:
            course_id: Course ID
            assignment_overrides: List of override objects with 'id' and 'assignment_id' plus update attributes

        Returns:
            List of updated AssignmentOverride dictionaries

        Raises:
            ValueError: If assignment_overrides format is invalid

        Note:
            Updates all overrides in a transaction - all succeed or none are updated.
            All current overridden values must be supplied to be retained.
            Errors are reported in an errors attribute array.

        Example:
            overrides = [
                {
                    "id": 122,
                    "assignment_id": 109,
                    "title": "Updated Title"
                },
                {
                    "id": 993,
                    "assignment_id": 13,
                    "due_at": "2012-10-08T21:00:00Z"
                }
            ]
            result = api.batch_update_overrides(123, overrides)
        """
        if not assignment_overrides:
            raise ValueError("assignment_overrides cannot be empty")

        for i, override in enumerate(assignment_overrides):
            if not isinstance(override, dict):
                raise ValueError(f"Override at index {i} must be a dictionary")
            if "id" not in override or "assignment_id" not in override:
                raise ValueError(f"Override at index {i} must include both 'id' and 'assignment_id'")

        data = {"assignment_overrides": assignment_overrides}

        response = self._make_request(
            "PUT", f"/api/v1/courses/{course_id}/assignments/overrides", json_data=data
        )
        return response.json()


# Convenience instance using environment variables
assignments = AssignmentsAPI()