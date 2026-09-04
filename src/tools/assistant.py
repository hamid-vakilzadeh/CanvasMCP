"""Compact instructor and authoring tools for the local Canvas MCP server."""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import math
import mimetypes
import re
from datetime import timedelta
from functools import wraps
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import quote

import httpx2
from fastmcp import FastMCP
from fastmcp.dependencies import Progress
from fastmcp.tools import ToolResult
from fastmcp.utilities.tasks import TaskConfig
from mcp.types import TextContent, ToolAnnotations
from pydantic import BaseModel, Field

from action_plans import Mutation, Precondition, fingerprint, plan_store
from canvas_client import AsyncCanvasClient, CanvasAPIError


READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)
PLAN_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)
MUTATING = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)
BACKGROUND = TaskConfig(mode="optional", poll_interval=timedelta(seconds=2))


def _assistant_tool(fn):
    """Return stable, structured errors without changing the public signature."""

    @wraps(fn)
    async def wrapped(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except CanvasAPIError as exc:
            error = {
                "code": exc.code,
                "message": exc.detail,
                "status": exc.status,
                "endpoint": exc.endpoint,
            }
        except ValueError as exc:
            error = {"code": "invalid_request", "message": str(exc)}
        payload = {"error": error}
        return ToolResult(
            content=[TextContent(type="text", text=json.dumps(payload))],
            structured_content=payload,
            is_error=True,
        )

    return wrapped


def _sid(value: str | int) -> str:
    result = str(value)
    lowered = result.lower()
    if (
        not result
        or result in {".", ".."}
        or any(character in result for character in "/?#\\")
        or "%2f" in lowered
        or "%5c" in lowered
    ):
        raise ValueError("Canvas IDs must be a single URL path segment")
    return result


def _form_payload(
    payload: dict[str, Any], prefix: str | None = None
) -> dict[str, Any]:
    """Flatten friendly nested values into Canvas/Rails bracket parameters."""
    result: dict[str, Any] = {}

    def add(path: str, value: Any) -> None:
        if isinstance(value, dict):
            if not value:
                result[path] = ""
            for key, nested in value.items():
                add(f"{path}[{key}]", nested)
        elif isinstance(value, list):
            if value and any(isinstance(item, (dict, list)) for item in value):
                for index, nested in enumerate(value):
                    add(f"{path}[{index}]", nested)
            else:
                array_path = path if path.endswith("[]") else f"{path}[]"
                result[array_path] = value if value else ""
        else:
            result[path] = "" if value is None else value

    for key, value in payload.items():
        path = key if prefix is None or "[" in key else f"{prefix}[{key}]"
        add(path, value)
    return result


def _compact(items: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{key: item.get(key) for key in fields if key in item} for item in items]


def _plain_text(value: Any, limit: int = 20_000) -> str | None:
    """Make Canvas HTML readable in plans without silently dropping long answers."""
    if value is None:
        return None
    cleaned = html.unescape(re.sub(r"<[^>]+>", " ", str(value)))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "…"


class QuizQuestionGradeUpdate(BaseModel):
    """One manually graded Classic Quiz question score or feedback change."""

    question_id: str | int
    score: float | None = None
    comment: str | None = None


def _file_fingerprint(path: Path) -> tuple[int, int, str]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, digest.hexdigest()


async def _bounded_pages(
    client: AsyncCanvasClient,
    endpoint: str,
    *,
    params: dict[str, Any] | None = None,
    max_pages: int = 5,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], str | None]:
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(max_pages):
        page = await client.page(
            endpoint, params=params, cursor=cursor, limit=page_size
        )
        items.extend(page["items"])
        cursor = page.get("next_cursor")
        if not cursor:
            break
    return items, cursor


def _canvas_current_score(enrollments: list[dict[str, Any]]) -> float | None:
    for enrollment in enrollments:
        grades = enrollment.get("grades") or {}
        raw = grades.get("current_score", enrollment.get("computed_current_score"))
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
    return None


