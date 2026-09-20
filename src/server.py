"""Shared Canvas tools and resources, independent of the MCP transport."""

from fastmcp import FastMCP
from fastmcp.server.transforms.search import BM25SearchTransform
from fastmcp_tasks import TasksExtension
from fastmcp.server.middleware import Middleware
from ferpa import AUTHORING_RESOURCES, AUTHORING_TOOLS, ferpa_enabled, ferpa_scope

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
from tools.quiz_accommodations import QuizAccommodationTools
from tools.grade_posting import GradePostingTools
from tools.groups import GroupTools
from tools.attachments import AttachmentTools
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
For student quiz time extensions or 1.5x accommodations, search for quiz
accommodations to find canvas_plan_quiz_accommodations. Use the correct quiz engine.
For hidden grades, search for grade posting to find canvas_get_grade_posting_status
and canvas_plan_grade_release. Saving a grade or accepting a release job does not
prove student visibility; verify the per-student posting status.
For course student groups and group sets, search for student project groups.
Group sets are Canvas group categories; assignment groups are gradebook categories.
For assignment or submission attachment content, search for read assignment
attachments. Use canvas_read_assignment_attachment with a returned file ID;
follow text pagination and report extraction gaps before assessing the work.
Classic Quiz file-upload answers use canvas_read_quiz_attachment with the quiz
submission, question and file IDs. Discussion post/reply files use
canvas_read_discussion_attachment with topic, entry and file IDs. These readers
return image content blocks for visual inspection and spreadsheet cells/formulas.

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


class FerpaMiddleware(Middleware):
    """Keep the startup policy stable throughout discovery and nested calls."""

    def __init__(self, enabled: bool):
        self.enabled = enabled

    async def on_message(self, context, call_next):
        with ferpa_scope(self.enabled):
            return await call_next(context)


def create_server() -> FastMCP:
    # auth=None prevents FastMCP from loading an auth provider from inherited
    # environment settings. Canvas authenticates API calls with the user's token.
    enabled = ferpa_enabled()
    instructions = SERVER_INSTRUCTIONS if enabled else (
        "Canvas MCP is running locally with FERPA=false. Student grades, submissions, "
        "student records, Inbox, discussion entries, attachment readers, and student reports "
        "are disabled. Course-authoring tools remain available. Do not try alternate tools "
        "to retrieve disabled data. To enable it, the user must set FERPA=true in the "
        "server environment and restart. Discover advanced authoring tools with "
        "canvas_search_tools, execute them with canvas_call_tool, and use the "
        "canvas_plan_* / canvas_apply_change preview workflow for writes."
    )
    mcp = FastMCP(
        "Canvas-MCP",
        instructions=instructions,
        auth=None,
        mask_error_details=False,
    )
    mcp.add_middleware(FerpaMiddleware(enabled))
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
    QuizAccommodationTools(mcp)
    GradePostingTools(mcp)
    GroupTools(mcp)
    AttachmentTools(mcp)
    ReportingTools(mcp)
    register_content_creation_resource(mcp)
    register_instructor_experience(mcp)
    if not enabled:
        mcp.disable(components={"tool", "resource", "template", "prompt"})
        mcp.enable(names=set(AUTHORING_TOOLS), components={"tool"})
        mcp.enable(names=set(AUTHORING_RESOURCES), components={"resource", "template"})
        mcp.enable(names={"build_canvas_course"}, components={"prompt"})
    mcp.disable(names=DIRECT_WRITE_TOOLS, components={"tool"})
    mcp.add_transform(
        BM25SearchTransform(
            max_results=5,
            always_visible=([*AssistantTools.VISIBLE_NAMES, 'canvas_dashboard_data'] if enabled else
                            [name for name in AssistantTools.VISIBLE_NAMES if name in AUTHORING_TOOLS]),
            search_tool_name="canvas_search_tools",
            call_tool_name="canvas_call_tool",
        )
    )
    return mcp
