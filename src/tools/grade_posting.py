"""Grade visibility and explicit grade release; Canvas docs checked 2026-09-16."""

from typing import Annotated, Any

from pydantic import Field

from action_plans import Mutation, Precondition, fingerprint, plan_store
from canvas_client import AsyncCanvasClient, CanvasAPIError
from tools.assistant import PLAN_ONLY, READ_ONLY, _assistant_tool, _compact
from tools.quiz_accommodations import CanvasID, numeric_id, unique_ids


POST_GRADES = """mutation CanvasMCPPostGrades($input: PostAssignmentGradesInput!) {
  postAssignmentGrades(input: $input) {
    progress { _id state completion message }
    errors { attribute message }
  }
}"""
VISIBILITY_PARAMS = {"include[]": ["visibility"]}


def grade_visibility(submission: dict[str, Any]) -> dict[str, Any]:
    """Use per-submission posting state, never the deprecated assignment.muted."""
    result = _compact([submission], (
        "score", "grade", "entered_score", "entered_grade", "excused",
        "posted_at", "assignment_visible", "workflow_state",
    ))[0]
    posted = (bool(submission["posted_at"]) if "posted_at" in submission else None)
    has_grade = (submission.get("score") is not None or submission.get("grade") is not None
                 or submission.get("excused") is True)
    if not any(k in submission for k in ("score", "grade", "excused")):
        state, visible = "unknown", None
    elif not has_grade:
        state, visible = "no_grade", False
    elif submission.get("assignment_visible") is False:
        state, visible = "assignment_unavailable", False
    elif posted is False:
        state, visible = "hidden", False
    elif posted and submission.get("assignment_visible") is True and has_grade:
        state, visible = "visible", True
    else:
        state, visible = "unknown", None
    return {**result, "posting_status": "posted" if posted else "unposted" if posted is False else "unknown",
            "student_visibility": state, "student_visible": visible,
            "basis": "Canvas posted_at and assignment_visible; this does not prove the student viewed the grade."}


async def grade_readback(client, endpoint):
    """A read failure after an accepted write must not invite replaying that write."""
    try:
        submission = await client.get(endpoint, VISIBILITY_PARAMS)
        if not isinstance(submission, dict):
            raise ValueError("Canvas returned an unexpected submission response")
        return {"readback_status": "available", **grade_visibility(submission)}
    except Exception as exc:
        return {"readback_status": "unavailable", "student_visibility": "unknown",
                "student_visible": None, "error": str(exc),
                "next_step": "The write was accepted. Read the submission again; do not repeat the write just because visibility could not be checked."}


def release_result(value):
    """GraphQL may return errors with HTTP 200; a queued job is not completion."""
    value = value if isinstance(value, dict) else {}
    payload = (value.get("data") or {}).get("postAssignmentGrades") or {}
    errors = [*(value.get("errors") or []), *(payload.get("errors") or [])]
    progress = payload.get("progress") or {}
    if progress.get("_id") is not None:
        # Even a completed Canvas job needs per-student visibility readback.
        result = {"status": "failed" if progress.get("state") == "failed" else "accepted",
                  "progress_id": str(progress["_id"]), "progress": progress}
        if errors:
            result["errors"] = errors
        return result
    if errors:
        # Validation errors before execution or explicit mutation validation
        # failures are definite. A top-level execution error can also occur while
        # serializing an already-started job; without its ID, inspect before retry.
        uncertain = bool(value.get("errors")) and "data" in value
        return {"status": "uncertain" if uncertain else "failed", "errors": errors}
    return {"status": "uncertain", "error": "Canvas did not acknowledge a grade-release job. Inspect visibility before retrying."}


async def apply_grade_release(client, plan):
    mutation = plan.mutations[0]
    try:
        value = await client.post(mutation.endpoint, json_data=mutation.json_data)
        result = release_result(value)
    except Exception as exc:
        definite_failure = isinstance(exc, CanvasAPIError) and 400 <= exc.status < 500
        result = {"status": "failed" if definite_failure else "uncertain", "error": str(exc)}
    return {"action": plan.action, **result,
            "course_id": plan.preview["course_id"], "assignment_id": plan.preview["assignment_id"],
            "student_ids": plan.preview["target_student_ids"], "student_visibility_verified": False,
            "next_step": "Call canvas_get_grade_posting_status with these IDs and progress_id when returned. Wait for completed progress and visible student grades. Inspect uncertain results before retrying."}


