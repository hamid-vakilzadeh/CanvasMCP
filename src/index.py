from fastmcp import FastMCP
from utils import verify_key
from canvasAPI.course.courses import list_courses

mcp = FastMCP("Canvas-MCP")


@mcp.tool
async def list_courses_tool() -> str:
    """Get a list of all the courses the user has taught as a teacher.
    Use this function to get course information such as course name, course ID and term information.
    API key should be passed as a query parameter: ?apikey=your_key
    """
    # Extract API key from HTTP request
    try:
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()

        if request and hasattr(request, "query_params"):
            apikey = request.query_params.get("apikey")
        else:
            # Fallback: try to get from URL if available
            apikey = None
            if request and hasattr(request, "url"):
                import urllib.parse

                parsed = urllib.parse.urlparse(str(request.url))
                params = urllib.parse.parse_qs(parsed.query)
                apikey = params.get("apikey", [None])[0]

        if not apikey:
            raise ValueError("API key required in query parameters (?apikey=your_key)")

    except Exception as e:
        raise ValueError(f"Error extracting API key from request: {str(e)}")

    # Verify the API key
    try:
        verification_result = verify_key(apikey)
        if not verification_result.get("valid", False):
            raise ValueError("Invalid API key")

        # Extract Canvas credentials from meta object
        meta = verification_result.get("meta", {})
        base_url = meta.get("profileUrl")
        access_token = meta.get("profileAccessToken")

        if not base_url or not access_token:
            raise ValueError("Canvas credentials not found in API key metadata")

        # Call the Canvas API
        result = list_courses(
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
                "term_id": item.get("term", {}).get("id"),
                "term_name": item.get("term", {}).get("name"),
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

    except Exception as e:
        raise ValueError(f"Error processing request: {str(e)}")


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=3000, path="/mcp")
