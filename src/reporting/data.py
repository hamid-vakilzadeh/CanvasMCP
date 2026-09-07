"""Complete, provenance-aware Canvas reads shared by reports and snapshots."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from canvas_client import AsyncCanvasClient
from reporting.common import now, number, sid, plain, safe_url


class CountedClient:
    """Count logical Canvas calls (HTTP retries are deliberately not inferred)."""
    def __init__(self, client):
        self.client, self.calls = client, 0

    def __getattr__(self, name):
        return getattr(self.client, name)

    async def get(self, *args, **kwargs):
        self.calls += 1
        return await self.client.get(*args, **kwargs)

    async def page(self, *args, **kwargs):
        self.calls += 1
        return await self.client.page(*args, **kwargs)


def warning(section: str, error: Exception) -> dict:
    return {"section": section, "code": getattr(error, "code", "unavailable"),
            "message": "Canvas data is unavailable for this section; it has not been treated as zero."}


async def all_pages(client, endpoint: str, params: dict | None = None, *, array_key: str | None = None) -> dict:
    """Follow every page, retaining a partial result and explicit continuation on error."""
    items, cursor, seen, linked = [], None, set(), {}
    calls = 0
    while True:
        try:
            calls += 1
            page = await client.page(endpoint, params=params, cursor=cursor, limit=100)
            values = page["items"]
            for value in values:
                if array_key and isinstance(value, dict) and array_key in value:
                    items.extend(value[array_key])
                    for key, extra in (value.get("linked") or {}).items():
                        linked.setdefault(key, []).extend(extra if isinstance(extra, list) else [extra])
                else:
                    items.append(value)
            next_cursor = page.get("next_cursor")
            if not next_cursor:
                return {"items": items, "next_cursor": None, "complete": True, "page_calls": calls, "linked": linked}
            if next_cursor in seen:
                raise ValueError("Canvas pagination repeated a cursor")
            seen.add(next_cursor)
            cursor = next_cursor
        except Exception as exc:
            return {"items": items, "next_cursor": cursor, "complete": False,
                    "page_calls": calls, "linked": linked, "warning": warning("pagination", exc)}


async def collect_snapshot(client, course_id: str, student_id: str, *, include_activity: bool = True) -> dict:
    course_id, student_id = sid(course_id), sid(student_id)
    calls = {
        "enrollments": all_pages(client, f"/api/v1/courses/{course_id}/enrollments",
                                  {"user_id": student_id, "type[]": ["StudentEnrollment"]}),
        "progress": client.get(f"/api/v1/courses/{course_id}/users/{student_id}/progress"),
        "submissions": all_pages(client, f"/api/v1/courses/{course_id}/students/submissions",
                                 {"student_ids[]": [student_id], "include[]": ["assignment"]}),
    }
    if include_activity:
        calls["analytics"] = client.get(f"/api/v1/courses/{course_id}/analytics/users/{student_id}/activity")
    results = await asyncio.gather(*calls.values(), return_exceptions=True)
    snapshot: dict[str, Any] = {"course_id": course_id, "student_id": student_id, "warnings": [],
                                "retrieved_at": now(), "coverage": {}}
    for key, result in zip(calls, results, strict=True):
        if isinstance(result, Exception):
            snapshot["warnings"].append(warning(key, result))
            snapshot["coverage"][key] = {"complete": False, "available": False}
        elif key in {"submissions", "enrollments"}:
            snapshot[key] = result["items"]
            snapshot[f"{key}_next_cursor"] = result["next_cursor"]
            snapshot["coverage"][key] = {"complete": result["complete"], "available": True,
                                           "count": len(result["items"]), "page_calls": result["page_calls"]}
            if not result["complete"]:
                snapshot["warnings"].append({**result["warning"], "section": key})
        else:
            snapshot[key] = result
            snapshot["coverage"][key] = {"complete": True, "available": True}
    return snapshot


def compact_snapshot(snapshot: dict, *, activity_key: str = "analytics") -> dict:
    """Keep historical tool/resource field names and omit submission bodies."""
    result = dict(snapshot)
    if activity_key != "analytics" and "analytics" in result:
        result[activity_key] = result.pop("analytics")
    if activity_key != "analytics":
        result["warnings"] = [{**w, "section": activity_key if w["section"] == "analytics" else w["section"]}
                              for w in result.get("warnings", [])]
        result["coverage"] = {activity_key if k == "analytics" else k: v
                              for k, v in result.get("coverage", {}).items()}
    if "submissions" in result:
        fields = ("id", "assignment_id", "workflow_state", "submitted_at", "late", "missing", "excused",
                  "score", "grade", "assignment")
        result["submissions"] = [{k: row[k] for k in fields if k in row} for row in result["submissions"]]
    if activity_key == 'analytics':
        result['warnings'] = [{**w, 'error': w.get('error', w.get('message'))} for w in result.get('warnings', [])]
    return result


def grades_from(enrollments: list[dict]) -> dict:
    """Canvas grades only. Never invent a weighted/current grade from assignment rows."""
    fields = ("current_score", "current_grade", "final_score", "final_grade", "unposted_current_score",
              "unposted_current_grade", "unposted_final_score", "unposted_final_grade")
    selected = next((e for e in enrollments if e.get("enrollment_state") == "active"),
                    enrollments[0] if enrollments else {})
    grades = selected.get("grades") or {}
    result = {key: grades.get(key, selected.get(f"computed_{key}")) for key in fields}
    result["periods"] = {key: value for key, value in selected.items()
                         if "grading_period" in key or key.startswith("current_period_")}
    result["label"] = "Canvas-calculated grades; current and final use different grading denominators."
    return result


def assignment_row(submission: dict) -> dict:
    assignment = submission.get("assignment") or {}
    score, possible = number(submission.get("score")), number(assignment.get("points_possible"))
    # Flags are orthogonal: a late submission may also be awaiting grading.
    flags = [name for name in ("excused", "missing", "late") if submission.get(name) is True]
    if submission.get("workflow_state") in {"submitted", "pending_review"} or (
        submission.get("submitted_at") and score is None and not submission.get("excused")
    ):
        flags.append("awaiting_grading")
    status = ("excused" if "excused" in flags else "missing" if "missing" in flags else
              "awaiting_grading" if "awaiting_grading" in flags else "graded" if score is not None else
              "submitted" if submission.get("submitted_at") else "not_submitted")
    # Assignment.due_at can be the teacher's general date rather than this student's override.
    due = submission.get("cached_due_date") or submission.get("due_at")
    return {"assignment_id": str(submission.get("assignment_id", assignment.get("id", ""))),
            "submission_id": str(submission["id"]) if submission.get("id") is not None else None,
            "title": assignment.get("name", "Assignment"), "status": status, "flags": flags,
            "score": score, "grade": submission.get("grade"), "points_possible": possible,
            "percent": round(100 * score / possible, 2) if score is not None and possible and possible > 0 else None,
            "submitted_at": submission.get("submitted_at"), "graded_at": submission.get("graded_at"),
            "posted_at": submission.get("posted_at"), "student_due_at": due,
            "due_date_source": "submission" if due else "unavailable",
            "general_due_at": assignment.get("due_at"), "attempt": submission.get("attempt"),
            "url": safe_url(assignment.get("html_url")), "quiz_id": assignment.get("quiz_id"),
            "is_new_quiz": assignment.get("is_quiz_lti_assignment", False),
            "assignment_group_id": assignment.get("assignment_group_id"),
            "visibility": {k: submission[k] for k in ("assignment_visible", "posted_at") if k in submission}}


def activity_summary(analytics: dict | None) -> dict:
    if not isinstance(analytics, dict):
        return {"available": False, "days": [], "last_participation_at": None}
    days: dict[str, dict] = {}
    for timestamp, views in (analytics.get("page_views") or {}).items():
        day = timestamp[:10]
        row = days.setdefault(day, {"date": day, "views": 0, "participations": 0})
        row["views"] += number(views) or 0
    dates = []
    for item in analytics.get("participations") or []:
        timestamp = item.get("created_at")
        if timestamp:
            dates.append(timestamp)
            row = days.setdefault(timestamp[:10], {"date": timestamp[:10], "views": 0, "participations": 0})
            row["participations"] += 1
    return {"available": True, "days": [days[d] for d in sorted(days)],
            "last_participation_at": max(dates) if dates else None,
            "source_updated_at": analytics.get("updated_at"),
            "interpretation": "Recorded Canvas activity only; it does not establish attendance, effort, understanding, or misconduct."}


async def student_report(client, course_id: str, student_id: str, *, sections: list[str] | None = None) -> dict:
    course_id, student_id = sid(course_id), sid(student_id)
    sections = sections or ["overview", "assignments", "progress"]
    if set(sections) - {"overview", "assignments", "progress", "activity", "rubrics", "outcomes"}:
        raise ValueError("Unsupported report section")
    started = time.monotonic()
    client = CountedClient(client)
    snapshot = await collect_snapshot(client, course_id, student_id, include_activity="activity" in sections)
    warnings = snapshot["warnings"]
    try:
        course = await client.get(f"/api/v1/courses/{course_id}", {"include[]": ["term"]})
    except Exception as exc:
        course = {"id": course_id}
        warnings.append(warning("course", exc))
    enrollments = snapshot.get("enrollments") or []
    if not isinstance(enrollments, list):
        enrollments = []
    if not enrollments and snapshot['coverage'].get('enrollments', {}).get('complete'):
        raise ValueError('Canvas returned no student enrollment in this course')
    user = next((e.get("user") for e in enrollments if e.get("user")), {})
    rows = [assignment_row(s) for s in snapshot.get("submissions", [])]
    complete = snapshot["coverage"].get("submissions", {}).get("complete", False)
    counts = {state: sum(state in row["flags"] for row in rows)
              for state in ("missing", "late", "excused", "awaiting_grading")}
    progress = snapshot.get("progress") or {}
    required = number(progress.get("requirement_count"))
    completed = number(progress.get("requirement_completed_count"))
    result = {
        "schema_version": 1, "course_id": course_id, "student_id": student_id,
        "course": {k: course[k] for k in ("id", "name", "course_code", "term", "time_zone") if k in course},
        "student": {"id": student_id, "name": user.get("name") or user.get("short_name") or f"Student {student_id}"},
        "grades": grades_from(enrollments), "counts": counts, "counts_complete": complete,
        "assignments": rows, "progress": {**progress, "configured": required is not None and required > 0,
            "percent": round(100 * completed / required, 1) if required and required > 0 and completed is not None else None},
        "activity": activity_summary(snapshot.get("analytics")), "rubrics": [], "outcomes": [],
        "coverage": snapshot["coverage"], "warnings": warnings, "retrieved_at": snapshot["retrieved_at"],
        "metrics": {"elapsed_seconds": 0, "submission_page_calls": snapshot["coverage"].get("submissions", {}).get("page_calls", 0)},
    }
    if "progress" in sections:
        modules = await all_pages(client, f"/api/v1/courses/{course_id}/modules",
                                  {"student_id": student_id, "include[]": ["items", "content_details"]})
        for module in modules['items']:
            if module.get('items_count', 0) > len(module.get('items') or []):
                items = await all_pages(client, f"/api/v1/courses/{course_id}/modules/{sid(module['id'])}/items",
                                        {'student_id': student_id, 'include[]': ['content_details']})
                module['items'] = items['items']
                if not items['complete']:
                    modules['complete'] = False
                    modules['warning'] = items['warning']
        result["modules"] = [{k: m[k] for k in ("id", "name", "state", "completed_at", "items", "items_count") if k in m}
                             for m in modules["items"]]
        result["coverage"]["modules"] = {"complete": modules["complete"]}
        if not modules["complete"]:
            warnings.append({**modules["warning"], "section": "modules"})
    if "outcomes" in sections:
        outcomes = await all_pages(client, f"/api/v1/courses/{course_id}/outcome_results",
                                   {"user_ids[]": [student_id], "include[]": ["alignments"], "include_hidden": False},
                                   array_key="outcome_results")
        rollups = await all_pages(client, f"/api/v1/courses/{course_id}/outcome_rollups",
                                  {"user_ids[]": [student_id], "include[]": ["outcomes"]}, array_key="rollups")
        result["outcomes"] = outcomes["items"]
        result["outcome_rollups"] = rollups["items"]
        result["outcome_definitions"] = rollups["linked"].get("outcomes", [])
        result["coverage"]["outcomes"] = {"complete": outcomes["complete"] and rollups["complete"]}
        for name, value in (("outcomes", outcomes), ("outcome_rollups", rollups)):
            if not value["complete"]:
                warnings.append({**value["warning"], "section": name})
    if "rubrics" in sections:
        semaphore = asyncio.Semaphore(4)

        async def rubric(row):
            async with semaphore:
                assignment_id = sid(row["assignment_id"])
                endpoint = f"/api/v1/courses/{course_id}/assignments/{assignment_id}"
                try:
                    assignment, submission = await asyncio.gather(
                        client.get(endpoint), client.get(f"{endpoint}/submissions/{student_id}",
                            {"include[]": ["rubric_assessment", "submission_comments", "visibility"]}))
                    if assignment.get('anonymous_grading') or submission.get('assignment_visible') is False:
                        raise ValueError('Identity or assignment visibility is restricted')
                    return {"assignment_id": assignment_id, "title": row["title"],
                            "criteria": assignment.get("rubric") or [], "assessment": submission.get("rubric_assessment") or {},
                            "comments": [{"comment": c.get("comment"), "created_at": c.get("created_at")}
                                         for c in submission.get("submission_comments") or []],
                            "url": row["url"]}
                except Exception as exc:
                    warnings.append(warning("rubrics", exc))
                    return None
        result["rubrics"] = [r for r in await asyncio.gather(*(rubric(row) for row in rows)) if r]
        result["coverage"]["rubrics"] = {"complete": len(result["rubrics"]) == len(rows) and complete}
    result["metrics"]["elapsed_seconds"] = round(time.monotonic() - started, 3)
    result['metrics']['logical_canvas_calls'] = client.calls
    result['metrics']['serialized_bytes'] = len(json.dumps(result, ensure_ascii=False).encode())
    return result
