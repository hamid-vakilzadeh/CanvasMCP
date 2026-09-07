"""Shared Canvas tools and resources, independent of the MCP transport."""

from fastmcp import FastMCP
from fastmcp.server.transforms.search import BM25SearchTransform
from fastmcp_tasks import TasksExtension

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
from tools.assistant import AssistantTools
from resources.content_creation_rules import register_content_creation_resource
from instructor_experience import register_instructor_experience
from reporting.tools import ReportingTools


SERVER_INSTRUCTIONS = """
You are connected directly to the user's Canvas LMS through a fully local stdio
server. Use the visible canvas_* tools for common instructor and course-authoring
workflows. Content creation is a primary capability: use the page, assignment,
announcement, discussion, module, quiz, file-upload, and course-copy planning
tools, the discussion entry/reply planner, Classic Quiz submission grading, or
the advanced rubric planner. Ask the user to review the returned preview before
calling canvas_apply_change with confirm=true.

For an action that is not initially visible, call canvas_search_tools using a
plain-language description. Execute discovered tools with canvas_call_tool.
Never use a direct Canvas mutation tool; all Canvas writes must use a canvas_plan_*
tool followed by canvas_apply_change. Call canvas_capabilities when unsure.

For student dashboards and comprehensive AI learning reviews, search for
student report or learning review. Canonical guidance is at canvas://reports/templates.
Dashboard selection uses direct read tools, without AI inference. Learning reviews
collect durable evidence, then require the AI client to read every batch and save
cited analysis before rendering. Accepted background work is not completed work.
Local report jobs and discussion queue updates do not write to Canvas. Search for
discussion watch to configure independent local polling and faculty-reviewed drafts.
""".strip()


# Existing direct write tools remain as implementation/reference code but are
# not model-visible because they bypass the plan/apply boundary.
DIRECT_WRITE_TOOLS = {
    "update_course", "reset_course_content",
    "create_module", "update_module", "delete_module", "relock_module",
    "create_module_item", "update_module_item", "delete_module_item",
    "duplicate_page", "update_front_page", "create_page", "update_page",
    "delete_page", "revert_to_revision",
    "create_quiz", "update_quiz", "delete_quiz", "create_quiz_question",
    "update_quiz_question", "delete_quiz_question", "create_quiz_question_group",
    "update_quiz_question_group", "delete_quiz_question_group",
    "reorder_quiz_question_group_questions",
    "create_discussion_topic", "update_discussion_topic", "delete_discussion_topic",
    "duplicate_discussion_topic", "reorder_pinned_topics", "post_entry", "post_reply",
    "update_entry", "delete_entry", "mark_entry_read", "mark_entry_unread", "rate_entry",
    "create_announcement",
    "create_assignment", "update_assignment", "delete_assignment", "duplicate_assignment",
    "bulk_update_assignment_dates", "create_assignment_override",
    "update_assignment_override", "delete_assignment_override", "batch_create_overrides",
    "batch_update_overrides", "create_assignment_group", "update_assignment_group",
    "delete_assignment_group", "set_assignment_extensions",
    "set_single_student_assignment_extension",
    "update_file", "delete_file", "reset_verifier", "upload_file_via_url",
    "complete_upload_from_url", "monitor_upload_progress", "copy_file",
    "create_folder", "update_folder", "delete_folder", "copy_folder",
    "get_media_folder",
    "set_usage_rights", "remove_usage_rights",
    "create_content_migration", "copy_course_content", "selective_course_copy",
    "execute_selective_migration",
}


def create_server() -> FastMCP:
    # auth=None prevents FastMCP from loading an auth provider from inherited
    # environment settings. Canvas authenticates API calls with the user's token.
    mcp = FastMCP(
        "Canvas-MCP",
        instructions=SERVER_INSTRUCTIONS,
        auth=None,
        mask_error_details=False,
    )
    mcp.add_extension(
        TasksExtension(
            url="memory://",
            name="canvas-mcp-local",
            worker_name="canvas-mcp-local",
            concurrency=4,
        )
    )
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
    AssistantTools(mcp)
    ReportingTools(mcp)
    register_content_creation_resource(mcp)
    register_instructor_experience(mcp)
    mcp.disable(names=DIRECT_WRITE_TOOLS, components={"tool"})
    mcp.add_transform(
        BM25SearchTransform(
            max_results=5,
            always_visible=[*AssistantTools.VISIBLE_NAMES, 'canvas_dashboard_data'],
            search_tool_name="canvas_search_tools",
            call_tool_name="canvas_call_tool",
        )
    )
    return mcp
