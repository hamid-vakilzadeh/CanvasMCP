"""Course-related tools for Canvas MCP."""

from .base import ToolProvider
from canvasAPI.course import courses


class CourseTools(ToolProvider):
    """Tools for managing Canvas courses."""

    def _register_tools(self):
        """Register all course-related tools."""
        self.mcp.tool(self.list_courses, tags={"course"})

    async def list_courses(self) -> list[dict]:
        """Get a list of all the courses the user has taught as a teacher.
        Use this function to get course information such as course name, course ID and term information.
        """
        result = courses.list_courses(
            enrollment_type="teacher", include=["term"], all_pages=True
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

        return courses_list