class AssistantTools:
    """Register the small, always-visible Canvas assistant surface."""

    VISIBLE_NAMES = [
        "canvas_capabilities",
        "canvas_list_courses",
        "canvas_get_course_structure",
        "canvas_list_course_people",
        "canvas_get_student_snapshot",
        "canvas_analyze_student_engagement",
        "canvas_list_grading_queue",
        "canvas_get_submission_review",
        "canvas_get_quiz_submission_review",
        "canvas_list_inbox",
        "canvas_get_conversation",
        "canvas_plan_communication",
        "canvas_plan_announcement_change",
        "canvas_plan_page_change",
        "canvas_plan_assignment_change",
        "canvas_plan_discussion_change",
        "canvas_plan_discussion_entry",
        "canvas_plan_module_change",
        "canvas_plan_quiz_change",
        "canvas_plan_file_upload",
        "canvas_plan_course_copy",
        "canvas_plan_grade_change",
        "canvas_plan_quiz_submission_grade",
        "canvas_apply_change",
    ]

    def __init__(self, mcp: FastMCP):
        self.mcp = mcp
        self._register()

    def _register(self) -> None:
        read_tools = [
            self.canvas_capabilities,
            self.canvas_list_courses,
            self.canvas_get_course_structure,
            self.canvas_list_course_people,
            self.canvas_get_student_snapshot,
            self.canvas_get_submission_review,
            self.canvas_get_quiz_submission_review,
            self.canvas_list_inbox,
            self.canvas_get_conversation,
        ]
        for fn in read_tools:
            self.mcp.tool(_assistant_tool(fn), annotations=READ_ONLY, tags={"curated", "read"})
        self.mcp.tool(
            _assistant_tool(self.canvas_get_course_copy_selection),
            annotations=READ_ONLY,
            tags={"advanced", "course-copy", "read"},
        )
        for fn in (self.canvas_analyze_student_engagement, self.canvas_list_grading_queue):
            self.mcp.tool(
                _assistant_tool(fn),
                annotations=READ_ONLY,
                tags={"curated", "read", "background"},
                task=BACKGROUND,
            )
        for fn in (
            self.canvas_plan_communication,
            self.canvas_plan_announcement_change,
            self.canvas_plan_page_change,
            self.canvas_plan_assignment_change,
            self.canvas_plan_discussion_change,
            self.canvas_plan_discussion_entry,
            self.canvas_plan_module_change,
            self.canvas_plan_quiz_change,
            self.canvas_plan_file_upload,
            self.canvas_plan_course_copy,
            self.canvas_plan_grade_change,
            self.canvas_plan_quiz_submission_grade,
        ):
            self.mcp.tool(_assistant_tool(fn), annotations=PLAN_ONLY, tags={"curated", "plan"})
        self.mcp.tool(
            _assistant_tool(self.canvas_plan_advanced_action),
            annotations=PLAN_ONLY,
            tags={"advanced", "plan", "authoring"},
        )
        self.mcp.tool(
            _assistant_tool(self.canvas_apply_change),
            annotations=MUTATING,
            tags={"curated", "write", "background"},
            task=BACKGROUND,
        )

    async def canvas_capabilities(self) -> dict[str, Any]:
        """Describe available Canvas workflows and how to discover advanced actions."""
        return {
            "transport": "local stdio",
            "authentication": ["CANVAS_URL", "CANVAS_ACCESS_TOKEN"],
            "visible_tools": self.VISIBLE_NAMES + ["canvas_search_tools", "canvas_call_tool"],
            "discovery": {
                "search": "Use canvas_search_tools with a natural-language request.",
                "call": "Use canvas_call_tool for a discovered read or compatibility action.",
                "maximum_results": 5,
            },
            "authoring": [
                "pages", "assignments", "announcements", "discussions", "modules",
                "Classic Quizzes", "New Quizzes", "rubrics", "files", "course copies",
            ],
            "instructor_workflows": [
                "rosters", "student snapshots", "engagement criteria", "grading queues",
                "submission review", "Classic Quiz essay review and scoring",
                "grades and comments", "discussion posts and replies", "private Inbox outreach",
            ],
            "writes": "Create a plan, review it, then call canvas_apply_change with confirm=true.",
            "background_tasks": {
                "mode": "optional",
                "backend": "memory://",
                "persistence": "Task handles are lost when the MCP process exits.",
            },
        }

    async def canvas_list_courses(
        self,
        state: Annotated[
            Literal["available", "completed", "unpublished", "deleted", "all"],
            Field(description="Enrollment state to return"),
        ] = "available",
        cursor: Annotated[str | None, Field(description="Opaque cursor from a prior result")] = None,
        limit: Annotated[int, Field(ge=1, le=100)] = 50,
    ) -> dict[str, Any]:
        """List courses available to the token owner, favoring instructor use."""
        params: dict[str, Any] = {"enrollment_type": "teacher", "include[]": ["term", "teachers"]}
        if state != "all":
            params["state[]"] = [state]
        async with AsyncCanvasClient.from_environment() as client:
            page = await client.page("/api/v1/courses", params=params, cursor=cursor, limit=limit)
        page["items"] = _compact(
            page["items"],
            ("id", "name", "course_code", "workflow_state", "start_at", "end_at", "term", "teachers"),
        )
        return page

    async def canvas_get_course_structure(
        self,
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        limit_per_type: Annotated[int, Field(ge=1, le=100)] = 50,
    ) -> dict[str, Any]:
        """Return a compact overview of modules, pages, assignments, and quizzes."""
        course_id = _sid(course_id)
        async with AsyncCanvasClient.from_environment() as client:
            modules, pages, assignments, quizzes = await asyncio.gather(
                client.page(
                    f"/api/v1/courses/{course_id}/modules",
                    params={"include[]": ["items", "content_details"]},
                    limit=limit_per_type,
                ),
                client.page(f"/api/v1/courses/{course_id}/pages", limit=limit_per_type),
                client.page(f"/api/v1/courses/{course_id}/assignments", limit=limit_per_type),
                client.page(f"/api/v1/courses/{course_id}/quizzes", limit=limit_per_type),
            )
        return {
            "course_id": course_id,
            "modules": _compact(modules["items"], ("id", "name", "position", "published", "items")),
            "pages": _compact(pages["items"], ("page_id", "url", "title", "published", "updated_at")),
            "assignments": _compact(assignments["items"], ("id", "name", "due_at", "points_possible", "published")),
            "quizzes": _compact(quizzes["items"], ("id", "title", "quiz_type", "due_at", "published")),
            "truncated": any(x["next_cursor"] for x in (modules, pages, assignments, quizzes)),
        }

    async def canvas_list_course_people(
        self,
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        search: Annotated[str | None, Field(description="Partial student name")]=None,
        include_inactive: bool = False,
        cursor: Annotated[str | None, Field(description="Opaque cursor from a prior result")]=None,
        limit: Annotated[int, Field(ge=1, le=100)] = 50,
    ) -> dict[str, Any]:
        """List students with enrollment context; inactive students are excluded by default."""
        params: dict[str, Any] = {
            "enrollment_type[]": ["student"],
            "include[]": ["enrollments"],
        }
        if search:
            params["search_term"] = search
        if not include_inactive:
            params["enrollment_state[]"] = ["active", "invited"]
        async with AsyncCanvasClient.from_environment() as client:
            page = await client.page(
                f"/api/v1/courses/{_sid(course_id)}/users",
                params=params,
                cursor=cursor,
                limit=limit,
            )
        page["items"] = _compact(page["items"], ("id", "name", "sortable_name", "short_name", "enrollments"))
        return page

    async def canvas_get_student_snapshot(
        self,
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        student_id: Annotated[str | int, Field(description="Canvas student ID")],
    ) -> dict[str, Any]:
        """Combine enrollment, progress, submissions, and analytics for one student."""
        course_id, student_id = _sid(course_id), _sid(student_id)
        warnings: list[dict[str, Any]] = []
        async with AsyncCanvasClient.from_environment() as client:
            calls = {
                "enrollments": client.get(
                    f"/api/v1/courses/{course_id}/enrollments",
                    {"user_id": student_id, "type[]": ["StudentEnrollment"]},
                ),
                "progress": client.get(f"/api/v1/courses/{course_id}/users/{student_id}/progress"),
                "submissions": client.page(
                    f"/api/v1/courses/{course_id}/students/submissions",
                    params={"student_ids[]": [student_id], "include[]": ["assignment"]},
                    limit=100,
                ),
                "analytics": client.get(f"/api/v1/courses/{course_id}/analytics/users/{student_id}/activity"),
            }
            results = await asyncio.gather(*calls.values(), return_exceptions=True)
        sections: dict[str, Any] = {}
        for key, value in zip(calls, results, strict=True):
            if isinstance(value, Exception):
                warnings.append({"section": key, "error": str(value)})
            else:
                sections[key] = value
        submission_page = sections.get("submissions", {})
        submissions = submission_page.get("items", []) if isinstance(submission_page, dict) else []
        if isinstance(submissions, list):
            sections["submissions"] = _compact(
                submissions,
                ("id", "assignment_id", "workflow_state", "submitted_at", "late", "missing", "score", "grade", "assignment"),
            )
            sections["submissions_next_cursor"] = submission_page.get("next_cursor")
        return {"course_id": course_id, "student_id": student_id, **sections, "warnings": warnings}

    async def canvas_analyze_student_engagement(
        self,
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        student_ids: Annotated[list[str | int] | None, Field(description="Students to analyze; defaults to the active roster")]=None,
        minimum_missing: Annotated[int, Field(ge=0)] = 1,
        maximum_score_percent: Annotated[float | None, Field(ge=0, le=100)] = None,
        limit: Annotated[int, Field(ge=1, le=100)] = 100,
        progress: Progress = Progress(),
    ) -> dict[str, Any]:
        """Find students matching explicit missing-work or score criteria; this is not a prediction."""
        course_id = _sid(course_id)
        async with AsyncCanvasClient.from_environment() as client:
            if student_ids is None:
                people = await client.page(
                    f"/api/v1/courses/{course_id}/users",
                    params={
                        "enrollment_type[]": ["student"],
                        "enrollment_state[]": ["active"],
                        "include[]": ["enrollments"],
                    },
                    limit=limit,
                )
                students = people["items"]
                roster_next_cursor = people.get("next_cursor")
            else:
                students = [{"id": _sid(value), "name": None} for value in student_ids[:limit]]
                roster_next_cursor = None
            await progress.set_total(max(1, len(students)))
            matches: list[dict[str, Any]] = []
            truncated_submission_ids: list[str] = []
            score_unavailable_ids: list[str] = []
            for student in students:
                student_id = _sid(student["id"])
                await progress.set_message("Reviewing student submissions")
                submissions, submissions_next_cursor = await _bounded_pages(
                    client,
                    f"/api/v1/courses/{course_id}/students/submissions",
                    params={"student_ids[]": [student_id], "include[]": ["assignment"]},
                )
                if submissions_next_cursor:
                    truncated_submission_ids.append(student_id)
                missing = [item for item in submissions if item.get("missing")]
                enrollments = student.get("enrollments") or []
                if maximum_score_percent is not None and not enrollments:
                    enrollment_page = await client.page(
                        f"/api/v1/courses/{course_id}/enrollments",
                        params={
                            "user_id": student_id,
                            "type[]": ["StudentEnrollment"],
                            "state[]": ["active"],
                        },
                        limit=10,
                    )
                    enrollments = enrollment_page["items"]
                score_percent = _canvas_current_score(enrollments)
                if maximum_score_percent is not None and score_percent is None:
                    score_unavailable_ids.append(student_id)
                reasons: list[dict[str, Any]] = []
                if len(missing) >= minimum_missing and minimum_missing > 0:
                    reasons.append({"criterion": "missing_assignments", "actual": len(missing), "threshold": minimum_missing})
                if maximum_score_percent is not None and score_percent is not None and score_percent <= maximum_score_percent:
                    reasons.append({"criterion": "score_percent", "actual": score_percent, "threshold": maximum_score_percent})
                if reasons:
                    matches.append({
                        "student_id": student_id,
                        "name": student.get("name"),
                        "matched_criteria": reasons,
                        "missing_assignment_ids": [_sid(item.get("assignment_id")) for item in missing],
                        "canvas_current_score": score_percent,
                    })
                await progress.increment()
        return {
            "course_id": course_id,
            "evaluated": len(students),
            "matched": len(matches),
            "students": matches,
            "roster_next_cursor": roster_next_cursor,
            "submission_data_truncated_for": truncated_submission_ids,
            "current_score_unavailable_for": score_unavailable_ids,
            "interpretation": "These students matched the stated criteria; this is not a prediction of student risk.",
        }

    async def canvas_list_grading_queue(
        self,
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        assignment_ids: Annotated[list[str | int] | None, Field(description="Optional assignments to include")]=None,
        workflow_state: Annotated[
            Literal["submitted", "pending_review"],
            Field(description="Submission state to load; call once for each state when both are needed"),
        ] = "submitted",
        cursor: Annotated[str | None, Field(description="Opaque cursor from a prior result")]=None,
        limit: Annotated[int, Field(ge=1, le=100)] = 50,
        progress: Progress = Progress(),
    ) -> dict[str, Any]:
        """List submissions awaiting instructor review with assignment and student context."""
        course_id = _sid(course_id)
        params: dict[str, Any] = {
            "student_ids[]": ["all"],
            "include[]": ["assignment", "user"],
            "workflow_state": workflow_state,
        }
        if assignment_ids:
            params["assignment_ids[]"] = [_sid(value) for value in assignment_ids]
        await progress.set_message("Loading grading queue")
        async with AsyncCanvasClient.from_environment() as client:
            page = await client.page(
                f"/api/v1/courses/{course_id}/students/submissions",
                params=params,
                cursor=cursor,
                limit=limit,
            )
        await progress.set_total(page["count"] or 1)
        if page["count"]:
            await progress.increment(page["count"])
        page["items"] = _compact(
            page["items"],
            ("id", "assignment_id", "user_id", "workflow_state", "submitted_at", "late", "missing", "score", "grade", "assignment", "user"),
        )
        page["course_id"] = course_id
        page["workflow_state"] = workflow_state
        return page

    async def canvas_get_submission_review(
        self,
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        assignment_id: Annotated[str | int, Field(description="Canvas assignment ID")],
        student_id: Annotated[str | int | None, Field(description="Canvas student ID")]=None,
        anonymous_id: Annotated[str | None, Field(description="Anonymous grading identifier")]=None,
    ) -> dict[str, Any]:
        """Get a submission with comments, rubric assessment, history, and visibility."""
        if (student_id is None) == (anonymous_id is None):
            raise ValueError("Provide exactly one of student_id or anonymous_id")
        target = (
            f"anonymous_submissions/{_sid(anonymous_id)}"
            if anonymous_id is not None
            else f"submissions/{_sid(student_id)}"
        )
        endpoint = f"/api/v1/courses/{_sid(course_id)}/assignments/{_sid(assignment_id)}/{target}"
        async with AsyncCanvasClient.from_environment() as client:
            return await client.get(endpoint, {"include[]": ["submission_comments", "rubric_assessment", "submission_history", "visibility"]})

    @staticmethod
    def _quiz_submissions(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and isinstance(payload.get("quiz_submissions"), list):
            return payload["quiz_submissions"]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict) and payload.get("id") is not None:
            return [payload]
        return []

    async def _load_quiz_submission_review(
        self,
        client: AsyncCanvasClient,
        *,
        course_id: str,
        quiz_id: str,
        quiz_submission_id: str | None,
        student_id: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        include_params = {"include[]": ["submission", "quiz", "user"]}
        if quiz_submission_id is not None:
            submission_endpoint = (
                f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/"
                f"{quiz_submission_id}"
            )
            submission_payload = await client.get(submission_endpoint, include_params)
            candidates = self._quiz_submissions(submission_payload)
        else:
            collection_endpoint = f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions"
            collection_params = {**include_params, "per_page": 100}
            collection_payload = await client.get(collection_endpoint, collection_params)
            candidates = [
                item
                for item in self._quiz_submissions(collection_payload)
                if str(item.get("user_id")) == student_id
            ]
            if not candidates:
                raise ValueError(f"No Classic Quiz submission found for student {student_id}")
            candidates.sort(
                key=lambda item: (int(item.get("attempt") or 0), int(item.get("id") or 0)),
                reverse=True,
            )
            selected_id = _sid(candidates[0].get("id"))
            submission_endpoint = (
                f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/{selected_id}"
            )
            submission_payload = await client.get(submission_endpoint, include_params)
            candidates = self._quiz_submissions(submission_payload)
        if not candidates:
            raise ValueError("Canvas did not return the requested Classic Quiz submission")
        submission = candidates[0]
        if submission.get("id") is None:
            raise ValueError("Canvas returned a Classic Quiz submission without an ID")
        actual_submission_id = _sid(submission.get("id"))
        if quiz_submission_id is not None and actual_submission_id != quiz_submission_id:
            raise ValueError("Canvas returned a different quiz submission than requested")
        if student_id is not None and str(submission.get("user_id")) != student_id:
            raise ValueError("The quiz submission does not belong to the requested student")
        attempt = submission.get("attempt")
        if not isinstance(attempt, int) or attempt < 1:
            raise ValueError("Canvas returned an invalid Classic Quiz attempt number")

        question_params = {
            "quiz_submission_id": actual_submission_id,
            "quiz_submission_attempt": attempt,
        }
        answer_endpoint = f"/api/v1/quiz_submissions/{actual_submission_id}/questions"
        answer_params = {"include[]": ["quiz_question"]}
        definitions, answer_payload = await asyncio.gather(
            _bounded_pages(
                client,
                f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions",
                params=question_params,
            ),
            client.get(answer_endpoint, answer_params),
        )
        question_definitions, next_cursor = definitions
        answer_records = (
            answer_payload.get("quiz_submission_questions", [])
            if isinstance(answer_payload, dict)
            else answer_payload if isinstance(answer_payload, list) else []
        )
        definitions_by_id = {
            str(item.get("id")): item
            for item in question_definitions
            if isinstance(item, dict) and item.get("id") is not None
        }
        answers_by_id = {
            str(item.get("id")): item
            for item in answer_records
            if isinstance(item, dict) and item.get("id") is not None
        }
        ordered_ids = list(definitions_by_id)
        ordered_ids.extend(value for value in answers_by_id if value not in definitions_by_id)
        manual_types = {"essay_question", "file_upload_question"}
        questions: list[dict[str, Any]] = []
        for question_id in ordered_ids:
            record = answers_by_id.get(question_id, {})
            nested_definition = record.get("quiz_question")
            definition = definitions_by_id.get(question_id) or (
                nested_definition if isinstance(nested_definition, dict) else record
            )
            question_type = definition.get("question_type") or record.get("question_type")
            if question_type not in manual_types:
                continue
            questions.append(
                {
                    "question_id": question_id,
                    "question_name": definition.get("question_name") or record.get("question_name"),
                    "question_type": question_type,
                    "question_text": _plain_text(
                        definition.get("question_text", record.get("question_text"))
                    ),
                    "points_possible": definition.get(
                        "points_possible", record.get("points_possible")
                    ),
                    "answer": _plain_text(record.get("answer")),
                    "answer_available": "answer" in record,
                    "score": record.get("score"),
                    "score_available": "score" in record,
                    "comment": _plain_text(record.get("comment")),
                    "comment_available": "comment" in record,
                }
            )
        review = {
            "course_id": course_id,
            "quiz_id": quiz_id,
            "quiz_submission": {
                key: submission.get(key)
                for key in (
                    "id", "user_id", "attempt", "workflow_state", "score", "kept_score",
                    "fudge_points", "started_at", "finished_at", "end_at", "validation_token",
                )
                if key in submission and key != "validation_token"
            },
            "user": submission.get("user"),
            "assignment_submission": submission.get("submission"),
            "questions": questions,
            "question_count": len(questions),
            "answers_unavailable": sum(
                not item["answer_available"]
                for item in questions
            ),
            "question_data_truncated": bool(next_cursor),
        }
        state = {
            "submission_endpoint": submission_endpoint,
            "submission_params": include_params,
            "submission_payload": submission_payload,
            "answer_endpoint": answer_endpoint,
            "answer_params": answer_params,
            "answer_payload": answer_payload,
        }
        return review, state

    async def canvas_get_quiz_submission_review(
        self,
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        quiz_id: Annotated[str | int, Field(description="Classic Quiz ID")],
        quiz_submission_id: Annotated[
            str | int | None,
            Field(description="Classic Quiz submission ID; provide this or student_id"),
        ] = None,
        student_id: Annotated[
            str | int | None,
            Field(description="Student ID; selects the latest returned attempt"),
        ] = None,
    ) -> dict[str, Any]:
        """Review only essay and file-upload questions in a Classic Quiz attempt."""
        if (quiz_submission_id is None) == (student_id is None):
            raise ValueError("Provide exactly one of quiz_submission_id or student_id")
        normalized_submission_id = (
            _sid(quiz_submission_id) if quiz_submission_id is not None else None
        )
        normalized_student_id = _sid(student_id) if student_id is not None else None
        async with AsyncCanvasClient.from_environment() as client:
            review, _ = await self._load_quiz_submission_review(
                client,
                course_id=_sid(course_id),
                quiz_id=_sid(quiz_id),
                quiz_submission_id=normalized_submission_id,
                student_id=normalized_student_id,
            )
        return review

    async def canvas_list_inbox(
        self,
        course_id: Annotated[str | int | None, Field(description="Optional course filter")]=None,
        scope: Annotated[Literal["inbox", "unread", "starred", "archived", "sent"], Field(description="Conversation scope")]="inbox",
        cursor: Annotated[str | None, Field(description="Opaque cursor from a prior result")]=None,
        limit: Annotated[int, Field(ge=1, le=100)] = 50,
    ) -> dict[str, Any]:
        """List Canvas Inbox conversations."""
        params: dict[str, Any] = {"include[]": ["participant_avatars"]}
        if scope != "inbox":
            params["scope"] = scope
        if course_id is not None:
            params["filter[]"] = [f"course_{_sid(course_id)}"]
        async with AsyncCanvasClient.from_environment() as client:
            return await client.page("/api/v1/conversations", params=params, cursor=cursor, limit=limit)

    async def canvas_get_conversation(
        self,
        conversation_id: Annotated[str | int, Field(description="Canvas conversation ID")],
    ) -> dict[str, Any]:
        """Get a Canvas Inbox thread and its messages without changing read state."""
        async with AsyncCanvasClient.from_environment() as client:
            return await client.get(
                f"/api/v1/conversations/{_sid(conversation_id)}",
                {"auto_mark_as_read": False},
            )

    async def canvas_get_course_copy_selection(
        self,
        destination_course_id: Annotated[str | int, Field(description="Destination Canvas course ID")],
        migration_id: Annotated[str | int, Field(description="Content migration ID")],
        content_type: Annotated[str | None, Field(description="Optional Canvas selective-data type")]=None,
    ) -> Any:
        """List content and copy-property keys for a staged selective course copy."""
        params = {"type": content_type} if content_type else None
        endpoint = (
            f"/api/v1/courses/{_sid(destination_course_id)}/content_migrations/"
            f"{_sid(migration_id)}/selective_data"
        )
        async with AsyncCanvasClient.from_environment() as client:
            return await client.get(endpoint, params)

    async def _snapshot(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], Precondition]:
        async with AsyncCanvasClient.from_environment() as client:
            current = await client.get(endpoint, params)
        return current, Precondition(
            endpoint=endpoint, fingerprint=fingerprint(current), params=params
        )

    async def _simple_plan(
        self,
        *,
        action: str,
        summary: str,
        operation: str,
        collection_endpoint: str,
        item_endpoint: str | None,
        payload: dict[str, Any],
        prefix: str | None,
        update_method: Literal["PUT", "PATCH"] = "PUT",
    ) -> dict[str, Any]:
        operation = operation.lower()
        preconditions: list[Precondition] = []
        before: Any = None
        if operation == "create":
            method, endpoint = "POST", collection_endpoint
        else:
            if not item_endpoint:
                raise ValueError(f"{action} {operation} requires an item ID")
            before, condition = await self._snapshot(item_endpoint)
            preconditions.append(condition)
            method, endpoint = (
                ("DELETE", item_endpoint)
                if operation == "delete"
                else (update_method, item_endpoint)
            )
        changes = dict(payload)
        if operation in {"publish", "unpublish"}:
            changes["published"] = operation == "publish"
        if operation in {"create", "update"} and not changes:
            raise ValueError(f"{action} {operation} requires at least one field in changes")
        data = _form_payload(changes, prefix)
        return await plan_store.create(
            action=action,
            summary=summary,
            preview={"operation": operation, "before": before, "changes": changes},
            mutations=[Mutation(method=method, endpoint=endpoint, data=data or None)],
            preconditions=preconditions,
            destructive=operation == "delete",
        )

    async def canvas_plan_communication(
        self,
        recipient_ids: Annotated[list[str | int], Field(min_length=1, max_length=100, description="Canvas user IDs")],
        body: Annotated[str, Field(min_length=1, description="Private message body")],
        subject: Annotated[str | None, Field(description="Conversation subject")]=None,
        course_id: Annotated[str | int | None, Field(description="Optional course context")]=None,
    ) -> dict[str, Any]:
        """Plan separate private Canvas Inbox conversations for up to 100 students."""
        recipients = [_sid(value) for value in recipient_ids]
        mutations = [
            Mutation(
                method="POST",
                endpoint="/api/v1/conversations",
                data={
                    "recipients[]": [recipient],
                    "body": body,
                    "subject": subject or "Message from your instructor",
                    "group_conversation": False,
                    "force_new": True,
                    **({"context_code": f"course_{_sid(course_id)}"} if course_id is not None else {}),
                },
                label=f"recipient:{recipient}",
            )
            for recipient in recipients
        ]
        return await plan_store.create(
            action="private_student_messages",
            summary=f"Send {len(recipients)} separate private Canvas conversations",
            preview={"recipient_ids": recipients, "subject": subject, "body": body, "private": True},
            mutations=mutations,
            warnings=["This operation is not atomic; cancellation can leave some messages sent."],
        )

    async def canvas_plan_page_change(
        self,
        course_id: str | int,
        operation: Literal["create", "update", "publish", "unpublish", "delete"],
        page_url: str | None = None,
        changes: Annotated[dict[str, Any] | None, Field(description="Page fields such as title, body, published, editing_roles")]=None,
    ) -> dict[str, Any]:
        """Plan creation or maintenance of a Canvas course page."""
        course_id = _sid(course_id)
        return await self._simple_plan(
            action="page_change", summary=f"{operation.title()} Canvas page",
            operation=operation, collection_endpoint=f"/api/v1/courses/{course_id}/pages",
            item_endpoint=f"/api/v1/courses/{course_id}/pages/{quote(page_url, safe='')}" if page_url else None,
            payload=changes or {}, prefix="wiki_page",
        )

    async def canvas_plan_assignment_change(
        self,
        course_id: str | int,
        operation: Literal["create", "update", "publish", "unpublish", "delete"],
        assignment_id: str | int | None = None,
        changes: Annotated[dict[str, Any] | None, Field(description="Assignment fields such as name, description, due_at, points_possible")]=None,
    ) -> dict[str, Any]:
        """Plan creation or maintenance of a Canvas assignment."""
        course_id = _sid(course_id)
        return await self._simple_plan(
            action="assignment_change", summary=f"{operation.title()} Canvas assignment",
            operation=operation, collection_endpoint=f"/api/v1/courses/{course_id}/assignments",
            item_endpoint=f"/api/v1/courses/{course_id}/assignments/{_sid(assignment_id)}" if assignment_id is not None else None,
            payload=changes or {}, prefix="assignment",
        )

    async def canvas_plan_announcement_change(
        self,
        course_id: str | int,
        operation: Literal["create", "update", "publish", "unpublish", "delete"],
        announcement_id: str | int | None = None,
        changes: Annotated[dict[str, Any] | None, Field(description="Announcement fields such as title, message, delayed_post_at")]=None,
    ) -> dict[str, Any]:
        """Plan creation or maintenance of a course announcement."""
        course_id = _sid(course_id)
        payload = {**(changes or {}), "is_announcement": True}
        return await self._simple_plan(
            action="announcement_change", summary=f"{operation.title()} Canvas announcement",
            operation=operation, collection_endpoint=f"/api/v1/courses/{course_id}/discussion_topics",
            item_endpoint=f"/api/v1/courses/{course_id}/discussion_topics/{_sid(announcement_id)}" if announcement_id is not None else None,
            payload=payload, prefix=None,
        )

    async def canvas_plan_discussion_change(
        self,
        course_id: str | int,
        operation: Literal["create", "update", "publish", "unpublish", "delete"],
        discussion_id: str | int | None = None,
        changes: Annotated[dict[str, Any] | None, Field(description="Discussion fields such as title, message, discussion_type, published")]=None,
    ) -> dict[str, Any]:
        """Plan creation or maintenance of a Canvas discussion."""
        course_id = _sid(course_id)
        return await self._simple_plan(
            action="discussion_change", summary=f"{operation.title()} Canvas discussion",
            operation=operation, collection_endpoint=f"/api/v1/courses/{course_id}/discussion_topics",
            item_endpoint=f"/api/v1/courses/{course_id}/discussion_topics/{_sid(discussion_id)}" if discussion_id is not None else None,
            payload=changes or {}, prefix=None,
        )

    async def canvas_plan_discussion_entry(
        self,
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        topic_id: Annotated[str | int, Field(description="Canvas discussion topic ID")],
        operation: Annotated[
            Literal["post_entry", "post_reply"],
            Field(description="Post a top-level entry or reply to a specific entry"),
        ],
        message: Annotated[str, Field(min_length=1, description="Entry or reply body")],
        entry_id: Annotated[
            str | int | None,
            Field(description="Parent discussion entry ID; required only for post_reply"),
        ] = None,
    ) -> dict[str, Any]:
        """Plan a new discussion entry or an entry-specific reply."""
        course_id = _sid(course_id)
        topic_id = _sid(topic_id)
        message = message.strip()
        if not message:
            raise ValueError("message must contain non-whitespace text")
        if operation == "post_reply" and entry_id is None:
            raise ValueError("post_reply requires entry_id")
        if operation == "post_entry" and entry_id is not None:
            raise ValueError("entry_id is only valid for post_reply")

        topic_endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}"
        parent_id = _sid(entry_id) if entry_id is not None else None
        preconditions: list[Precondition] = []
        parent_entry: dict[str, Any] | None = None
        async with AsyncCanvasClient.from_environment() as client:
            topic = await client.get(topic_endpoint)
            if parent_id is not None:
                entry_list_endpoint = f"{topic_endpoint}/entry_list"
                entry_list_params = {"ids[]": [parent_id]}
                entry_payload = await client.get(entry_list_endpoint, entry_list_params)
                entries = (
                    entry_payload.get("entries", [])
                    if isinstance(entry_payload, dict)
                    else entry_payload if isinstance(entry_payload, list) else []
                )
                matching = [
                    item for item in entries
                    if isinstance(item, dict) and str(item.get("id")) == parent_id
                ]
                if len(matching) != 1:
                    raise ValueError(f"Discussion entry {parent_id} was not found in topic {topic_id}")
                parent_entry = matching[0]
                preconditions.append(
                    Precondition(
                        endpoint=entry_list_endpoint,
                        params=entry_list_params,
                        fingerprint=fingerprint(entry_payload),
                    )
                )

        endpoint = f"{topic_endpoint}/entries"
        if parent_id is not None:
            endpoint += f"/{parent_id}/replies"
        warnings = [
            "Applying this plan publishes the message immediately and may notify discussion participants."
        ]
        group_children = topic.get("group_topic_children") or []
        if group_children:
            warnings.append(
                "This is a group discussion root topic. Post to the intended child group topic instead."
            )
        return await plan_store.create(
            action="discussion_entry",
            summary=(
                f"Reply to discussion entry {parent_id} in topic {topic_id}"
                if parent_id is not None
                else f"Post a new entry in discussion topic {topic_id}"
            ),
            preview={
                "operation": operation,
                "topic": {
                    key: topic.get(key)
                    for key in ("id", "title", "published", "locked", "discussion_type")
                    if key in topic
                },
                "parent_entry": (
                    {
                        "id": parent_entry.get("id"),
                        "user_name": parent_entry.get("user_name"),
                        "created_at": parent_entry.get("created_at"),
                        "message": _plain_text(parent_entry.get("message"), 2_000),
                    }
                    if parent_entry is not None else None
                ),
                "message": message,
            },
            mutations=[Mutation("POST", endpoint, data={"message": message})],
            preconditions=preconditions,
            warnings=warnings,
        )

    async def canvas_plan_module_change(
        self,
        course_id: str | int,
        operation: Literal["create", "update", "publish", "unpublish", "delete", "add_item", "update_item", "delete_item"],
        module_id: str | int | None = None,
        item_id: str | int | None = None,
        changes: Annotated[dict[str, Any] | None, Field(description="Module or module-item fields")]=None,
    ) -> dict[str, Any]:
        """Plan module and module-item creation, publishing, ordering, or deletion."""
        course_id = _sid(course_id)
        item_operation = operation.endswith("_item")
        normalized = operation.replace("_item", "") if item_operation else operation
        if normalized == "add":
            normalized = "create"
        if item_operation and module_id is None:
            raise ValueError("Module item operations require module_id")
        collection = (
            f"/api/v1/courses/{course_id}/modules/{_sid(module_id)}/items"
            if item_operation else f"/api/v1/courses/{course_id}/modules"
        )
        item_endpoint = None
        if item_operation and item_id is not None:
            item_endpoint = f"{collection}/{_sid(item_id)}"
        elif not item_operation and module_id is not None:
            item_endpoint = f"{collection}/{_sid(module_id)}"
        return await self._simple_plan(
            action="module_item_change" if item_operation else "module_change",
            summary=f"{operation.replace('_', ' ').title()} in Canvas",
            operation=normalized,
            collection_endpoint=collection,
            item_endpoint=item_endpoint,
            payload=changes or {},
            prefix="module_item" if item_operation else "module",
        )

    async def canvas_plan_quiz_change(
        self,
        course_id: str | int,
        engine: Literal["classic", "new"],
        operation: Literal["create", "update", "publish", "unpublish", "delete"],
        quiz_id: str | int | None = None,
        changes: Annotated[dict[str, Any] | None, Field(description="Quiz fields; include an items array when creating questions/items")]=None,
    ) -> dict[str, Any]:
        """Plan Classic or New Quiz creation, settings, items, publishing, or deletion."""
        course_id = _sid(course_id)
        root = "/api/v1" if engine == "classic" else "/api/quiz/v1"
        collection = f"{root}/courses/{course_id}/quizzes"
        quiz_endpoint = f"{collection}/{_sid(quiz_id)}" if quiz_id is not None else None
        payload = dict(changes or {})
        items = payload.pop("items", [])
        if items and operation != "create":
            raise ValueError("Quiz items can only be included when creating a quiz")
        result = await self._simple_plan(
            action=f"{engine}_quiz_change", summary=f"{operation.title()} {engine.title()} Canvas quiz",
            operation=operation, collection_endpoint=collection, item_endpoint=quiz_endpoint,
            payload=payload, prefix="quiz", update_method="PATCH" if engine == "new" else "PUT",
        )
        if operation == "create" and items:
            result["warnings"].append("Quiz items will be added after Canvas returns the new quiz ID.")
            # The apply path recognizes this placeholder and substitutes the created quiz ID.
            additions = []
            for index, item in enumerate(items):
                additions.append(Mutation(
                    method="POST",
                    endpoint=f"{collection}/{{created_quiz_id}}/{'questions' if engine == 'classic' else 'items'}",
                    data=_form_payload(item, "question" if engine == "classic" else "item"),
                    label=f"quiz-item:{index + 1}",
                ))
            result = await plan_store.append_mutations(result["plan_token"], additions)
        return result

    async def canvas_plan_advanced_action(
        self,
        action: Annotated[
            str,
            Field(
                description=(
                    "Advanced action: create/update/delete assignment_override or assignment_group; "
                    "create/update/delete folder; set/remove file_usage_rights; "
                    "create/update/delete classic_quiz_question or classic_quiz_question_group; "
                    "create_rubric; set_assignment_extensions; apply_course_copy_selection"
                )
            ),
        ],
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        arguments: Annotated[dict[str, Any], Field(description="IDs and Canvas fields required by the selected action")],
    ) -> dict[str, Any]:
        """Plan advanced authoring, rubric, usage-rights, and course-copy actions."""
        action = action.lower().strip()
        course_id = _sid(course_id)
        args = dict(arguments)
        resource_id: str | None = None
        collection: str
        prefix: str | None

        if action == "create_rubric":
            assignment_id = args.pop("assignment_id", None)
            title = args.pop("title", None)
            criteria = args.pop("criteria", None)
            if assignment_id is None:
                raise ValueError("create_rubric requires assignment_id")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("create_rubric requires a non-empty title")
            if not isinstance(criteria, list) or not criteria:
                raise ValueError("create_rubric requires a non-empty criteria list")

            normalized_criteria: list[dict[str, Any]] = []
            for criterion_index, criterion in enumerate(criteria, start=1):
                if not isinstance(criterion, dict):
                    raise ValueError(f"Rubric criterion {criterion_index} must be an object")
                description = criterion.get("description")
                points = criterion.get("points")
                ratings = criterion.get("ratings")
                if not isinstance(description, str) or not description.strip():
                    raise ValueError(f"Rubric criterion {criterion_index} requires a description")
                if not isinstance(points, (int, float)) or isinstance(points, bool) or points < 0:
                    raise ValueError(f"Rubric criterion {criterion_index} requires non-negative points")
                if not isinstance(ratings, list) or not ratings:
                    raise ValueError(f"Rubric criterion {criterion_index} requires ratings")
                normalized_ratings: list[dict[str, Any]] = []
                for rating_index, rating in enumerate(ratings, start=1):
                    if not isinstance(rating, dict):
                        raise ValueError(
                            f"Rubric criterion {criterion_index} rating {rating_index} must be an object"
                        )
                    rating_description = rating.get("description")
                    rating_points = rating.get("points")
                    if not isinstance(rating_description, str) or not rating_description.strip():
                        raise ValueError(
                            f"Rubric criterion {criterion_index} rating {rating_index} requires a description"
                        )
                    if (
                        not isinstance(rating_points, (int, float))
                        or isinstance(rating_points, bool)
                        or rating_points < 0
                        or rating_points > points
                    ):
                        raise ValueError(
                            f"Rubric criterion {criterion_index} rating {rating_index} points "
                            "must be between zero and the criterion points"
                        )
                    normalized_rating = {
                        "description": rating_description.strip(),
                        "points": rating_points,
                    }
                    if rating.get("long_description") is not None:
                        normalized_rating["long_description"] = rating["long_description"]
                    normalized_ratings.append(normalized_rating)
                normalized_criterion = {
                    "description": description.strip(),
                    "points": points,
                    "ratings": normalized_ratings,
                }
                if criterion.get("long_description") is not None:
                    normalized_criterion["long_description"] = criterion["long_description"]
                if criterion.get("criterion_use_range") is not None:
                    normalized_criterion["criterion_use_range"] = bool(
                        criterion["criterion_use_range"]
                    )
                normalized_criteria.append(normalized_criterion)

            use_for_grading = args.pop("use_for_grading", True)
            hide_score_total = args.pop("hide_score_total", False)
            purpose = args.pop("purpose", "grading")
            free_form_comments = args.pop("free_form_criterion_comments", True)
            association_title = args.pop("association_title", title)
            if not isinstance(use_for_grading, bool) or not isinstance(hide_score_total, bool):
                raise ValueError("Rubric grading and score visibility options must be booleans")
            if not isinstance(free_form_comments, bool):
                raise ValueError("free_form_criterion_comments must be a boolean")
            if not isinstance(association_title, str) or not association_title.strip():
                raise ValueError("association_title must be a non-empty string")
            if purpose not in {"grading", "bookmark"}:
                raise ValueError("Rubric purpose must be grading or bookmark")
            if use_for_grading and hide_score_total:
                raise ValueError("Canvas cannot hide the rubric score total when it is used for grading")
            if args:
                raise ValueError(
                    "Unsupported create_rubric arguments: " + ", ".join(sorted(args))
                )

            assignment_id = _sid(assignment_id)
            assignment_endpoint = (
                f"/api/v1/courses/{course_id}/assignments/{assignment_id}"
            )
            assignment, condition = await self._snapshot(assignment_endpoint)
            rubric_points = sum(float(item["points"]) for item in normalized_criteria)
            assignment_points = assignment.get("points_possible")
            warnings: list[str] = []
            if assignment_points is not None and float(assignment_points) != rubric_points:
                warnings.append(
                    f"Rubric totals {rubric_points:g} points but the assignment totals "
                    f"{float(assignment_points):g} points."
                )
            rubric_data = _form_payload(
                {
                    "title": title.strip(),
                    "free_form_criterion_comments": free_form_comments,
                    "criteria": normalized_criteria,
                },
                "rubric",
            )
            association_data = _form_payload(
                {
                    "association_id": assignment_id,
                    "association_type": "Assignment",
                    "title": association_title.strip(),
                    "use_for_grading": use_for_grading,
                    "hide_score_total": hide_score_total,
                    "purpose": purpose,
                },
                "rubric_association",
            )
            return await plan_store.create(
                action=action,
                summary=f"Create and attach rubric to assignment {assignment_id}",
                preview={
                    "assignment": {
                        key: assignment.get(key)
                        for key in ("id", "name", "points_possible", "published")
                        if key in assignment
                    },
                    "rubric": {
                        "title": title.strip(),
                        "points_possible": rubric_points,
                        "criteria": normalized_criteria,
                    },
                    "association": {
                        "use_for_grading": use_for_grading,
                        "hide_score_total": hide_score_total,
                        "purpose": purpose,
                    },
                },
                mutations=[
                    Mutation(
                        "POST",
                        f"/api/v1/courses/{course_id}/rubrics",
                        data={**rubric_data, **association_data},
                    )
                ],
                preconditions=[condition],
                warnings=warnings,
            )
        elif action.endswith("assignment_override"):
            assignment_id = args.pop("assignment_id", None)
            if assignment_id is None:
                raise ValueError("assignment override actions require assignment_id")
            resource_id = args.pop("override_id", None)
            collection = f"/api/v1/courses/{course_id}/assignments/{_sid(assignment_id)}/overrides"
            prefix = "assignment_override"
        elif action.endswith("assignment_group"):
            resource_id = args.pop("assignment_group_id", None)
            collection = f"/api/v1/courses/{course_id}/assignment_groups"
            prefix = None
        elif action.endswith("folder"):
            resource_id = args.pop("folder_id", None)
            collection = f"/api/v1/courses/{course_id}/folders"
            prefix = None
        elif action.endswith("classic_quiz_question_group"):
            quiz_id = args.pop("quiz_id", None)
            if quiz_id is None:
                raise ValueError("quiz question-group actions require quiz_id")
            resource_id = args.pop("group_id", None)
            collection = f"/api/v1/courses/{course_id}/quizzes/{_sid(quiz_id)}/groups"
            prefix = "quiz_groups[]"
        elif action.endswith("classic_quiz_question"):
            quiz_id = args.pop("quiz_id", None)
            if quiz_id is None:
                raise ValueError("quiz question actions require quiz_id")
            resource_id = args.pop("question_id", None)
            collection = f"/api/v1/courses/{course_id}/quizzes/{_sid(quiz_id)}/questions"
            prefix = "question"
        elif action == "set_assignment_extensions":
            assignment_id = args.pop("assignment_id", None)
            if assignment_id is None:
                raise ValueError("set_assignment_extensions requires assignment_id")
            extensions = args.pop("assignment_extensions", None)
            if not isinstance(extensions, list) or not extensions:
                raise ValueError("assignment_extensions must be a non-empty list")
            return await plan_store.create(
                action=action,
                summary=f"Set extra attempts for {len(extensions)} students",
                preview={"course_id": course_id, "assignment_id": _sid(assignment_id), "assignment_extensions": extensions},
                mutations=[Mutation(
                    "POST",
                    f"/api/v1/courses/{course_id}/assignments/{_sid(assignment_id)}/extensions",
                    json_data={"assignment_extensions": extensions},
                )],
            )
        elif action == "apply_course_copy_selection":
            migration_id = args.pop("migration_id", None)
            selection_properties = args.pop("selection_properties", None)
            if migration_id is None:
                raise ValueError("apply_course_copy_selection requires migration_id")
            if not isinstance(selection_properties, dict) or not selection_properties:
                raise ValueError(
                    "selection_properties must contain property keys returned by "
                    "canvas_get_course_copy_selection"
                )
            endpoint = f"/api/v1/courses/{course_id}/content_migrations/{_sid(migration_id)}"
            before, condition = await self._snapshot(endpoint)
            return await plan_store.create(
                action=action,
                summary=f"Apply selected content for migration {_sid(migration_id)}",
                preview={"before": before, "selection_properties": selection_properties},
                mutations=[Mutation("PUT", endpoint, data=_form_payload(selection_properties))],
                preconditions=[condition],
            )
        elif action in {"set_file_usage_rights", "remove_file_usage_rights"}:
            file_ids = args.pop("file_ids", None)
            if not isinstance(file_ids, list) or not file_ids:
                raise ValueError("file usage-rights actions require a non-empty file_ids list")
            endpoint = f"/api/v1/courses/{course_id}/usage_rights"
            if action == "remove_file_usage_rights":
                return await plan_store.create(
                    action=action,
                    summary=f"Remove usage rights from {len(file_ids)} files",
                    preview={"file_ids": [_sid(value) for value in file_ids]},
                    mutations=[Mutation("DELETE", endpoint, data={"file_ids[]": [_sid(value) for value in file_ids]})],
                    destructive=True,
                )
            usage_rights = args.pop("usage_rights", None)
            if not isinstance(usage_rights, dict):
                raise ValueError("set_file_usage_rights requires a usage_rights object")
            return await plan_store.create(
                action=action,
                summary=f"Set usage rights on {len(file_ids)} files",
                preview={"file_ids": [_sid(value) for value in file_ids], "usage_rights": usage_rights},
                mutations=[Mutation("PUT", endpoint, data={"file_ids[]": [_sid(value) for value in file_ids], **_form_payload(usage_rights, "usage_rights")})],
            )
        else:
            supported = [
                "create/update/delete_assignment_override",
                "create/update/delete_assignment_group",
                "create/update/delete_folder",
                "create/update/delete_classic_quiz_question",
                "create/update/delete_classic_quiz_question_group",
                "create_rubric",
                "set_assignment_extensions",
                "apply_course_copy_selection",
                "set_file_usage_rights",
                "remove_file_usage_rights",
            ]
            raise ValueError(f"Unsupported advanced action. Choose one of: {', '.join(supported)}")

        operation = action.split("_", 1)[0]
        item_endpoint = f"{collection}/{_sid(resource_id)}" if resource_id is not None else None
        if action.endswith("folder") and resource_id is not None:
            item_endpoint = f"/api/v1/folders/{_sid(resource_id)}"
        return await self._simple_plan(
            action=action,
            summary=action.replace("_", " ").title(),
            operation=operation,
            collection_endpoint=collection,
            item_endpoint=item_endpoint,
            payload=args,
            prefix=prefix,
        )

    async def canvas_plan_file_upload(
        self,
        course_id: str | int,
        local_path: Annotated[str, Field(description="Absolute path to a local file")],
        folder_id: str | int | None = None,
        on_duplicate: Literal["overwrite", "rename"] = "rename",
    ) -> dict[str, Any]:
        """Plan a local-file upload using Canvas's multi-step upload protocol."""
        path = Path(local_path).expanduser()
        if not path.is_absolute() or not path.is_file():
            raise ValueError("local_path must be an existing absolute file path")
        path = path.resolve(strict=True)
        size, modified_ns, sha256 = await asyncio.to_thread(_file_fingerprint, path)
        data: dict[str, Any] = {
            "name": path.name,
            "size": size,
            "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "on_duplicate": on_duplicate,
            "_local_path": str(path),
            "_local_size": size,
            "_local_modified_ns": modified_ns,
            "_local_sha256": sha256,
        }
        if folder_id is not None:
            data["parent_folder_id"] = _sid(folder_id)
        return await plan_store.create(
            action="file_upload",
            summary=f"Upload {path.name} to Canvas course {_sid(course_id)}",
            preview={
                key: value for key, value in data.items() if not key.startswith("_local_")
            } | {"sha256": sha256},
            mutations=[Mutation("UPLOAD", f"/api/v1/courses/{_sid(course_id)}/files", data=data)],
        )

    async def canvas_plan_course_copy(
        self,
        source_course_id: str | int,
        destination_course_id: str | int,
        selective_import: bool = False,
        selected_items: Annotated[
            dict[str, list[str | int]] | None,
            Field(description="Content types and source IDs to copy immediately, such as pages or assignments"),
        ] = None,
        date_shift_options: Annotated[dict[str, Any] | None, Field(description="Canvas date-shift options")]=None,
    ) -> dict[str, Any]:
        """Plan a complete or selective course copy through Content Migrations."""
        data: dict[str, Any] = {
            "migration_type": "course_copy_importer",
            "settings[source_course_id]": _sid(source_course_id),
        }
        data.update(_form_payload(date_shift_options or {}, "date_shift_options"))
        if selected_items:
            data.update(_form_payload(selected_items, "select"))
        elif selective_import:
            data["selective_import"] = True
        warnings = ["Canvas runs the migration asynchronously after accepting it."]
        if selective_import and not selected_items:
            warnings.append(
                "This migration will stop at waiting_for_select. Use "
                "canvas_get_course_copy_selection, then plan apply_course_copy_selection."
            )
        return await plan_store.create(
            action="course_copy",
            summary=f"Copy course {_sid(source_course_id)} into {_sid(destination_course_id)}",
            preview={
                "source_course_id": _sid(source_course_id),
                "destination_course_id": _sid(destination_course_id),
                "selective_import": selective_import and not bool(selected_items),
                "selected_items": selected_items,
                "date_shift_options": date_shift_options,
            },
            mutations=[Mutation("POST", f"/api/v1/courses/{_sid(destination_course_id)}/content_migrations", data=data)],
            warnings=warnings,
        )

    async def canvas_plan_grade_change(
        self,
        course_id: str | int,
        assignment_id: str | int,
        student_id: str | int | None = None,
        anonymous_id: str | None = None,
        posted_grade: str | None = None,
        excuse: bool | None = None,
        comment: str | None = None,
        group_comment: bool = False,
        comment_attempt: Annotated[
            int | None,
            Field(ge=1, description="Optional submission attempt to associate with the comment"),
        ] = None,
        rubric_assessment: Annotated[
            dict[str, dict[str, Any]] | None,
            Field(description="Rubric criterion IDs mapped to points, rating_id, or comments"),
        ] = None,
    ) -> dict[str, Any]:
        """Plan one student's grade, excuse status, or student-visible submission comment."""
        if (student_id is None) == (anonymous_id is None):
            raise ValueError("Provide exactly one of student_id or anonymous_id")
        identifier = _sid(anonymous_id) if anonymous_id is not None else _sid(student_id)
        target = (
            f"anonymous_submissions/{identifier}"
            if anonymous_id is not None
            else f"submissions/{identifier}"
        )
        endpoint = f"/api/v1/courses/{_sid(course_id)}/assignments/{_sid(assignment_id)}/{target}"
        snapshot_params = {
            "include[]": ["submission_comments", "rubric_assessment", "submission_history", "visibility"]
        }
        before, condition = await self._snapshot(endpoint, snapshot_params)
        data: dict[str, Any] = {}
        if posted_grade is not None:
            data["submission[posted_grade]"] = posted_grade
        if excuse is not None:
            data["submission[excuse]"] = excuse
        if comment is not None:
            if not comment.strip():
                raise ValueError("comment must contain non-whitespace text")
            data["comment[text_comment]"] = comment
            data["comment[group_comment]"] = group_comment
            if comment_attempt is not None:
                data["comment[attempt]"] = comment_attempt
        elif comment_attempt is not None:
            raise ValueError("comment_attempt requires comment")
        if group_comment and comment is None:
            raise ValueError("group_comment requires comment")
        if rubric_assessment:
            data.update(_form_payload(rubric_assessment, "rubric_assessment"))
        if not data:
            raise ValueError("Provide posted_grade, excuse, comment, or rubric_assessment")
        warnings: list[str] = []
        if comment is not None:
            warnings.append(
                "Applying this plan posts the submission comment immediately and Canvas may notify the student."
            )
        if group_comment:
            warnings.append("This comment is marked as a group comment and may notify every group member.")
        previous_comments = before.get("submission_comments") or []
        return await plan_store.create(
            action="grade_change",
            summary=(
                f"Update assignment {_sid(assignment_id)} for "
                f"{'anonymous submission' if anonymous_id is not None else 'student'} {identifier}"
            ),
            preview={
                "before": _compact([before], ("score", "grade", "excused", "workflow_state"))[0],
                "recent_comments": [
                    {
                        "id": item.get("id"),
                        "author_name": item.get("author_name"),
                        "created_at": item.get("created_at"),
                        "comment": _plain_text(item.get("comment"), 2_000),
                    }
                    for item in previous_comments[-5:]
                    if isinstance(item, dict)
                ],
                "changes": data,
                "identifier_type": "anonymous_id" if anonymous_id is not None else "student_id",
                "identifier": identifier,
            },
            mutations=[Mutation("PUT", endpoint, data=data)],
            preconditions=[condition],
            warnings=warnings,
        )

    async def canvas_plan_quiz_submission_grade(
        self,
        course_id: Annotated[str | int, Field(description="Canvas course ID")],
        quiz_id: Annotated[str | int, Field(description="Classic Quiz ID")],
        quiz_submission_id: Annotated[
            str | int, Field(description="Completed Classic Quiz submission ID")
        ],
        question_updates: Annotated[
            list[QuizQuestionGradeUpdate] | None,
            Field(
                max_length=100,
                description="Essay or file-upload question IDs with a score, feedback comment, or both",
            ),
        ] = None,
        fudge_points: Annotated[
            float | None,
            Field(description="Optional signed adjustment to the attempt total"),
        ] = None,
    ) -> dict[str, Any]:
        """Plan essay/file-upload scores or comments, or an overall quiz score adjustment."""
        course_id = _sid(course_id)
        quiz_id = _sid(quiz_id)
        quiz_submission_id = _sid(quiz_submission_id)
        normalized_updates = [
            item
            if isinstance(item, QuizQuestionGradeUpdate)
            else QuizQuestionGradeUpdate.model_validate(item)
            for item in (question_updates or [])
        ]
        if not normalized_updates and fudge_points is None:
            raise ValueError("Provide question_updates, fudge_points, or both")
        if fudge_points is not None and not math.isfinite(fudge_points):
            raise ValueError("fudge_points must be a finite number")

        async with AsyncCanvasClient.from_environment() as client:
            review, state = await self._load_quiz_submission_review(
                client,
                course_id=course_id,
                quiz_id=quiz_id,
                quiz_submission_id=quiz_submission_id,
                student_id=None,
            )
        submission = review["quiz_submission"]
        if submission.get("workflow_state") != "complete":
            raise ValueError("Classic Quiz question grading requires a completed attempt")
        attempt = submission.get("attempt")
        if not isinstance(attempt, int) or attempt < 1:
            raise ValueError("Canvas returned an invalid Classic Quiz attempt number")

        current_questions = {
            str(item["question_id"]): item for item in review["questions"]
        }
        seen: set[str] = set()
        preview_updates: list[dict[str, Any]] = []
        data: dict[str, Any] = {"quiz_submissions[][attempt]": attempt}
        warnings = [
            "The plan is the draft. Canvas has no Classic Quiz grading draft; applying it persists the scores and comments immediately."
        ]
        unavailable_before = False
        for item in normalized_updates:
            question_id = _sid(item.question_id)
            if question_id in seen:
                raise ValueError(f"Question {question_id} appears more than once")
            seen.add(question_id)
            if question_id not in current_questions:
                raise ValueError(
                    f"Question {question_id} is not an essay or file-upload question "
                    f"in quiz submission {quiz_submission_id}; only manually graded "
                    "question types are supported"
                )
            if item.score is None and item.comment is None:
                raise ValueError(
                    f"Question {question_id} requires a score, comment, or both"
                )
            if item.score is not None and item.score < 0:
                raise ValueError(f"Question {question_id} score cannot be negative")
            if item.score is not None and not math.isfinite(item.score):
                raise ValueError(f"Question {question_id} score must be a finite number")
            current = current_questions[question_id]
            if item.score is not None:
                data[
                    f"quiz_submissions[][questions][{question_id}][score]"
                ] = item.score
                unavailable_before = unavailable_before or not current["score_available"]
                points_possible = current.get("points_possible")
                if points_possible is not None and item.score > float(points_possible):
                    warnings.append(
                        f"Question {question_id} score {item.score:g} exceeds its "
                        f"{float(points_possible):g} available points."
                    )
            if item.comment is not None:
                data[
                    f"quiz_submissions[][questions][{question_id}][comment]"
                ] = item.comment
            preview_updates.append(
                {
                    "question_id": question_id,
                    "question_name": current.get("question_name"),
                    "question_text": current.get("question_text"),
                    "student_answer": current.get("answer"),
                    "answer_available": current.get("answer_available"),
                    "before": {
                        "score": current.get("score"),
                        "score_available": current.get("score_available"),
                        "comment": current.get("comment"),
                        "comment_available": current.get("comment_available"),
                    },
                    "changes": {
                        **({"score": item.score} if item.score is not None else {}),
                        **({"comment": item.comment} if item.comment is not None else {}),
                    },
                }
            )
        if fudge_points is not None:
            data["quiz_submissions[][fudge_points]"] = fudge_points
        if unavailable_before:
            warnings.append(
                "Canvas did not expose at least one current per-question score, so that before value cannot be shown."
            )
        preconditions = [
            Precondition(
                endpoint=state["submission_endpoint"],
                params=state["submission_params"],
                fingerprint=fingerprint(state["submission_payload"]),
            ),
            Precondition(
                endpoint=state["answer_endpoint"],
                params=state["answer_params"],
                fingerprint=fingerprint(state["answer_payload"]),
            ),
        ]
        return await plan_store.create(
            action="quiz_submission_grade",
            summary=(
                f"Grade {len(preview_updates)} question(s) in Classic Quiz submission "
                f"{quiz_submission_id}"
            ),
            preview={
                "quiz_submission": submission,
                "question_updates": preview_updates,
                "fudge_points": fudge_points,
            },
            mutations=[
                Mutation(
                    "PUT",
                    f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/"
                    f"{quiz_submission_id}",
                    data=data,
                )
            ],
            preconditions=preconditions,
            warnings=warnings,
        )

    async def _upload(self, client: AsyncCanvasClient, mutation: Mutation) -> Any:
        data = dict(mutation.data or {})
        local_path = data.pop("_local_path")
        expected_size = data.pop("_local_size")
        expected_modified_ns = data.pop("_local_modified_ns")
        expected_sha256 = data.pop("_local_sha256")
        current = await asyncio.to_thread(_file_fingerprint, Path(local_path))
        if current != (expected_size, expected_modified_ns, expected_sha256):
            raise ValueError("The local file changed after the upload plan was reviewed")
        initiated = await client.post(mutation.endpoint, data=data)
        upload_url = initiated.get("upload_url")
        upload_params = initiated.get("upload_params", {})
        if not isinstance(upload_url, str) or not upload_url.startswith("https://"):
            raise ValueError("Canvas returned an invalid upload URL")
        # Never forward the Canvas bearer token to the storage upload host.
        async with httpx2.AsyncClient(timeout=httpx2.Timeout(60.0, connect=5.0), follow_redirects=True) as uploader:
            with open(local_path, "rb") as handle:
                response = await uploader.post(upload_url, data=upload_params, files={"file": (Path(local_path).name, handle)})
            if response.status_code >= 400:
                raise ValueError(f"Canvas storage upload failed with HTTP {response.status_code}")
            try:
                return response.json()
            except Exception:
                return {"status": "uploaded", "location": response.headers.get("Location")}

    async def canvas_apply_change(
        self,
        plan_token: Annotated[str, Field(description="Token returned by a canvas_plan_* tool")],
        confirm: Annotated[Literal[True], Field(description="Must be true after reviewing the plan")],
        progress: Progress = Progress(),
    ) -> dict[str, Any]:
        """Apply a reviewed, short-lived Canvas mutation plan exactly once."""
        if confirm is not True:
            raise ValueError("confirm must be true")
        plan = await plan_store.consume(plan_token)
        results: list[dict[str, Any]] = []
        async with AsyncCanvasClient.from_environment() as client:
            for condition in plan.preconditions:
                current = await client.get(condition.endpoint, condition.params)
                if fingerprint(current) != condition.fingerprint:
                    raise ValueError("Plan is stale because the Canvas record changed; create a new plan")
            await progress.set_total(max(1, len(plan.mutations)))
            created_quiz_id: str | None = None
            for index, mutation in enumerate(plan.mutations):
                label = mutation.label or f"mutation:{index + 1}"
                await progress.set_message("Applying Canvas change")
                if "{created_quiz_id}" in mutation.endpoint and not created_quiz_id:
                    results.append(
                        {
                            "label": label,
                            "status": "skipped",
                            "error": "The quiz was not created, so its dependent item was not sent",
                        }
                    )
                    await progress.increment()
                    continue
                endpoint = mutation.endpoint.replace("{created_quiz_id}", created_quiz_id or "")
                try:
                    if mutation.method == "UPLOAD":
                        value = await self._upload(client, mutation)
                    elif mutation.method == "POST":
                        value = await client.post(endpoint, data=mutation.data, json_data=mutation.json_data)
                    elif mutation.method == "PUT":
                        value = await client.put(endpoint, data=mutation.data, json_data=mutation.json_data)
                    elif mutation.method == "PATCH":
                        value = await client.patch(endpoint, data=mutation.data, json_data=mutation.json_data)
                    elif mutation.method == "DELETE":
                        value = await client.delete(endpoint, params=mutation.data)
                    else:
                        raise ValueError(f"Unsupported mutation method {mutation.method}")
                    if index == 0 and plan.action.endswith("quiz_change") and isinstance(value, dict):
                        raw_id = value.get("id")
                        if raw_id is not None:
                            created_quiz_id = _sid(raw_id)
                    results.append({"label": label, "status": "applied", "result": value})
                except Exception as exc:
                    results.append({"label": label, "status": "failed", "error": str(exc)})
                await progress.increment()
        successes = sum(item["status"] == "applied" for item in results)
        return {
            "action": plan.action,
            "status": "completed" if successes == len(results) else "partial" if successes else "failed",
            "applied": successes,
            "failed": len(results) - successes,
            "results": results,
        }
