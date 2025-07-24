"""Course-related tools for Canvas MCP."""

from .base import ToolProvider
from canvasAPI.course import courses
from tools.getToken import get_user_token


class CourseTools(ToolProvider):
    """Tools for managing Canvas courses."""

    def _register_tools(self):
        """Register all course-related tools."""
        self.mcp.tool(self.list_courses, tags={"course"})

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
