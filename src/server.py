"""Shared Canvas tools and resources, independent of the MCP transport."""

from fastmcp import FastMCP

from tools.courses import CourseTools
from tools.modules import ModuleTools
from tools.pages import PageTools
from tools.quizzes import QuizTools, QuizQuestionTools, QuizQuestionGroupTools
from tools.discussionTopics import DiscussionTools, DiscussionEntryTools, AnnouncementTools
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


def create_server() -> FastMCP:
    # auth=None prevents FastMCP from loading an auth provider from inherited
    # environment settings. Canvas authenticates API calls with the user's token.
    mcp = FastMCP("Canvas-MCP", auth=None)
    for provider in (
        CourseTools,
        ModuleTools,
        PageTools,
        QuizTools,
        QuizQuestionTools,
        QuizQuestionGroupTools,
        DiscussionTools,
        DiscussionEntryTools,
        AnnouncementTools,
        AssignmentTools,
        AssignmentOverrideTools,
        AssignmentGroupTools,
        AssignmentExtensionTools,
        FileTools,
        FolderTools,
        UsageRightsTools,
        CanvasReferenceTools,
        ContentMigrationTools,
    ):
        provider(mcp)
    register_content_creation_resource(mcp)
    return mcp
