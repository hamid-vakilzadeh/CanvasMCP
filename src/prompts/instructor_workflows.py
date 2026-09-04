"""FastMCP prompt templates for common instructor workflows."""

from __future__ import annotations

from fastmcp import FastMCP


def register_instructor_prompts(mcp: FastMCP) -> None:
    """Register course-authoring, grading, progress, and outreach prompts."""

    @mcp.prompt(
        "build_canvas_course",
        title="Build a Canvas Course",
        description="Plan and create an accessible Canvas course structure from learning objectives.",
        tags={"canvas", "authoring", "course-design"},
    )
    def build_canvas_course(
        course_id: str,
        learning_objectives: str,
        design_notes: str = "",
    ) -> str:
        """Build a course in Canvas.

        Args:
            course_id: Canvas course ID to inspect and develop.
            learning_objectives: Intended course or module learning objectives.
            design_notes: Optional audience, schedule, accessibility, or style requirements.
        """
        return f"""Help the faculty member build Canvas course {course_id}.

Learning objectives:
{learning_objectives}

Additional design notes:
{design_notes or "No additional notes were supplied."}

First inspect canvas://courses/{course_id}/overview and read
canvas://reference/content-creation. Propose a coherent module sequence before
changing Canvas. Use canvas_plan_page_change, canvas_plan_assignment_change,
canvas_plan_discussion_change, canvas_plan_module_change,
canvas_plan_quiz_change, canvas_plan_file_upload, and
canvas_plan_course_copy as appropriate. Preserve accessible headings, link text,
tables, color contrast, and a clear student learning path. Present every write
preview to the faculty member; call canvas_apply_change only after they approve
it explicitly. Use canvas_search_tools for an advanced action that is not
initially visible."""

    @mcp.prompt(
        "grade_with_rubric",
        title="Grade a Canvas Submission with a Rubric",
        description="Review one submission and prepare evidence-based rubric feedback.",
        tags={"canvas", "grading", "rubric"},
    )
    def grade_with_rubric(
        course_id: str,
        assignment_id: str,
        student_id: str,
        grading_focus: str = "",
        anonymous: bool = False,
    ) -> str:
        """Prepare a rubric-based grade.

        Args:
            course_id: Canvas course ID.
            assignment_id: Canvas assignment ID.
            student_id: Canvas student ID, or an anonymous identifier when anonymous is true.
            grading_focus: Optional faculty guidance about criteria or feedback.
            anonymous: Whether student_id is an anonymous grading identifier.
        """
        return f"""Review the submission for course {course_id}, assignment
{assignment_id}, {'anonymous submission' if anonymous else 'student'} {student_id}. Use
canvas_get_submission_review with {'anonymous_id' if anonymous else 'student_id'}={student_id} and
inspect the assignment rubric before evaluating the work. Follow the rubric
criterion by criterion, cite evidence from the submission, distinguish rubric
evidence from coaching suggestions, and do not infer facts that are absent.
Preserve Canvas anonymous-grading rules and never reveal an identity Canvas has
hidden. Faculty guidance: {grading_focus or "Use the published rubric as written."}

Prepare any score, rubric assessment, or comment with
canvas_plan_grade_change using {'anonymous_id' if anonymous else 'student_id'}={student_id}.
Show the complete preview and call
canvas_apply_change only after explicit faculty approval."""

    @mcp.prompt(
        "review_student_progress",
        title="Review Canvas Student Progress",
        description="Review one student's course progress using Canvas evidence.",
        tags={"canvas", "student", "progress"},
    )
    def review_student_progress(
        course_id: str,
        student_id: str,
        focus: str = "",
    ) -> str:
        """Review student progress.

        Args:
            course_id: Canvas course ID.
            student_id: Canvas student ID.
            focus: Optional question or progress criterion from the faculty member.
        """
        return f"""Review student {student_id} in Canvas course {course_id}.
Read canvas://courses/{course_id}/students/{student_id}/snapshot and retrieve
additional evidence only when necessary. Faculty focus:
{focus or "Summarize participation, submitted work, missing work, and current performance."}

Separate observed Canvas facts from interpretation. Describe explicit matched
criteria rather than predicting that a student is “at risk.” Mention unavailable
or permission-restricted sections. Omit email, login, and SIS identifiers unless
the faculty member explicitly requests them and Canvas permits access. Do not
contact or grade the student unless the faculty member separately approves a
write preview followed by canvas_apply_change."""

    @mcp.prompt(
        "contact_students",
        title="Contact Canvas Students Privately",
        description="Identify an audience and prepare private Canvas Inbox outreach.",
        tags={"canvas", "inbox", "outreach"},
    )
    def contact_students(
        course_id: str,
        audience: str,
        purpose: str,
        tone: str = "supportive and concise",
    ) -> str:
        """Prepare private student outreach.

        Args:
            course_id: Canvas course ID.
            audience: Student names, IDs, or explicit selection criteria.
            purpose: Reason for the outreach and desired response or action.
            tone: Desired message tone.
        """
        return f"""Prepare private Canvas Inbox outreach for course {course_id}.
Audience: {audience}
Purpose: {purpose}
Tone: {tone}

Resolve the intended recipients with canvas_list_course_people or
canvas_analyze_student_engagement and show the evidence used for a criteria-based
selection. Draft a respectful message that discloses no other student's
information. Use canvas_plan_communication. For multiple students, require a
separate private conversation for each recipient; never expose the recipient
list through a group conversation. Show recipient count, recipients, subject,
and message preview. Call canvas_apply_change only after explicit faculty
approval."""

    @mcp.prompt(
        "review_grading_queue",
        title="Review the Canvas Grading Queue",
        description="Triage submitted work awaiting instructor review.",
        tags={"canvas", "grading", "workflow"},
    )
    def review_grading_queue(course_id: str, assignment_id: str = "") -> str:
        """Review work awaiting grading.

        Args:
            course_id: Canvas course ID.
            assignment_id: Optional Canvas assignment ID to narrow the queue.
        """
        assignment_scope = (
            f"assignment {assignment_id}" if assignment_id else "all assignments"
        )
        return f"""Review the Canvas grading queue for course {course_id}, scoped
to {assignment_scope}. Use canvas_list_grading_queue, group submissions by
assignment and urgency, and report counts for unreviewed, late, and missing work.
Do not treat missing work as submitted work. Open ordinary submissions with
canvas_get_submission_review. For a completed Classic Quiz that needs manual
question scoring, use canvas_get_quiz_submission_review and report explicitly
when Canvas withholds answer or current-score fields. Preserve anonymous grading.
Recommend a review order, but do not assign grades or post comments unless the
faculty member explicitly requests a preview with canvas_plan_grade_change or
canvas_plan_quiz_submission_grade and then approves canvas_apply_change."""
