from typing import List, Dict, Union, Literal, Optional
from ..base import CanvasAPIBase


class GradingRules(Dict):
    """Grading Rules for an assignment."""

    drop_lowest: int
    drop_highest: int
    never_drop: List[int]


class AssignmentGroup(Dict):
    """An assignment group object."""

    id: int
    name: str
    position: int
    group_weight: int
    sis_source_id: str
    integration_data: dict
    assignments: list
    rules: Union[GradingRules, None]


class AssignmentGroupsAPI(CanvasAPIBase):
    """Canvas LMS Assignment Groups API client for managing assignment groups."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Assignment Groups API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def list_assignment_groups(
        self,
        course_id: Union[int, str],
        include: Optional[
            List[
                Literal[
                    "assignments",
                    "discussion_topic",
                    "all_dates",
                    "assignment_visibility",
                    "overrides",
                    "submission",
                    "observed_users",
                    "can_edit",
                    "score_statistics",
                ]
            ]
        ] = None,
        assignment_ids: Optional[List[Union[int, str]]] = None,
        exclude_assignment_submission_types: Optional[
            List[
                Literal["online_quiz", "discussion_topic", "wiki_page", "external_tool"]
            ]
        ] = None,
        override_assignment_dates: bool = True,
        grading_period_id: Optional[int] = None,
        scope_assignments_to_student: bool = False,
        all_page: bool = False,
    ) -> List[AssignmentGroup]:
        """
        List assignment groups for a course.

        Args:
            course_id: Course ID
            include: Associations to include with the group
            assignment_ids: Filter assignments by IDs (requires "assignments" in include)
            exclude_assignment_submission_types: Exclude assignments with specified submission types
            override_assignment_dates: Apply assignment overrides for each assignment
            grading_period_id: Filter by grading period ID
            scope_assignments_to_student: Filter assignments to current user in grading period
            all_pages: If True, fetch all pages automatically. If False, return only first page.

        Returns:
            List of AssignmentGroup dictionaries

        Raises:
            ValueError: If invalid include values or parameter combinations are provided
        """
        # Validate include values
        if include is not None:
            valid_include_values = {
                "assignments",
                "discussion_topic",
                "all_dates",
                "assignment_visibility",
                "overrides",
                "submission",
                "observed_users",
                "can_edit",
                "score_statistics",
            }
            invalid_includes = [i for i in include if i not in valid_include_values]
            if invalid_includes:
                raise ValueError(
                    f"Invalid include values: {', '.join(invalid_includes)}. "
                    f"Allowed values: {', '.join(sorted(valid_include_values))}"
                )

            # Validate include dependencies
            if "discussion_topic" in include and "assignments" not in include:
                raise ValueError(
                    "'discussion_topic' requires 'assignments' to be included"
                )
            if "all_dates" in include and "assignments" not in include:
                raise ValueError("'all_dates' requires 'assignments' to be included")
            if "assignment_visibility" in include and "assignments" not in include:
                raise ValueError(
                    "'assignment_visibility' requires 'assignments' to be included"
                )
            if "submission" in include and "assignments" not in include:
                raise ValueError("'submission' requires 'assignments' to be included")
            if "score_statistics" in include:
                if "assignments" not in include or "submission" not in include:
                    raise ValueError(
                        "'score_statistics' requires both 'assignments' and 'submission' to be included"
                    )

        # Validate exclude_assignment_submission_types
        if exclude_assignment_submission_types is not None:
            valid_submission_types = {
                "online_quiz",
                "discussion_topic",
                "wiki_page",
                "external_tool",
            }
            invalid_types = [
                t
                for t in exclude_assignment_submission_types
                if t not in valid_submission_types
            ]
            if invalid_types:
                raise ValueError(
                    f"Invalid submission types: {', '.join(invalid_types)}. "
                    f"Allowed values: {', '.join(sorted(valid_submission_types))}"
                )

        # Validate scope_assignments_to_student requires grading_period_id
        if scope_assignments_to_student and grading_period_id is None:
            raise ValueError(
                "'scope_assignments_to_student' requires 'grading_period_id' to be provided"
            )

        params = {}

        if include:
            params["include[]"] = include
        if assignment_ids:
            params["assignment_ids[]"] = assignment_ids
        if exclude_assignment_submission_types:
            params["exclude_assignment_submission_types[]"] = (
                exclude_assignment_submission_types
            )
        if override_assignment_dates is not None:
            params["override_assignment_dates"] = override_assignment_dates
        if grading_period_id is not None:
            params["grading_period_id"] = grading_period_id
        if scope_assignments_to_student:
            params["scope_assignments_to_student"] = scope_assignments_to_student

        if all_page:
            return self._get_all_pages(
                "GET", f"/api/v1/courses/{course_id}/assignment_groups", params=params
            )
        else:
            response = self._make_request(
                "GET", f"/api/v1/courses/{course_id}/assignment_groups", params=params
            )
            return response.json()

    def get_assignment_group(
        self,
        course_id: Union[int, str],
        assignment_group_id: Union[int, str],
        include: Optional[
            List[
                Literal[
                    "assignments",
                    "discussion_topic",
                    "assignment_visibility",
                    "submission",
                    "score_statistics",
                ]
            ]
        ] = None,
        override_assignment_dates: bool = True,
        grading_period_id: Optional[int] = None,
    ) -> AssignmentGroup:
        """
        Get a specific assignment group.

        Args:
            course_id: Course ID
            assignment_group_id: Assignment Group ID
            include: Associations to include with the group
            override_assignment_dates: Apply assignment overrides for each assignment
            grading_period_id: Filter by grading period ID

        Returns:
            AssignmentGroup dictionary

        Raises:
            ValueError: If invalid include values are provided
        """
        # Validate include values
        if include is not None:
            valid_include_values = {
                "assignments",
                "discussion_topic",
                "assignment_visibility",
                "submission",
                "score_statistics",
            }
            invalid_includes = [i for i in include if i not in valid_include_values]
            if invalid_includes:
                raise ValueError(
                    f"Invalid include values: {', '.join(invalid_includes)}. "
                    f"Allowed values: {', '.join(sorted(valid_include_values))}"
                )

            # Validate include dependencies
            if "discussion_topic" in include and "assignments" not in include:
                raise ValueError(
                    "'discussion_topic' requires 'assignments' to be included"
                )
            if "assignment_visibility" in include and "assignments" not in include:
                raise ValueError(
                    "'assignment_visibility' requires 'assignments' to be included"
                )
            if "submission" in include and "assignments" not in include:
                raise ValueError("'submission' requires 'assignments' to be included")
            if "score_statistics" in include:
                if "assignments" not in include or "submission" not in include:
                    raise ValueError(
                        "'score_statistics' requires both 'assignments' and 'submission' to be included"
                    )

        params = {}

        if include:
            params["include[]"] = include
        if override_assignment_dates is not None:
            params["override_assignment_dates"] = override_assignment_dates
        if grading_period_id is not None:
            params["grading_period_id"] = grading_period_id

        response = self._make_request(
            "GET",
            f"/api/v1/courses/{course_id}/assignment_groups/{assignment_group_id}",
            params=params,
        )
        return response.json()

    def create_assignment_group(
        self,
        course_id: Union[int, str],
        name: str,
        position: Optional[int] = None,
        group_weight: Optional[float] = None,
        sis_source_id: Optional[str] = None,
        integration_data: Optional[Dict] = None,
    ) -> AssignmentGroup:
        """
        Create a new assignment group.

        Args:
            course_id: Course ID
            name: Assignment group name
            position: Position of this assignment group relative to others
            group_weight: Percent of total grade this assignment group represents
            sis_source_id: SIS source ID of the assignment group
            integration_data: Integration data for the assignment group

        Returns:
            Created AssignmentGroup dictionary

        Raises:
            ValueError: If name is empty or group_weight is invalid
        """
        if not name or not name.strip():
            raise ValueError("Assignment group name cannot be empty")

        if group_weight is not None and (group_weight < 0 or group_weight > 100):
            raise ValueError("Group weight must be between 0 and 100")

        data = {"name": name.strip()}

        if position is not None:
            data["position"] = position
        if group_weight is not None:
            data["group_weight"] = group_weight
        if sis_source_id is not None:
            data["sis_source_id"] = sis_source_id
        if integration_data is not None:
            data["integration_data"] = integration_data

        response = self._make_request(
            "POST", f"/api/v1/courses/{course_id}/assignment_groups", data=data
        )
        return response.json()

    def update_assignment_group(
        self,
        course_id: Union[int, str],
        assignment_group_id: Union[int, str],
        name: Optional[str] = None,
        position: Optional[int] = None,
        group_weight: Optional[float] = None,
        sis_source_id: Optional[str] = None,
        integration_data: Optional[Dict] = None,
        rules: Optional[Dict] = None,
    ) -> AssignmentGroup:
        """
        Update an existing assignment group.

        Args:
            course_id: Course ID
            assignment_group_id: Assignment Group ID
            name: Assignment group name
            position: Position of this assignment group relative to others
            group_weight: Percent of total grade this assignment group represents
            sis_source_id: SIS source ID of the assignment group
            integration_data: Integration data for the assignment group
            rules: Grading rules (drop_lowest, drop_highest, never_drop)

        Returns:
            Updated AssignmentGroup dictionary

        Raises:
            ValueError: If name is empty, group_weight is invalid, or rules are malformed
        """
        if name is not None and (not name or not name.strip()):
            raise ValueError("Assignment group name cannot be empty")

        if group_weight is not None and (group_weight < 0 or group_weight > 100):
            raise ValueError("Group weight must be between 0 and 100")

        # Validate rules if provided
        if rules is not None:
            if not isinstance(rules, dict):
                raise ValueError("Rules must be a dictionary")

            valid_rule_keys = {"drop_lowest", "drop_highest", "never_drop"}
            invalid_keys = set(rules.keys()) - valid_rule_keys
            if invalid_keys:
                raise ValueError(
                    f"Invalid rule keys: {', '.join(invalid_keys)}. "
                    f"Allowed keys: {', '.join(sorted(valid_rule_keys))}"
                )

            if "drop_lowest" in rules and (
                not isinstance(rules["drop_lowest"], int) or rules["drop_lowest"] < 0
            ):
                raise ValueError("drop_lowest must be a non-negative integer")

            if "drop_highest" in rules and (
                not isinstance(rules["drop_highest"], int) or rules["drop_highest"] < 0
            ):
                raise ValueError("drop_highest must be a non-negative integer")

            if "never_drop" in rules and not isinstance(rules["never_drop"], list):
                raise ValueError("never_drop must be a list of assignment IDs")

        data = {}

        if name is not None:
            data["name"] = name.strip()
        if position is not None:
            data["position"] = position
        if group_weight is not None:
            data["group_weight"] = group_weight
        if sis_source_id is not None:
            data["sis_source_id"] = sis_source_id
        if integration_data is not None:
            data["integration_data"] = integration_data
        if rules is not None:
            data["rules"] = rules

        response = self._make_request(
            "PUT",
            f"/api/v1/courses/{course_id}/assignment_groups/{assignment_group_id}",
            data=data,
        )
        return response.json()

    def delete_assignment_group(
        self,
        course_id: Union[int, str],
        assignment_group_id: Union[int, str],
        move_assignments_to: Optional[Union[int, str]] = None,
    ) -> AssignmentGroup:
        """
        Delete an assignment group.

        Args:
            course_id: Course ID
            assignment_group_id: Assignment Group ID to delete
            move_assignments_to: ID of another assignment group to move assignments to
                                If not provided, assignments in this group will be deleted

        Returns:
            Deleted AssignmentGroup dictionary

        Example:
            # Delete group and move assignments to another group
            result = api.delete_assignment_group(123, 456, move_assignments_to=789)

            # Delete group and all its assignments
            result = api.delete_assignment_group(123, 456)
        """
        params = {}
        if move_assignments_to is not None:
            params["move_assignments_to"] = move_assignments_to

        response = self._make_request(
            "DELETE",
            f"/api/v1/courses/{course_id}/assignment_groups/{assignment_group_id}",
            params=params,
        )
        return response.json()


# Convenience instance using environment variables
assignment_groups = AssignmentGroupsAPI()
