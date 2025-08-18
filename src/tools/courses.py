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
        reset_course_tool = self._wrap_tool_with_analytics(self.reset_course_content)
        
        # Register wrapped tools
        self.mcp.tool(list_courses_tool, tags={"course"})
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

        Args:
            course_id: The ID of the course to reset

        Returns:
            Dictionary containing the new course information

        Example:
            await reset_course_content(12345)
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
