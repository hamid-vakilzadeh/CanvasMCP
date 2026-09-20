"""Opt-in exposure of student records; this setting does not certify compliance."""

from contextlib import contextmanager
from contextvars import ContextVar
import os
import re
from urllib.parse import parse_qs, unquote, urlsplit


DISABLED_MESSAGE = "Student-record access is disabled. Set FERPA=true in the server environment and restart to enable it."
_enabled: ContextVar[bool | None] = ContextVar("canvas_ferpa", default=None)

# An allowlist makes newly added tools unavailable in restricted mode until
# their arguments and return values have been reviewed.
AUTHORING_TOOLS = frozenset({
    "canvas_capabilities", "canvas_list_courses", "canvas_get_course_structure",
    "canvas_plan_announcement_change", "canvas_plan_page_change",
    "canvas_plan_assignment_change", "canvas_plan_discussion_change",
    "canvas_plan_module_change", "canvas_plan_quiz_change", "canvas_plan_file_upload",
    "canvas_plan_course_copy", "canvas_get_course_copy_selection",
    "canvas_plan_advanced_action", "canvas_apply_change",
    "list_courses", "get_course", "list_modules", "show_module",
    "list_module_items", "show_module_item", "show_front_page", "list_pages",
    "show_page", "list_revisions", "show_revision", "list_quizzes", "get_quiz",
    "list_quiz_questions", "get_quiz_question", "get_quiz_question_group",
    "list_discussion_topics", "get_discussion_topic", "list_announcements",
    "list_assignments", "get_assignment", "list_assignment_groups", "get_assignment_group",
    "get_quota", "list_files", "list_folders", "resolve_path", "get_folder", "list_licenses",
    "get_canvas_content_creation_rules", "search_canvas_reference",
    "list_content_migrations", "get_content_migration", "list_migration_systems",
    "get_migration_progress",
})
AUTHORING_RESOURCES = frozenset({
    "resource://content-creation-reference", "canvas://reference/content-creation",
    "canvas://courses/{course_id}/overview", "canvas://reference/actions/{domain}",
})
AUTHORING_ACTIONS = frozenset({
    "page_change", "assignment_change", "announcement_change", "discussion_change",
    "module_change", "module_item_change", "classic_quiz_change", "new_quiz_change",
    "file_upload", "course_copy", "create_rubric", "apply_course_copy_selection",
    "set_file_usage_rights", "remove_file_usage_rights",
    *(f"{operation}_{resource}" for operation in ("create", "update", "delete")
      for resource in ("assignment_group", "folder", "classic_quiz_question", "classic_quiz_question_group")),
})
STUDENT_FIELDS = frozenset({
    "submission", "submissions", "submission_history", "submission_comments", "submission_data",
    "quiz_submissions", "rubric_assessment", "rubric_assessments", "peer_reviews",
    "enrollments", "enrollment", "observed_users", "grades", "grade", "score",
    "entered_grade", "entered_score", "current_grade", "final_grade", "current_score", "final_score",
    "unposted_current_grade", "unposted_final_grade", "unposted_current_score", "unposted_final_score",
    "computed_current_score", "computed_final_score", "computed_current_grade", "computed_final_grade",
    "total_scores", "current_grading_period_scores", "course_progress", "student_progress",
    "discussion_subentry_count", "participants", "recent_replies", "entries", "replies",
    "last_reply_at", "last_reply", "assessment_requests", "all_dates", "overrides",
    "quiz_extensions", "score_statistics", "submission_statistics", "submissions_download_url",
    "quiz_statistics_url", "quiz_submission_versions_html_url",
})
STUDENT_ARGUMENTS = STUDENT_FIELDS | {
    "student_id", "student_ids", "user_id", "user_ids", "anonymous_id", "as_user_id",
    "quiz_submission_id", "quiz_submission_attempt", "submission_id",
    "scope_assignments_to_student", "student_inclusions", "submission_user",
}
_PRIVATE_PATH = re.compile(
    r"/(?:submissions|anonymous_submissions|quiz_submissions|students|enrollments|analytics|"
    r"outcome_results|outcome_rollups|conversations|entries|replies|entry_list|view|"
    r"extensions|accommodations|overrides|users|memberships)(?:/|$)|/api/graphql(?:/|$)"
)


