"""Course-related tools for Canvas MCP."""

from typing import Annotated
from pydantic import Field

from .base import ToolProvider
from canvasAPI.course import courses
from tools.getToken import get_user_token


class CourseTools(ToolProvider):
    """Tools for managing Canvas courses."""

    def _register_tools(self):
        """Register all course-related tools."""
        # Wrap tools with analytics if enabled
        list_courses_tool = self._wrap_tool_with_analytics(self.list_courses)
        get_course_tool = self._wrap_tool_with_analytics(self.get_course)
        update_course_tool = self._wrap_tool_with_analytics(self.update_course)
        reset_course_tool = self._wrap_tool_with_analytics(self.reset_course_content)

        # Register wrapped tools
        self.mcp.tool(list_courses_tool, tags={"course"})
        self.mcp.tool(get_course_tool, tags={"course"})
        self.mcp.tool(update_course_tool, tags={"course", "update"})
        self.mcp.tool(reset_course_tool, tags={"course", "reset"})

    async def list_courses(self) -> str:
        """Get a list of all the courses the user has taught as a teacher.
        Use this function to get course information such as course name, course ID and term information.
        """

        base_url, access_token = get_user_token()

        result = courses.list_courses(
            base_url=base_url,
            access_token=access_token,
            enrollment_type="teacher",
            include=["term"],
            all_pages=True,
        )

        courses_list = [
            {
                "course_id": item["id"],
                "course_name": item["name"],
                "term_id": item["term"]["id"],
                "term_name": item["term"]["name"],
            }
            for item in result
        ]

        # Generate a markdown list of courses
        course_list_md = "\n".join(
            f"- {course['course_name']}, (Course ID: {course['course_id']}, Term: {course['term_name']})"
            for course in courses_list
        )
        course_list_md = f"# Courses List\n\n{course_list_md}"

        return course_list_md

    async def get_course(
        self,
        course_id: Annotated[str | int, Field(description="The course ID to retrieve")],
        include_needs_grading_count: Annotated[
            bool,
            Field(description="Include total number of submissions needing grading"),
        ] = False,
        include_syllabus_body: Annotated[
            bool,
            Field(description="Include user-generated HTML for the course syllabus"),
        ] = False,
        include_public_description: Annotated[
            bool,
            Field(
                description="Include user-generated text for the course public description"
            ),
        ] = False,
        include_total_scores: Annotated[
            bool, Field(description="Include student enrollment grade fields")
        ] = False,
        include_current_grading_period_scores: Annotated[
            bool, Field(description="Include current grading period grade information")
        ] = False,
        include_term: Annotated[
            bool, Field(description="Include enrollment term information")
        ] = False,
        include_account: Annotated[
            bool, Field(description="Include account JSON for the course")
        ] = False,
        include_course_progress: Annotated[
            bool, Field(description="Include progress through the course")
        ] = False,
        include_sections: Annotated[
            bool, Field(description="Include section enrollment information")
        ] = False,
        include_storage_quota_used_mb: Annotated[
            bool, Field(description="Include amount of storage space used by files")
        ] = False,
        include_total_students: Annotated[
            bool,
            Field(description="Include total number of active and invited students"),
        ] = False,
        include_passback_status: Annotated[
            bool, Field(description="Include grade passback status")
        ] = False,
        include_favorites: Annotated[
            bool, Field(description="Include if user has marked course as favorite")
        ] = False,
        include_teachers: Annotated[
            bool, Field(description="Include teacher information")
        ] = False,
        include_observed_users: Annotated[
            bool,
            Field(
                description="Include observed users data if current user has observer enrollment"
            ),
        ] = False,
        include_permissions: Annotated[
            bool,
            Field(
                description="Include permissions the current user has for the course"
            ),
        ] = False,
        include_course_image: Annotated[
            bool, Field(description="Include course image URL if set")
        ] = False,
        include_banner_image: Annotated[
            bool, Field(description="Include course banner image URL if set")
        ] = False,
        include_concluded: Annotated[
            bool, Field(description="Include whether course has been concluded")
        ] = False,
        include_lti_context_id: Annotated[
            bool, Field(description="Include course LTI tool ID")
        ] = False,
        include_post_manually: Annotated[
            bool, Field(description="Include course post policy setting")
        ] = False,
        teacher_limit: Annotated[
            int | None,
            Field(description="Maximum number of teacher enrollments to show"),
        ] = None,
    ) -> dict:
        """Get detailed information about a single course.

        This function retrieves comprehensive information about a course, including optional
        additional data such as enrollment information, grading details, and course settings.

        """
        base_url, access_token = get_user_token()

        try:
            # Build include list based on boolean parameters
            include_list = []
            if include_needs_grading_count:
                include_list.append("needs_grading_count")
            if include_syllabus_body:
                include_list.append("syllabus_body")
            if include_public_description:
                include_list.append("public_description")
            if include_total_scores:
                include_list.append("total_scores")
            if include_current_grading_period_scores:
                include_list.append("current_grading_period_scores")
            if include_term:
                include_list.append("term")
            if include_account:
                include_list.append("account")
            if include_course_progress:
                include_list.append("course_progress")
            if include_sections:
                include_list.append("sections")
            if include_storage_quota_used_mb:
                include_list.append("storage_quota_used_mb")
            if include_total_students:
                include_list.append("total_students")
            if include_passback_status:
                include_list.append("passback_status")
            if include_favorites:
                include_list.append("favorites")
            if include_teachers:
                include_list.append("teachers")
            if include_observed_users:
                include_list.append("observed_users")
            if include_permissions:
                include_list.append("permissions")
            if include_course_image:
                include_list.append("course_image")
            if include_banner_image:
                include_list.append("banner_image")
            if include_concluded:
                include_list.append("concluded")
            if include_lti_context_id:
                include_list.append("lti_context_id")
            if include_post_manually:
                include_list.append("post_manually")

            result = courses.get_course(
                base_url=base_url,
                access_token=access_token,
                course_id=course_id,
                include=include_list if include_list else None,
                teacher_limit=teacher_limit,
            )

            return {
                "success": True,
                "course": result,
                "message": f"Successfully retrieved course {course_id}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to retrieve course {course_id}",
            }

    async def update_course(
        self,
        course_id: Annotated[str | int, Field(description="The course ID to update")],
        name: Annotated[str | None, Field(description="The name of the course")] = None,
        course_code: Annotated[str | None, Field(description="The course code")] = None,
        start_at: Annotated[
            str | None,
            Field(
                description="Course start date in ISO8601 format (e.g., 2011-01-01T01:00Z)"
            ),
        ] = None,
        end_at: Annotated[
            str | None,
            Field(
                description="Course end date in ISO8601 format (e.g., 2011-01-01T01:00Z)"
            ),
        ] = None,
        license: Annotated[
            str | None,
            Field(
                description="Course license: private, cc_by_nc_nd, cc_by_nc_sa, cc_by_nc, cc_by_nd, cc_by_sa, cc_by, public_domain"
            ),
        ] = None,
        is_public: Annotated[
            bool | None,
            Field(
                description="Set to true if course is public to both authenticated and unauthenticated users"
            ),
        ] = None,
        is_public_to_auth_users: Annotated[
            bool | None,
            Field(
                description="Set to true if course is public only to authenticated users"
            ),
        ] = None,
        public_syllabus: Annotated[
            bool | None,
            Field(description="Set to true to make the course syllabus public"),
        ] = None,
        public_syllabus_to_auth: Annotated[
            bool | None,
            Field(
                description="Set to true to make the course syllabus public for authenticated users"
            ),
        ] = None,
        public_description: Annotated[
            str | None,
            Field(description="A publicly visible description of the course"),
        ] = None,
        allow_student_wiki_edits: Annotated[
            bool | None,
            Field(
                description="If true, students will be able to modify the course wiki"
            ),
        ] = None,
        allow_wiki_comments: Annotated[
            bool | None,
            Field(
                description="If true, course members will be able to comment on wiki pages"
            ),
        ] = None,
        allow_student_forum_attachments: Annotated[
            bool | None,
            Field(description="If true, students can attach files to forum posts"),
        ] = None,
        open_enrollment: Annotated[
            bool | None,
            Field(description="Set to true if the course is open enrollment"),
        ] = None,
        self_enrollment: Annotated[
            bool | None,
            Field(description="Set to true if the course is self enrollment"),
        ] = None,
        restrict_enrollments_to_course_dates: Annotated[
            bool | None,
            Field(
                description="Set to true to restrict user enrollments to the start and end dates"
            ),
        ] = None,
        term_id: Annotated[
            int | None,
            Field(description="The unique ID of the term to move the course to"),
        ] = None,
        sis_course_id: Annotated[
            str | None, Field(description="The unique SIS identifier")
        ] = None,
        integration_id: Annotated[
            str | None, Field(description="The unique Integration identifier")
        ] = None,
        hide_final_grades: Annotated[
            bool | None,
            Field(
                description="If true, totals in student grades summary will be hidden"
            ),
        ] = None,
        time_zone: Annotated[
            str | None,
            Field(
                description="The time zone for the course (IANA or Ruby on Rails format)"
            ),
        ] = None,
        apply_assignment_group_weights: Annotated[
            bool | None,
            Field(
                description="Set to true to weight final grade based on assignment group percentages"
            ),
        ] = None,
        storage_quota_mb: Annotated[
            int | None, Field(description="Storage quota for the course in megabytes")
        ] = None,
        event: Annotated[
            str | None,
            Field(
                description="Action to take: claim (unpublish), offer (publish), conclude, delete, undelete"
            ),
        ] = None,
        default_view: Annotated[
            str | None,
            Field(
                description="Default page type: feed, wiki, modules, syllabus, assignments"
            ),
        ] = None,
        syllabus_body: Annotated[
            str | None,
            Field(description="The syllabus body for the course (HTML supported)"),
        ] = None,
        syllabus_course_summary: Annotated[
            bool | None,
            Field(
                description="Display course summary on syllabus page (assignments and calendar events)"
            ),
        ] = None,
        grading_standard_id: Annotated[
            int | None,
            Field(description="The grading standard ID to set for the course"),
        ] = None,
        grade_passback_setting: Annotated[
            str | None,
            Field(description="Grade passback setting: 'nightly_sync' or empty string"),
        ] = None,
        course_format: Annotated[
            str | None, Field(description="Course format: on_campus or online")
        ] = None,
        image_url: Annotated[
            str | None,
            Field(description="URL to an image to be used as the course image"),
        ] = None,
        remove_image: Annotated[
            bool | None, Field(description="Set to true to remove the course image")
        ] = None,
        remove_banner_image: Annotated[
            bool | None,
            Field(description="Set to true to remove the course banner image"),
        ] = None,
        blueprint: Annotated[
            bool | None, Field(description="Set the course as a blueprint course")
        ] = None,
        homeroom_course: Annotated[
            bool | None,
            Field(
                description="Set the course as a homeroom course (Canvas for Elementary)"
            ),
        ] = None,
        template: Annotated[
            bool | None, Field(description="Enable or disable the course as a template")
        ] = None,
        course_color: Annotated[
            str | None,
            Field(
                description="Hex color code for the course (e.g., #FF5733) - Canvas for Elementary"
            ),
        ] = None,
        friendly_name: Annotated[
            str | None,
            Field(description="Friendly name for the course - Canvas for Elementary"),
        ] = None,
        enable_course_paces: Annotated[
            bool | None, Field(description="Enable or disable Course Pacing")
        ] = None,
        conditional_release: Annotated[
            bool | None,
            Field(
                description="Enable or disable individual learning paths based on assessment"
            ),
        ] = None,
        post_manually: Annotated[
            bool | None,
            Field(description="When true, all grades must be posted manually"),
        ] = None,
        override_sis_stickiness: Annotated[
            bool, Field(description="Override SIS sticky fields (default: true)")
        ] = True,
    ) -> dict:
        """Update an existing course with new information and settings.

        This function allows you to modify various aspects of a course including basic information,
        enrollment settings, grading configuration, and advanced features. Only the parameters you
        specify will be updated - all others will remain unchanged.

        """
        base_url, access_token = get_user_token()

        try:
            result = courses.update_course(
                base_url=base_url,
                access_token=access_token,
                course_id=course_id,
                name=name,
                course_code=course_code,
                start_at=start_at,
                end_at=end_at,
                license=license,
                is_public=is_public,
                is_public_to_auth_users=is_public_to_auth_users,
                public_syllabus=public_syllabus,
                public_syllabus_to_auth=public_syllabus_to_auth,
                public_description=public_description,
                allow_student_wiki_edits=allow_student_wiki_edits,
                allow_wiki_comments=allow_wiki_comments,
                allow_student_forum_attachments=allow_student_forum_attachments,
                open_enrollment=open_enrollment,
                self_enrollment=self_enrollment,
                restrict_enrollments_to_course_dates=restrict_enrollments_to_course_dates,
                term_id=term_id,
                sis_course_id=sis_course_id,
                integration_id=integration_id,
                hide_final_grades=hide_final_grades,
                time_zone=time_zone,
                apply_assignment_group_weights=apply_assignment_group_weights,
                storage_quota_mb=storage_quota_mb,
                event=event,
                default_view=default_view,
                syllabus_body=syllabus_body,
                syllabus_course_summary=syllabus_course_summary,
                grading_standard_id=grading_standard_id,
                grade_passback_setting=grade_passback_setting,
                course_format=course_format,
                image_url=image_url,
                remove_image=remove_image,
                remove_banner_image=remove_banner_image,
                blueprint=blueprint,
                homeroom_course=homeroom_course,
                template=template,
                course_color=course_color,
                friendly_name=friendly_name,
                enable_course_paces=enable_course_paces,
                conditional_release=conditional_release,
                post_manually=post_manually,
                override_sis_stickiness=override_sis_stickiness,
            )

            return {
                "success": True,
                "course": result,
                "message": f"Successfully updated course {course_id}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to update course {course_id}",
            }

    async def reset_course_content(
        self,
        course_id: Annotated[str | int, Field(description="The course ID to reset")],
    ) -> dict:
        """Reset course content (deletes current course and creates new equivalent).

        This operation will completely delete the current course and create a new
        equivalent course with the same settings but no content (assignments,
        discussions, pages, etc.). This is useful for reusing course shells.

        ⚠️ WARNING: This operation is irreversible and will permanently delete
        all course content including assignments, discussions, pages, files, etc.

        """
        base_url, access_token = get_user_token()

        try:
            result = courses.reset_course_content(
                base_url=base_url, access_token=access_token, course_id=course_id
            )

            return {
                "success": True,
                "message": f"Course {course_id} content has been reset successfully",
                "new_course": result,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to reset course {course_id} content",
            }
