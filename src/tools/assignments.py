"""Assignment-related tools for Canvas MCP."""

from typing import Annotated, Literal
from pydantic import Field
from datetime import datetime

from .base import ToolProvider
from canvasAPI.assignment import assignments, assignment_groups, assignment_extensions
from tools.getToken import get_user_token


class AssignmentTools(ToolProvider):
    """Tools for managing Canvas assignments."""

    def _register_tools(self):
        """Register all assignment-related tools."""
        tools_to_register = [
            (self.list_assignments, {"assignment"}),
            (self.get_assignment, {"assignment"}),
            (self.create_assignment, {"assignment"}),
            (self.update_assignment, {"assignment"}),
            (self.delete_assignment, {"assignment"}),
            (self.duplicate_assignment, {"assignment"}),
            (self.bulk_update_assignment_dates, {"assignment", "bulk"}),
        ]
        
        for tool_func, tags in tools_to_register:
            wrapped_tool = self._wrap_tool_with_analytics(tool_func)
            self.mcp.tool(wrapped_tool, tags=tags)

    async def list_assignments(
        self,
        course_id: Annotated[
            str | int, Field(description="The course ID to list assignments from")
        ],
        assignment_group_id: Annotated[
            str | int | None,
            Field(
                description="If provided, list assignments for this specific assignment group"
            ),
        ] = None,
        include: Annotated[
            list[
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
            | None,
            Field(description="Optional information to include with each assignment"),
        ] = None,
        search_term: Annotated[
            str | None,
            Field(description="Partial title of assignments to match and return"),
        ] = None,
        override_assignment_dates: Annotated[
            bool | None,
            Field(description="Apply assignment overrides for each assignment"),
        ] = True,
        needs_grading_count_by_section: Annotated[
            bool | None,
            Field(description="Split up needs_grading_count by sections"),
        ] = False,
        bucket: Annotated[
            Literal[
                "past",
                "overdue",
                "undated",
                "ungraded",
                "unsubmitted",
                "upcoming",
                "future",
            ]
            | None,
            Field(description="Filter assignments by due date and submission status"),
        ] = None,
        assignment_ids: Annotated[
            list[str | int] | None,
            Field(description="Return only specified assignments"),
        ] = None,
        order_by: Annotated[
            Literal["position", "name", "due_at"] | None,
            Field(description="Determines the order of assignments"),
        ] = "position",
        post_to_sis: Annotated[
            bool | None,
            Field(
                description="Return only assignments that have post_to_sis set or not set"
            ),
        ] = None,
        new_quizzes: Annotated[
            bool | None,
            Field(description="Return only New Quizzes assignments"),
        ] = None,
    ) -> list[dict]:
        """List assignments for a course or assignment group."""
        params = self._validate_params(
            course_id=course_id,
            assignment_group_id=assignment_group_id,
            include=include,
            search_term=search_term,
            override_assignment_dates=override_assignment_dates,
            needs_grading_count_by_section=needs_grading_count_by_section,
            bucket=bucket,
            assignment_ids=assignment_ids,
            order_by=order_by,
            post_to_sis=post_to_sis,
            new_quizzes=new_quizzes,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        response: list[assignments.Assignment] = assignments.list_assignments(**params)

        decorated_response = [
            {
                "id": i.get("id"),
                "name": i.get("name"),
            }
            for i in response
        ]

        return decorated_response

    async def get_assignment(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        assignment_id: Annotated[
            str | int, Field(description="The assignment ID to get")
        ],
        include: Annotated[
            list[
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
            | None,
            Field(description="Associations to include with the assignment"),
        ] = None,
        override_assignment_dates: Annotated[
            bool | None,
            Field(description="Apply assignment overrides to the assignment"),
        ] = True,
        needs_grading_count_by_section: Annotated[
            bool | None,
            Field(description="Split up needs_grading_count by sections"),
        ] = False,
        all_dates: Annotated[
            bool | None,
            Field(description="All dates associated with the assignment"),
        ] = False,
    ) -> dict:
        """Get a single assignment."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            include=include,
            override_assignment_dates=override_assignment_dates,
            needs_grading_count_by_section=needs_grading_count_by_section,
            all_dates=all_dates,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.get_assignment(**params)

    async def create_assignment(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        name: Annotated[str, Field(description="Assignment name")],
        submission_types: Annotated[
            list[
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
            Field(description="List of supported submission types"),
        ],
        position: Annotated[
            int | None,
            Field(description="Position in assignment group"),
        ] = None,
        allowed_extensions: Annotated[
            list[str] | None,
            Field(description="Allowed file extensions for online_upload"),
        ] = None,
        turnitin_enabled: Annotated[
            bool | None,
            Field(description="Enable Turnitin submissions"),
        ] = None,
        vericite_enabled: Annotated[
            bool | None,
            Field(description="Enable VeriCite submissions"),
        ] = None,
        turnitin_settings: Annotated[
            dict | None,
            Field(description="Turnitin configuration settings"),
        ] = None,
        integration_data: Annotated[
            str | None,
            Field(description="SIS integration data (JSON string)"),
        ] = None,
        integration_id: Annotated[
            str | None,
            Field(description="Third party integration ID"),
        ] = None,
        peer_reviews: Annotated[
            bool | None,
            Field(description="Enable peer reviews"),
        ] = None,
        automatic_peer_reviews: Annotated[
            bool | None,
            Field(description="Automatically assign peer reviews"),
        ] = None,
        notify_of_update: Annotated[
            bool | None,
            Field(description="Send notification to students"),
        ] = None,
        group_category_id: Annotated[
            int | None,
            Field(description="Group assignment category ID"),
        ] = None,
        grade_group_students_individually: Annotated[
            bool | None,
            Field(description="Grade group members individually"),
        ] = None,
        external_tool_tag_attributes: Annotated[
            dict | None,
            Field(description="External tool parameters"),
        ] = None,
        points_possible: Annotated[
            float | None,
            Field(description="Maximum points possible"),
        ] = None,
        grading_type: Annotated[
            Literal[
                "pass_fail",
                "percent",
                "letter_grade",
                "gpa_scale",
                "points",
                "not_graded",
            ]
            | None,
            Field(description="Grading strategy"),
        ] = "points",
        due_at: Annotated[
            str | None,
            Field(description="Due date/time (ISO format)"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="Lock date/time (ISO format)"),
        ] = None,
        unlock_at: Annotated[
            str | None,
            Field(description="Unlock date/time (ISO format)"),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="Assignment description (HTML supported)"),
        ] = None,
        assignment_group_id: Annotated[
            int | None,
            Field(description="Assignment group ID"),
        ] = None,
        assignment_overrides: Annotated[
            list[dict] | None,
            Field(description="List of assignment overrides"),
        ] = None,
        only_visible_to_overrides: Annotated[
            bool | None,
            Field(description="Only visible to overrides"),
        ] = None,
        published: Annotated[
            bool | None,
            Field(description="Whether assignment is published"),
        ] = None,
        grading_standard_id: Annotated[
            int | None,
            Field(description="Grading standard ID"),
        ] = None,
        omit_from_final_grade: Annotated[
            bool | None,
            Field(description="Exclude from final grade"),
        ] = None,
        hide_in_gradebook: Annotated[
            bool | None,
            Field(description="Hide in gradebook"),
        ] = None,
        quiz_lti: Annotated[
            bool | None,
            Field(description="Use Quizzes 2 LTI tool"),
        ] = None,
        moderated_grading: Annotated[
            bool | None,
            Field(description="Enable moderated grading"),
        ] = None,
        grader_count: Annotated[
            int | None,
            Field(description="Number of provisional graders"),
        ] = None,
        final_grader_id: Annotated[
            int | None,
            Field(description="Final grader user ID"),
        ] = None,
        grader_comments_visible_to_graders: Annotated[
            bool | None,
            Field(description="Show grader comments to other graders"),
        ] = None,
        graders_anonymous_to_graders: Annotated[
            bool | None,
            Field(description="Hide grader identities from other graders"),
        ] = None,
        graders_names_visible_to_final_grader: Annotated[
            bool | None,
            Field(description="Show grader names to final grader"),
        ] = None,
        anonymous_grading: Annotated[
            bool | None,
            Field(description="Enable anonymous grading"),
        ] = None,
        allowed_attempts: Annotated[
            int | None,
            Field(description="Number of submission attempts (-1 for unlimited)"),
        ] = None,
        annotatable_attachment_id: Annotated[
            int | None,
            Field(description="Attachment ID for student annotation"),
        ] = None,
    ) -> dict:
        """Create a new assignment."""
        params = self._validate_params(
            course_id=course_id,
            name=name,
            submission_types=submission_types,
            position=position,
            allowed_extensions=allowed_extensions,
            turnitin_enabled=turnitin_enabled,
            vericite_enabled=vericite_enabled,
            turnitin_settings=turnitin_settings,
            integration_data=integration_data,
            integration_id=integration_id,
            peer_reviews=peer_reviews,
            automatic_peer_reviews=automatic_peer_reviews,
            notify_of_update=notify_of_update,
            group_category_id=group_category_id,
            grade_group_students_individually=grade_group_students_individually,
            external_tool_tag_attributes=external_tool_tag_attributes,
            points_possible=points_possible,
            grading_type=grading_type,
            due_at=datetime.fromisoformat(due_at) if due_at else None,
            lock_at=datetime.fromisoformat(lock_at) if lock_at else None,
            unlock_at=datetime.fromisoformat(unlock_at) if unlock_at else None,
            description=description,
            assignment_group_id=assignment_group_id,
            assignment_overrides=assignment_overrides,
            only_visible_to_overrides=only_visible_to_overrides,
            published=published,
            grading_standard_id=grading_standard_id,
            omit_from_final_grade=omit_from_final_grade,
            hide_in_gradebook=hide_in_gradebook,
            quiz_lti=quiz_lti,
            moderated_grading=moderated_grading,
            grader_count=grader_count,
            final_grader_id=final_grader_id,
            grader_comments_visible_to_graders=grader_comments_visible_to_graders,
            graders_anonymous_to_graders=graders_anonymous_to_graders,
            graders_names_visible_to_final_grader=graders_names_visible_to_final_grader,
            anonymous_grading=anonymous_grading,
            allowed_attempts=allowed_attempts,
            annotatable_attachment_id=annotatable_attachment_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.create_assignment(**params)

    async def update_assignment(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        assignment_id: Annotated[
            str | int, Field(description="The assignment ID to update")
        ],
        name: Annotated[
            str | None,
            Field(description="Assignment name"),
        ] = None,
        position: Annotated[
            int | None,
            Field(description="Position in assignment group"),
        ] = None,
        submission_types: Annotated[
            list[
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
            | None,
            Field(
                description="List of supported submission types (only if no student submissions)"
            ),
        ] = None,
        allowed_extensions: Annotated[
            list[str] | None,
            Field(description="Allowed file extensions for online_upload"),
        ] = None,
        turnitin_enabled: Annotated[
            bool | None,
            Field(description="Enable Turnitin submissions"),
        ] = None,
        vericite_enabled: Annotated[
            bool | None,
            Field(description="Enable VeriCite submissions"),
        ] = None,
        turnitin_settings: Annotated[
            dict | None,
            Field(description="Turnitin configuration settings"),
        ] = None,
        sis_assignment_id: Annotated[
            str | None,
            Field(description="SIS assignment ID"),
        ] = None,
        integration_data: Annotated[
            str | None,
            Field(description="SIS integration data (JSON string)"),
        ] = None,
        integration_id: Annotated[
            str | None,
            Field(description="Third party integration ID"),
        ] = None,
        peer_reviews: Annotated[
            bool | None,
            Field(description="Enable peer reviews"),
        ] = None,
        automatic_peer_reviews: Annotated[
            bool | None,
            Field(description="Automatically assign peer reviews"),
        ] = None,
        notify_of_update: Annotated[
            bool | None,
            Field(description="Send notification to students"),
        ] = None,
        group_category_id: Annotated[
            int | None,
            Field(description="Group assignment category ID"),
        ] = None,
        grade_group_students_individually: Annotated[
            bool | None,
            Field(description="Grade group members individually"),
        ] = None,
        external_tool_tag_attributes: Annotated[
            dict | None,
            Field(description="External tool parameters"),
        ] = None,
        points_possible: Annotated[
            float | None,
            Field(description="Maximum points possible"),
        ] = None,
        grading_type: Annotated[
            Literal[
                "pass_fail",
                "percent",
                "letter_grade",
                "gpa_scale",
                "points",
                "not_graded",
            ]
            | None,
            Field(description="Grading strategy"),
        ] = None,
        due_at: Annotated[
            str | None,
            Field(
                description="Due date/time (ISO format). Cannot be grater than than 'lock_at'"
            ),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(
                description="Lock date/time (ISO format). Cannot be smaller than 'unlock_at' or 'due_at'"
            ),
        ] = None,
        unlock_at: Annotated[
            str | None,
            Field(
                description="Unlock date/time (ISO format). Cannot be grater than 'lock_at'."
            ),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="Assignment description (HTML supported)"),
        ] = None,
        assignment_group_id: Annotated[
            int | None,
            Field(description="Assignment group ID"),
        ] = None,
        assignment_overrides: Annotated[
            list[dict] | None,
            Field(description="List of assignment overrides"),
        ] = None,
        only_visible_to_overrides: Annotated[
            bool | None,
            Field(description="Only visible to overrides"),
        ] = None,
        published: Annotated[
            bool | None,
            Field(description="Whether assignment is published"),
        ] = None,
        grading_standard_id: Annotated[
            int | None,
            Field(description="Grading standard ID"),
        ] = None,
        omit_from_final_grade: Annotated[
            bool | None,
            Field(description="Exclude from final grade"),
        ] = None,
        hide_in_gradebook: Annotated[
            bool | None,
            Field(description="Hide in gradebook"),
        ] = None,
        moderated_grading: Annotated[
            bool | None,
            Field(description="Enable moderated grading"),
        ] = None,
        grader_count: Annotated[
            int | None,
            Field(description="Number of provisional graders"),
        ] = None,
        final_grader_id: Annotated[
            int | None,
            Field(description="Final grader user ID"),
        ] = None,
        grader_comments_visible_to_graders: Annotated[
            bool | None,
            Field(description="Show grader comments to other graders"),
        ] = None,
        graders_anonymous_to_graders: Annotated[
            bool | None,
            Field(description="Hide grader identities from other graders"),
        ] = None,
        graders_names_visible_to_final_grader: Annotated[
            bool | None,
            Field(description="Show grader names to final grader"),
        ] = None,
        anonymous_grading: Annotated[
            bool | None,
            Field(description="Enable anonymous grading"),
        ] = None,
        allowed_attempts: Annotated[
            int | None,
            Field(
                description="Number of submission attempts (-1 or null for unlimited)"
            ),
        ] = None,
        annotatable_attachment_id: Annotated[
            int | None,
            Field(description="Attachment ID for student annotation"),
        ] = None,
        force_updated_at: Annotated[
            bool | None,
            Field(description="Force updated_at to be set even if no changes"),
        ] = None,
    ) -> dict:
        """Update an existing assignment."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            name=name,
            position=position,
            submission_types=submission_types,
            allowed_extensions=allowed_extensions,
            turnitin_enabled=turnitin_enabled,
            vericite_enabled=vericite_enabled,
            turnitin_settings=turnitin_settings,
            sis_assignment_id=sis_assignment_id,
            integration_data=integration_data,
            integration_id=integration_id,
            peer_reviews=peer_reviews,
            automatic_peer_reviews=automatic_peer_reviews,
            notify_of_update=notify_of_update,
            group_category_id=group_category_id,
            grade_group_students_individually=grade_group_students_individually,
            external_tool_tag_attributes=external_tool_tag_attributes,
            points_possible=points_possible,
            grading_type=grading_type,
            due_at=datetime.fromisoformat(due_at) if due_at else None,
            lock_at=datetime.fromisoformat(lock_at) if lock_at else None,
            unlock_at=datetime.fromisoformat(unlock_at) if unlock_at else None,
            description=description,
            assignment_group_id=assignment_group_id,
            assignment_overrides=assignment_overrides,
            only_visible_to_overrides=only_visible_to_overrides,
            published=published,
            grading_standard_id=grading_standard_id,
            omit_from_final_grade=omit_from_final_grade,
            hide_in_gradebook=hide_in_gradebook,
            moderated_grading=moderated_grading,
            grader_count=grader_count,
            final_grader_id=final_grader_id,
            grader_comments_visible_to_graders=grader_comments_visible_to_graders,
            graders_anonymous_to_graders=graders_anonymous_to_graders,
            graders_names_visible_to_final_grader=graders_names_visible_to_final_grader,
            anonymous_grading=anonymous_grading,
            allowed_attempts=allowed_attempts,
            annotatable_attachment_id=annotatable_attachment_id,
            force_updated_at=force_updated_at,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.update_assignment(**params)

    async def delete_assignment(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        assignment_id: Annotated[
            str | int, Field(description="The assignment ID to delete")
        ],
    ) -> dict:
        """Delete an assignment."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.delete_assignment(**params)

    async def duplicate_assignment(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        assignment_id: Annotated[
            str | int, Field(description="The assignment ID to duplicate")
        ],
        result_type: Annotated[
            Literal["Quiz"] | None,
            Field(
                description="If 'Quiz', response will be serialized into quiz format"
            ),
        ] = None,
    ) -> dict:
        """Duplicate an assignment."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            result_type=result_type,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.duplicate_assignment(**params)

    async def bulk_update_assignment_dates(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_updates: Annotated[
            list[dict],
            Field(
                description="List of assignment update objects with 'id' and 'all_dates' keys"
            ),
        ],
    ) -> dict:
        """Update due dates and availability dates for multiple assignments."""
        params = self._validate_params(
            course_id=course_id,
            assignment_updates=assignment_updates,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.bulk_update_assignment_dates(**params)


class AssignmentOverrideTools(ToolProvider):
    """Tools for managing Canvas assignment overrides."""

    def _register_tools(self):
        """Register all assignment override-related tools."""
        tools_to_register = [
            (self.list_assignment_overrides, {"assignment", "override"}),
            (self.get_assignment_override, {"assignment", "override"}),
            (self.create_assignment_override, {"assignment", "override"}),
            (self.update_assignment_override, {"assignment", "override"}),
            (self.delete_assignment_override, {"assignment", "override"}),
            (self.get_group_override_redirect, {"assignment", "override", "group"}),
            (self.get_section_override_redirect, {"assignment", "override", "section"}),
            (self.batch_retrieve_overrides, {"assignment", "override", "batch"}),
            (self.batch_create_overrides, {"assignment", "override", "batch"}),
            (self.batch_update_overrides, {"assignment", "override", "batch"}),
        ]
        
        for tool_func, tags in tools_to_register:
            wrapped_tool = self._wrap_tool_with_analytics(tool_func)
            self.mcp.tool(wrapped_tool, tags=tags)

    async def list_assignment_overrides(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_id: Annotated[str | int, Field(description="Assignment ID")],
    ) -> list[dict]:
        """List assignment overrides for an assignment."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.list_assignment_overrides(**params)

    async def get_assignment_override(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_id: Annotated[str | int, Field(description="Assignment ID")],
        override_id: Annotated[str | int, Field(description="Override ID")],
    ) -> dict:
        """Get a single assignment override."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            override_id=override_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.get_assignment_override(**params)

    async def create_assignment_override(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_id: Annotated[str | int, Field(description="Assignment ID")],
        student_ids: Annotated[
            list[int] | None,
            Field(description="IDs of target students (for adhoc overrides)"),
        ] = None,
        title: Annotated[
            str | None,
            Field(
                description="Title of adhoc override (required if student_ids provided)"
            ),
        ] = None,
        group_id: Annotated[
            int | None,
            Field(description="ID of target group (for group assignments)"),
        ] = None,
        course_section_id: Annotated[
            int | None,
            Field(description="ID of target section"),
        ] = None,
        due_at: Annotated[
            str | None,
            Field(description="Overridden due date (ISO format)"),
        ] = None,
        unlock_at: Annotated[
            str | None,
            Field(description="Overridden unlock date (ISO format)"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="Overridden lock date (ISO format)"),
        ] = None,
    ) -> dict:
        """Create an assignment override."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            student_ids=student_ids,
            title=title,
            group_id=group_id,
            course_section_id=course_section_id,
            due_at=datetime.fromisoformat(due_at) if due_at else None,
            unlock_at=datetime.fromisoformat(unlock_at) if unlock_at else None,
            lock_at=datetime.fromisoformat(lock_at) if lock_at else None,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.create_assignment_override(**params)

    async def update_assignment_override(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_id: Annotated[str | int, Field(description="Assignment ID")],
        override_id: Annotated[str | int, Field(description="Override ID")],
        student_ids: Annotated[
            list[int] | None,
            Field(
                description="IDs of target students (ignored unless override is adhoc)"
            ),
        ] = None,
        title: Annotated[
            str | None,
            Field(
                description="Title of adhoc override (ignored unless override is adhoc)"
            ),
        ] = None,
        due_at: Annotated[
            str | None,
            Field(
                description="Overridden due date (null to remove override) (ISO format)"
            ),
        ] = None,
        unlock_at: Annotated[
            str | None,
            Field(
                description="Overridden unlock date (null to remove override) (ISO format)"
            ),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(
                description="Overridden lock date (null to remove override) (ISO format)"
            ),
        ] = None,
    ) -> dict:
        """Update an assignment override."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            override_id=override_id,
            student_ids=student_ids,
            title=title,
            due_at=datetime.fromisoformat(due_at) if due_at else None,
            unlock_at=datetime.fromisoformat(unlock_at) if unlock_at else None,
            lock_at=datetime.fromisoformat(lock_at) if lock_at else None,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.update_assignment_override(**params)

    async def delete_assignment_override(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_id: Annotated[str | int, Field(description="Assignment ID")],
        override_id: Annotated[str | int, Field(description="Override ID")],
    ) -> dict:
        """Delete an assignment override."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            override_id=override_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.delete_assignment_override(**params)

    async def get_group_override_redirect(
        self,
        group_id: Annotated[str | int, Field(description="Group ID")],
        assignment_id: Annotated[str | int, Field(description="Assignment ID")],
    ) -> dict:
        """Redirect to the assignment override for a group."""
        params = self._validate_params(
            group_id=group_id,
            assignment_id=assignment_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.get_group_override_redirect(**params)

    async def get_section_override_redirect(
        self,
        course_section_id: Annotated[str | int, Field(description="Course section ID")],
        assignment_id: Annotated[str | int, Field(description="Assignment ID")],
    ) -> dict:
        """Redirect to the assignment override for a section."""
        params = self._validate_params(
            course_section_id=course_section_id,
            assignment_id=assignment_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.get_section_override_redirect(**params)

    async def batch_retrieve_overrides(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_overrides: Annotated[
            list[dict],
            Field(description="List of dicts with 'id' and 'assignment_id' keys"),
        ],
    ) -> list[dict]:
        """Batch retrieve assignment overrides in a course."""
        params = self._validate_params(
            course_id=course_id,
            assignment_overrides=assignment_overrides,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.batch_retrieve_overrides(**params)

    async def batch_create_overrides(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_overrides: Annotated[
            list[dict],
            Field(description="List of override objects"),
        ],
    ) -> list[dict]:
        """Batch create assignment overrides in a course."""
        params = self._validate_params(
            course_id=course_id,
            assignment_overrides=assignment_overrides,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.batch_create_overrides(**params)

    async def batch_update_overrides(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_overrides: Annotated[
            list[dict],
            Field(
                description="List of override objects with 'id' and 'assignment_id' plus update attributes"
            ),
        ],
    ) -> list[dict]:
        """Batch update assignment overrides in a course."""
        params = self._validate_params(
            course_id=course_id,
            assignment_overrides=assignment_overrides,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignments.batch_update_overrides(**params)


class AssignmentGroupTools(ToolProvider):
    """Tools for managing Canvas assignment groups."""

    def _register_tools(self):
        """Register all assignment group-related tools."""
        tools_to_register = [
            (self.list_assignment_groups, {"assignment", "group"}),
            (self.get_assignment_group, {"assignment", "group"}),
            (self.create_assignment_group, {"assignment", "group"}),
            (self.update_assignment_group, {"assignment", "group"}),
            (self.delete_assignment_group, {"assignment", "group"}),
        ]
        
        for tool_func, tags in tools_to_register:
            wrapped_tool = self._wrap_tool_with_analytics(tool_func)
            self.mcp.tool(wrapped_tool, tags=tags)

    async def list_assignment_groups(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        include: Annotated[
            list[
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
            | None,
            Field(description="Associations to include with the group"),
        ] = None,
        assignment_ids: Annotated[
            list[str | int] | None,
            Field(
                description="Filter assignments by IDs (requires 'assignments' in include)"
            ),
        ] = None,
        exclude_assignment_submission_types: Annotated[
            list[
                Literal["online_quiz", "discussion_topic", "wiki_page", "external_tool"]
            ]
            | None,
            Field(description="Exclude assignments with specified submission types"),
        ] = None,
        override_assignment_dates: Annotated[
            bool | None,
            Field(description="Apply assignment overrides for each assignment"),
        ] = True,
        grading_period_id: Annotated[
            int | None,
            Field(description="Filter by grading period ID"),
        ] = None,
        scope_assignments_to_student: Annotated[
            bool | None,
            Field(description="Filter assignments to current user in grading period"),
        ] = False,
    ) -> list[dict]:
        """List assignment groups for a course."""
        params = self._validate_params(
            course_id=course_id,
            include=include,
            assignment_ids=assignment_ids,
            exclude_assignment_submission_types=exclude_assignment_submission_types,
            override_assignment_dates=override_assignment_dates,
            grading_period_id=grading_period_id,
            scope_assignments_to_student=scope_assignments_to_student,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignment_groups.list_assignment_groups(**params)

    async def get_assignment_group(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_group_id: Annotated[
            str | int, Field(description="Assignment Group ID")
        ],
        include: Annotated[
            list[
                Literal[
                    "assignments",
                    "discussion_topic",
                    "assignment_visibility",
                    "submission",
                    "score_statistics",
                ]
            ]
            | None,
            Field(description="Associations to include with the group"),
        ] = None,
        override_assignment_dates: Annotated[
            bool | None,
            Field(description="Apply assignment overrides for each assignment"),
        ] = True,
        grading_period_id: Annotated[
            int | None,
            Field(description="Filter by grading period ID"),
        ] = None,
    ) -> dict:
        """Get a specific assignment group."""
        params = self._validate_params(
            course_id=course_id,
            assignment_group_id=assignment_group_id,
            include=include,
            override_assignment_dates=override_assignment_dates,
            grading_period_id=grading_period_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignment_groups.get_assignment_group(**params)

    async def create_assignment_group(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        name: Annotated[str, Field(description="Assignment group name")],
        position: Annotated[
            int | None,
            Field(description="Position of this assignment group relative to others"),
        ] = None,
        group_weight: Annotated[
            float | None,
            Field(
                description="Percent of total grade this assignment group represents"
            ),
        ] = None,
        sis_source_id: Annotated[
            str | None,
            Field(description="SIS source ID of the assignment group"),
        ] = None,
        integration_data: Annotated[
            dict | None,
            Field(description="Integration data for the assignment group"),
        ] = None,
    ) -> dict:
        """Create a new assignment group."""
        params = self._validate_params(
            course_id=course_id,
            name=name,
            position=position,
            group_weight=group_weight,
            sis_source_id=sis_source_id,
            integration_data=integration_data,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignment_groups.create_assignment_group(**params)

    async def update_assignment_group(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_group_id: Annotated[
            str | int, Field(description="Assignment Group ID")
        ],
        name: Annotated[
            str | None,
            Field(description="Assignment group name"),
        ] = None,
        position: Annotated[
            int | None,
            Field(description="Position of this assignment group relative to others"),
        ] = None,
        group_weight: Annotated[
            float | None,
            Field(
                description="Percent of total grade this assignment group represents"
            ),
        ] = None,
        sis_source_id: Annotated[
            str | None,
            Field(description="SIS source ID of the assignment group"),
        ] = None,
        integration_data: Annotated[
            dict | None,
            Field(description="Integration data for the assignment group"),
        ] = None,
        rules: Annotated[
            dict | None,
            Field(description="Grading rules (drop_lowest, drop_highest, never_drop)"),
        ] = None,
    ) -> dict:
        """Update an existing assignment group."""
        params = self._validate_params(
            course_id=course_id,
            assignment_group_id=assignment_group_id,
            name=name,
            position=position,
            group_weight=group_weight,
            sis_source_id=sis_source_id,
            integration_data=integration_data,
            rules=rules,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignment_groups.update_assignment_group(**params)

    async def delete_assignment_group(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_group_id: Annotated[
            str | int, Field(description="Assignment Group ID to delete")
        ],
        move_assignments_to: Annotated[
            str | int | None,
            Field(description="ID of another assignment group to move assignments to"),
        ] = None,
    ) -> dict:
        """Delete an assignment group."""
        params = self._validate_params(
            course_id=course_id,
            assignment_group_id=assignment_group_id,
            move_assignments_to=move_assignments_to,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignment_groups.delete_assignment_group(**params)


class AssignmentExtensionTools(ToolProvider):
    """Tools for managing Canvas assignment extensions."""

    def _register_tools(self):
        """Register all assignment extension-related tools."""
        tools_to_register = [
            (self.set_assignment_extensions, {"assignment", "extension"}),
            (self.set_single_student_assignment_extension, {"assignment", "extension"}),
        ]
        
        for tool_func, tags in tools_to_register:
            wrapped_tool = self._wrap_tool_with_analytics(tool_func)
            self.mcp.tool(wrapped_tool, tags=tags)

    async def set_assignment_extensions(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_id: Annotated[str | int, Field(description="Assignment ID")],
        extensions: Annotated[
            list[dict],
            Field(
                description="List of extension objects with 'user_id' and 'extra_attempts' keys"
            ),
        ],
    ) -> dict:
        """Set extensions for student assignment submissions."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            extensions=extensions,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignment_extensions.set_assignment_extensions(**params)

    async def set_single_student_assignment_extension(
        self,
        course_id: Annotated[str | int, Field(description="Course ID")],
        assignment_id: Annotated[str | int, Field(description="Assignment ID")],
        user_id: Annotated[int, Field(description="Student user ID")],
        extra_attempts: Annotated[
            int, Field(description="Number of extra attempts to allow")
        ],
    ) -> dict:
        """Set extension for a single student assignment submission."""
        params = self._validate_params(
            course_id=course_id,
            assignment_id=assignment_id,
            user_id=user_id,
            extra_attempts=extra_attempts,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return assignment_extensions.set_single_student_assignment_extension(**params)