class GradePostingTools:
    def __init__(self, mcp):
        mcp.tool(_assistant_tool(self.canvas_get_grade_posting_status), annotations=READ_ONLY,
                 tags={"advanced", "grading", "read"})
        mcp.tool(_assistant_tool(self.canvas_plan_grade_release), annotations=PLAN_ONLY,
                 tags={"advanced", "grading", "plan"})

    async def _load(self, client, course_id, assignment_id, students):
        endpoint = f"/api/v1/courses/{course_id}/assignments/{assignment_id}"
        assignment = await client.get(endpoint)
        if str(assignment.get("id")) != assignment_id or str(assignment.get("course_id")) != course_id:
            raise ValueError("Canvas returned an assignment outside the requested course")
        if assignment.get("anonymous_grading") or assignment.get("anonymize_students"):
            raise ValueError("Use Canvas Gradebook to release anonymous grades; this tool targets explicit student IDs")
        submissions = []
        for student in students:
            submission = await client.get(f"{endpoint}/submissions/{student}", VISIBILITY_PARAMS)
            if str(submission.get("user_id")) != student or str(submission.get("assignment_id")) != assignment_id:
                raise ValueError("Canvas returned a mismatched submission")
            submissions.append(submission)
        return endpoint, assignment, submissions

    async def canvas_get_grade_posting_status(
        self,
        course_id: CanvasID,
        assignment_id: CanvasID,
        student_ids: Annotated[list[CanvasID], Field(min_length=1, max_length=100)],
        progress_id: CanvasID | None = None,
    ) -> dict:
        """Verify saved grade visibility/posting for specific students, and optionally a grade-release background job.

        Check posted_at and assignment_visible; assignment.muted is deprecated.
        An accepted or completed posting job alone does not verify visibility.
        """
        course_id, assignment_id = numeric_id(course_id), numeric_id(assignment_id)
        students = unique_ids(student_ids, "student_ids")
        if len(students) > 100:
            raise ValueError("Use at most 100 students per request")
        async with AsyncCanvasClient.from_environment() as client:
            progress = None
            if progress_id is not None:
                progress = await client.get(f"/api/v1/progress/{numeric_id(progress_id)}")
                if (str(progress.get("context_id")) != course_id or progress.get("context_type") != "Course"
                        or progress.get("tag") != "post_assignment_grades"):
                    raise ValueError("This is not a grade-release job for the requested course")
            _, assignment, submissions = await self._load(client, course_id, assignment_id, students)
        statuses = [{"student_id": str(s["user_id"]), **grade_visibility(s)} for s in submissions]
        if assignment.get("published") is False:
            for item in statuses:
                item.update(student_visibility="assignment_unavailable", student_visible=False)
        all_visible = all(s["student_visible"] is True for s in statuses)
        job_state = (progress or {}).get("workflow_state")
        state = ("failed" if job_state == "failed" else "pending" if progress and job_state != "completed"
                 else "completed" if all_visible else "visibility_not_verified")
        return {"course_id": course_id, "assignment_id": assignment_id, "status": state,
                "assignment": _compact([assignment], ("id", "name", "published", "post_manually", "muted"))[0],
                "students": statuses, "all_visible": all_visible, "progress": progress,
                "next_step": ("Visibility verified in Canvas API." if state == "completed" else
                              "Wait for pending jobs. Inspect hidden/unavailable/unknown grades; do not equate saved or queued with visible.")}

    async def canvas_plan_grade_release(
        self,
        course_id: CanvasID,
        assignment_id: CanvasID,
        student_ids: Annotated[list[CanvasID], Field(min_length=1, max_length=100)],
    ) -> dict:
        """Plan posting/releasing hidden assignment grades to explicit students under a manual posting policy.

        Uses Canvas postAssignmentGrades with onlyStudentIds and gradedOnly=true.
        Save grades first. Review targets, apply once, then check grade posting status.
        Does not change the posting policy or release other students' grades.
        Anonymous grading must be released in Canvas Gradebook.
        """
        course_id, assignment_id = numeric_id(course_id), numeric_id(assignment_id)
        students = unique_ids(student_ids, "student_ids")
        if len(students) > 100:
            raise ValueError("Use at most 100 students per plan")
        async with AsyncCanvasClient.from_environment() as client:
            endpoint, assignment, submissions = await self._load(client, course_id, assignment_id, students)
        if assignment.get("published") is not True:
            raise ValueError("Publish the assignment in Canvas before releasing grades")
        targets, skipped, guards = [], [], [Precondition(endpoint, fingerprint(assignment))]
        for submission in submissions:
            student = str(submission["user_id"])
            visibility = grade_visibility(submission)
            if visibility["student_visibility"] == "visible":
                skipped.append({"student_id": student, "reason": "already_visible"})
                continue
            if visibility["student_visibility"] != "hidden" or submission.get("assignment_visible") is not True:
                raise ValueError(f"Student {student}: requires an existing graded, hidden submission with assignment visibility available")
            targets.append({"student_id": student, **visibility})
            guards.append(Precondition(f"{endpoint}/submissions/{student}",
                fingerprint(submission, kind="submission"), VISIBILITY_PARAMS, fingerprint_kind="submission"))
        if not targets:
            raise ValueError("All requested grades are already visible; no release plan is needed")
        ids = [t["student_id"] for t in targets]
        return await plan_store.create(action="grade_release",
            summary=f"Release assignment {assignment_id} grades to {len(ids)} selected student(s)",
            preview={"course_id": course_id, "assignment_id": assignment_id,
                     "assignment": _compact([assignment], ("id", "name", "post_manually", "muted"))[0],
                     "students": targets, "target_student_ids": ids, "skipped": skipped},
            mutations=[Mutation("POST", "/api/graphql", json_data={"query": POST_GRADES,
                "variables": {"input": {"assignmentId": assignment_id, "onlyStudentIds": ids, "gradedOnly": True}}})],
            preconditions=guards, warnings=[
                "Applying releases the selected students' saved grades and associated feedback; Canvas may notify them.",
                "The assignment posting policy is unchanged. Other students and future hidden grades are not released.",
                "Canvas processes release asynchronously. Verify progress and each student's posted_at/assignment_visible before reporting visible grades.",
                "Canvas may require moderated grades to be finalized first; older deployments may not support selected-student release.",
            ])
