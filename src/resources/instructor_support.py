"""Compact Canvas resources for instructor and course-authoring workflows."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError

from canvas_client import AsyncCanvasClient


RESOURCE_ANNOTATIONS = {"audience": ["assistant"], "priority": 0.9}


ACTION_DOMAINS: dict[str, dict[str, Any]] = {
    "courses": {
        "summary": "Inspect a course and its teaching structure.",
        "visible_tools": ["canvas_list_courses", "canvas_get_course_structure"],
        "search_examples": ["course settings", "course activity", "course permissions"],
    },
    "students": {
        "summary": "Review rosters, enrollment context, progress, and engagement evidence.",
        "visible_tools": [
            "canvas_list_course_people",
            "canvas_get_student_snapshot",
            "canvas_analyze_student_engagement",
        ],
        "search_examples": ["student progress", "enrollments", "student activity"],
    },
    "grading": {
        "summary": "Review submissions and prepare individual grades or feedback.",
        "visible_tools": [
            "canvas_list_grading_queue",
            "canvas_get_submission_review",
            "canvas_get_quiz_submission_review",
            "canvas_plan_grade_change",
            "canvas_plan_quiz_submission_grade",
            "canvas_apply_change",
        ],
        "write_workflow": "Plan the grade or comment, review the preview, then apply it with confirm=true.",
    },
    "inbox": {
        "summary": "Read Canvas Inbox conversations and prepare private outreach.",
        "visible_tools": [
            "canvas_list_inbox",
            "canvas_get_conversation",
            "canvas_plan_communication",
            "canvas_apply_change",
        ],
        "write_workflow": "Bulk outreach creates a separate private conversation for each student.",
    },
    "pages": {
        "summary": "Create and maintain accessible Canvas pages.",
        "visible_tools": ["canvas_plan_page_change", "canvas_apply_change"],
        "reference": "canvas://reference/content-creation",
        "search_examples": ["list pages", "get page", "page revisions", "front page"],
    },
    "assignments": {
        "summary": "Create and maintain assignments, dates, and overrides.",
        "visible_tools": ["canvas_plan_assignment_change", "canvas_apply_change"],
        "search_examples": ["list assignments", "assignment overrides", "assignment groups"],
    },
    "rubrics": {
        "summary": "Create an analytic rubric, attach it to an assignment, and grade with it.",
        "visible_tools": [
            "canvas_plan_advanced_action",
            "canvas_plan_grade_change",
            "canvas_apply_change",
        ],
        "write_workflow": "Plan create_rubric with criteria and ratings, review the point totals, then apply it.",
    },
    "announcements": {
        "summary": "Create, schedule, update, and remove course announcements.",
        "visible_tools": ["canvas_plan_announcement_change", "canvas_apply_change"],
        "search_examples": ["list announcements", "announcement sections"],
    },
    "discussions": {
        "summary": "Create and maintain discussion topics and their entries.",
        "visible_tools": [
            "canvas_plan_discussion_change",
            "canvas_plan_discussion_entry",
            "canvas_apply_change",
        ],
        "search_examples": ["list discussions", "discussion entries", "discussion replies"],
    },
    "modules": {
        "summary": "Build course modules and organize module items.",
        "visible_tools": ["canvas_plan_module_change", "canvas_apply_change"],
        "search_examples": ["list module items", "module prerequisites", "module completion"],
    },
    "quizzes": {
        "summary": "Create quizzes and review or grade completed Classic Quiz attempts.",
        "visible_tools": [
            "canvas_plan_quiz_change",
            "canvas_get_quiz_submission_review",
            "canvas_plan_quiz_submission_grade",
            "canvas_apply_change",
        ],
        "search_examples": ["quiz questions", "question groups", "quiz reports", "quiz submissions"],
    },
    "files": {
        "summary": "Inspect course files and prepare secure local-file uploads.",
        "visible_tools": ["canvas_plan_file_upload", "canvas_apply_change"],
        "search_examples": ["list files", "folders", "usage rights"],
    },
    "course-copies": {
        "summary": "Prepare complete or selective course copies and monitor migrations.",
        "visible_tools": ["canvas_plan_course_copy", "canvas_apply_change"],
        "search_examples": [
            "content migrations",
            "course copy selective data",
            "apply course copy selection",
            "migration progress",
        ],
    },
}


def _compact(items: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{key: item.get(key) for key in fields if key in item} for item in items]


def _warning(section: str, error: BaseException) -> dict[str, str]:
    return {"section": section, "error": str(error)}


def _resource_id(value: str) -> str:
    lowered = value.lower()
    if (
        not value
        or value in {".", ".."}
        or any(character in value for character in "/?#\\")
        or "%2f" in lowered
        or "%5c" in lowered
    ):
        raise ResourceError("Canvas IDs must be a single URL path segment")
    return value


def _content_reference() -> str:
    path = Path(__file__).parent / "content" / "canvas_content_creation_reference.md"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ResourceError(f"Could not read the Canvas content reference: {exc}") from exc
    if not content.strip():
        raise ResourceError("Canvas content creation reference is empty")
    return content


def register_instructor_resources(mcp: FastMCP) -> None:
    """Register compact dynamic views and discoverable Canvas references."""

    @mcp.resource(
        "canvas://courses/{course_id}/overview",
        name="canvas_course_overview",
        title="Canvas Course Overview",
        description="Compact course metadata and teaching structure for an instructor.",
        mime_type="application/json",
        tags={"canvas", "course", "instructor"},
        annotations=RESOURCE_ANNOTATIONS,
    )
    async def canvas_course_overview(course_id: str) -> dict[str, Any]:
        course_id = _resource_id(str(course_id))
        warnings: list[dict[str, str]] = []
        async with AsyncCanvasClient.from_environment() as client:
            course = await client.get(
                f"/api/v1/courses/{course_id}",
                {"include[]": ["term", "teachers", "course_image", "public_description"]},
            )
            requests = {
                "modules": client.page(
                    f"/api/v1/courses/{course_id}/modules",
                    params={"include[]": ["items", "content_details"]},
                    limit=50,
                ),
                "pages": client.page(f"/api/v1/courses/{course_id}/pages", limit=50),
                "assignments": client.page(
                    f"/api/v1/courses/{course_id}/assignments", limit=50
                ),
                "quizzes": client.page(f"/api/v1/courses/{course_id}/quizzes", limit=50),
            }
            results = await asyncio.gather(*requests.values(), return_exceptions=True)

        sections: dict[str, Any] = {}
        truncated: dict[str, bool] = {}
        fields = {
            "modules": ("id", "name", "position", "published", "items"),
            "pages": ("page_id", "url", "title", "published", "updated_at"),
            "assignments": ("id", "name", "due_at", "points_possible", "published"),
            "quizzes": ("id", "title", "quiz_type", "due_at", "published"),
        }
        for section, result in zip(requests, results, strict=True):
            if isinstance(result, Exception):
                warnings.append(_warning(section, result))
                sections[section] = []
                truncated[section] = False
                continue
            sections[section] = _compact(result["items"], fields[section])
            truncated[section] = bool(result.get("next_cursor"))

        course_fields = (
            "id",
            "name",
            "course_code",
            "workflow_state",
            "start_at",
            "end_at",
            "term",
            "teachers",
            "image_download_url",
            "public_description",
        )
        return {
            "course": {key: course.get(key) for key in course_fields if key in course},
            **sections,
            "truncated": truncated,
            "warnings": warnings,
        }

    @mcp.resource(
        "canvas://courses/{course_id}/students/{student_id}/snapshot",
        name="canvas_student_snapshot",
        title="Canvas Student Snapshot",
        description="Enrollment, progress, submission, and activity evidence for one student.",
        mime_type="application/json",
        tags={"canvas", "student", "instructor"},
        annotations=RESOURCE_ANNOTATIONS,
    )
    async def canvas_student_snapshot(course_id: str, student_id: str) -> dict[str, Any]:
        course_id, student_id = _resource_id(str(course_id)), _resource_id(str(student_id))
        requests: dict[str, Any]
        async with AsyncCanvasClient.from_environment() as client:
            requests = {
                "enrollments": client.get(
                    f"/api/v1/courses/{course_id}/enrollments",
                    {"user_id": student_id, "type[]": ["StudentEnrollment"]},
                ),
                "progress": client.get(
                    f"/api/v1/courses/{course_id}/users/{student_id}/progress"
                ),
                "submissions": client.page(
                    f"/api/v1/courses/{course_id}/students/submissions",
                    params={"student_ids[]": [student_id], "include[]": ["assignment"]},
                    limit=100,
                ),
                "activity": client.get(
                    f"/api/v1/courses/{course_id}/analytics/users/{student_id}/activity"
                ),
            }
            results = await asyncio.gather(*requests.values(), return_exceptions=True)

        snapshot: dict[str, Any] = {
            "course_id": course_id,
            "student_id": student_id,
            "warnings": [],
        }
        for section, result in zip(requests, results, strict=True):
            if isinstance(result, Exception):
                snapshot["warnings"].append(_warning(section, result))
            else:
                snapshot[section] = result
        submission_page = snapshot.get("submissions")
        submissions = submission_page.get("items", []) if isinstance(submission_page, dict) else []
        if isinstance(submissions, list):
            snapshot["submissions"] = _compact(
                submissions,
                (
                    "id",
                    "assignment_id",
                    "workflow_state",
                    "submitted_at",
                    "late",
                    "missing",
                    "score",
                    "grade",
                    "assignment",
                ),
            )
            snapshot["submissions_next_cursor"] = submission_page.get("next_cursor")
        return snapshot

    @mcp.resource(
        "canvas://reference/actions/{domain}",
        name="canvas_action_reference",
        title="Canvas Action Reference",
        description="Tool and discovery guidance for a Canvas action domain.",
        mime_type="application/json",
        tags={"canvas", "actions", "reference"},
        annotations=RESOURCE_ANNOTATIONS,
    )
    async def canvas_action_reference(domain: str) -> dict[str, Any]:
        normalized = domain.strip().lower().replace("_", "-")
        if normalized not in ACTION_DOMAINS:
            supported = ", ".join(sorted(ACTION_DOMAINS))
            raise ResourceError(
                f"Unknown Canvas action domain '{domain}'. Supported domains: {supported}"
            )
        return {
            "domain": normalized,
            **ACTION_DOMAINS[normalized],
            "discovery": "Use canvas_search_tools when the visible tools do not cover the action.",
            "mutation_rule": "Writes must be previewed by a canvas_plan_* tool and executed with canvas_apply_change.",
        }

    @mcp.resource(
        "canvas://reference/content-creation",
        name="canvas_content_creation_reference",
        title="Canvas Content Creation Reference",
        description="Canvas-safe HTML, CSS, layout, accessibility, and content guidance.",
        mime_type="text/markdown",
        tags={"canvas", "content-creation", "reference"},
        annotations=RESOURCE_ANNOTATIONS,
        meta={"alias_of": "resource://content-creation-reference"},
    )
    async def canvas_content_creation_reference() -> str:
        return _content_reference()
