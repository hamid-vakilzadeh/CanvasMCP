from fastmcp import FastMCP
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
from tools.canvasGuides import CanvasReferenceTools
from tools.contentMigration import ContentMigrationTools

from resources.content_creation_rules import register_content_creation_resource

from session_middleware import SessionAuthMiddleware, SessionManagementMiddleware

mcp = FastMCP("Canvas-MCP")

# Add session management middleware
mcp.add_middleware(SessionManagementMiddleware())  # Handles session lifecycle
mcp.add_middleware(SessionAuthMiddleware())  # Handles authentication

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
CanvasReferenceTools(mcp)
ContentMigrationTools(mcp)

# Register resources
register_content_creation_resource(mcp)

if __name__ == "__main__":
    mcp.run(
        transport="http", host="0.0.0.0", port=3000, path="/mcp", stateless_http=False
    )
