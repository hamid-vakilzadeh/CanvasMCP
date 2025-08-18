import logging
from fastmcp import FastMCP
from fastmcp.utilities.logging import configure_logging
from fastapi import Response
import httpx

from tools.courses import CourseTools
from tools.modules import ModuleTools
from tools.pages import PageTools
from tools.quizzes import QuizTools, QuizQuestionTools, QuizQuestionGroupTools
from tools.discussionTopics import (
    DiscussionTools,
    DiscussionEntryTools,
    AnnouncementTools,
)
from tools.assignments import (
    AssignmentTools,
    AssignmentOverrideTools,
    AssignmentGroupTools,
    AssignmentExtensionTools,
)
from tools.files import FileTools, FolderTools, UsageRightsTools
from tools.canvasGuides import CanvasReferenceTools
from tools.contentMigration import ContentMigrationTools

from resources.content_creation_rules import register_content_creation_resource

from session_middleware import SessionAuthMiddleware, SessionManagementMiddleware
from analytics_middleware import AnalyticsMiddleware


# Configure FastMCP logging - reduce verbosity
configure_logging(level="WARNING", enable_rich_tracebacks=False)

# Reduce noise from other loggers
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)

mcp = FastMCP("Canvas-MCP")

# Add session management middleware
mcp.add_middleware(SessionManagementMiddleware())  # Handles session lifecycle
mcp.add_middleware(SessionAuthMiddleware())  # Handles authentication
mcp.add_middleware(AnalyticsMiddleware())  # Handles analytics tracking


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request):
    """Proxy favicon from victorai.bot"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://victorai.bot/favicon.ico")
            return Response(
                content=response.content,
                media_type="image/x-icon",
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        return Response(status_code=404)


CourseTools(mcp)
ModuleTools(mcp)
PageTools(mcp)
QuizTools(mcp)
QuizQuestionTools(mcp)
QuizQuestionGroupTools(mcp)
DiscussionTools(mcp)
DiscussionEntryTools(mcp)
AnnouncementTools(mcp)
AssignmentTools(mcp)
AssignmentOverrideTools(mcp)
AssignmentGroupTools(mcp)
AssignmentExtensionTools(mcp)
FileTools(mcp)
FolderTools(mcp)
UsageRightsTools(mcp)
CanvasReferenceTools(mcp)
ContentMigrationTools(mcp)

# Register resources
register_content_creation_resource(mcp)

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=3000,
        path="/mcp",
        stateless_http=False,
        log_level="WARNING",  # Reduce server verbosity
    )