def ferpa_enabled() -> bool:
    configured = _enabled.get()
    if configured is not None:
        return configured
    value = os.getenv("FERPA", "false").strip().lower()
    if value not in {"true", "false"}:
        raise ValueError("FERPA must be true or false (defaults to false).")
    return value == "true"


@contextmanager
def ferpa_scope(enabled: bool):
    token = _enabled.set(enabled)
    try:
        yield
    finally:
        _enabled.reset(token)


def require_ferpa() -> None:
    if not ferpa_enabled():
        raise ValueError(DISABLED_MESSAGE)


def check_arguments(arguments) -> None:
    """Reject student expansions, including nested and Rails bracket arguments."""
    if ferpa_enabled() or not isinstance(arguments, dict):
        return
    for key, value in arguments.items():
        parts = set(re.findall(r"[a-z_]+", str(key).lower()))
        parts |= {part.removeprefix("include_") for part in parts}
        if parts & STUDENT_ARGUMENTS and value not in (None, False, "", []):
            raise ValueError(DISABLED_MESSAGE)
        if "include" in parts:
            values = value if isinstance(value, list) else [value]
            if any(set(re.findall(r"[a-z_]+", str(item).lower())) & STUDENT_ARGUMENTS for item in values):
                raise ValueError(DISABLED_MESSAGE)
        if isinstance(value, dict):
            check_arguments(value)
        elif isinstance(value, list):
            for item in value:
                check_arguments(item)


def check_tool_access(name: str, arguments: dict | None = None) -> None:
    if ferpa_enabled():
        return
    if name not in AUTHORING_TOOLS:
        raise ValueError(DISABLED_MESSAGE)
    arguments = arguments or {}
    check_arguments(arguments)
    for key, value in arguments.items():
        if value is not None and (key.endswith("_id") or key == "url_or_id"):
            identifier = str(value)
            if identifier in {".", ".."} or any(c in identifier for c in "/?#\\%"):
                raise ValueError("Canvas IDs must be a single unencoded path segment")
    for key in ("context_type", "replacement_chain_context_type"):
        if arguments.get(key) not in (None, "courses"):
            raise ValueError(DISABLED_MESSAGE)
    if name == "canvas_plan_advanced_action" and str(arguments.get("action", "")).strip().lower() not in AUTHORING_ACTIONS:
        raise ValueError(DISABLED_MESSAGE)


def check_request(url: str, *payloads) -> None:
    """Also check resolved pagination URLs before either HTTP client sends them."""
    if ferpa_enabled():
        return
    parsed = urlsplit(url)
    path = unquote(parsed.path)
    if (_PRIVATE_PATH.search(path) or re.match(r"^/api/v1/files(?:/|$)", path)
            or any(part in {".", ".."} for part in path.split("/"))):
        raise ValueError(DISABLED_MESSAGE)
    check_arguments(parse_qs(parsed.query))
    for payload in payloads:
        check_arguments(payload)


def check_plan(plan) -> None:
    if ferpa_enabled():
        return
    if plan.action not in AUTHORING_ACTIONS or plan.local_draft:
        raise ValueError(DISABLED_MESSAGE)
    for condition in plan.preconditions:
        check_request(condition.endpoint, condition.params)
    for mutation in plan.mutations:
        check_request(mutation.endpoint, mutation.data, mutation.json_data)


def redact_student_fields(value):
    """Keep course/assignment definitions, excluding incidental student records."""
    if ferpa_enabled():
        return value
    if isinstance(value, dict):
        return {key: redact_student_fields(item) for key, item in value.items()
                if key not in STUDENT_FIELDS}
    if isinstance(value, list):
        return [redact_student_fields(item) for item in value]
    return value
