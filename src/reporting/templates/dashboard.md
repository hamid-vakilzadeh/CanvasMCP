# Individual student dashboard

Verified 2026-09-07. Audience: the faculty member. Purpose: inspect the student's
current course position and decide which work needs closer review.

Use `canvas_get_student_report` for structured data, or `canvas_open_student_dashboard`
for the interactive view. Reuse course and student IDs. Student selection calls
Canvas through the UI adapter without model inference. Load activity, rubrics,
and outcomes only when requested. Refresh bypasses the 60-second memory cache.

Show student, course, retrieval time, coverage notices, Canvas current/final
grades, missing/late/excused/awaiting-grading counts, a dated submission timeline,
and an accessible assignment table. Expand module requirements, rubric criteria
and feedback, outcomes, and recorded activity. Unknown values are unavailable,
not zero. A zero score is valid. Flags can overlap; do not sum them into a total.
An unsubmitted item is not automatically late or missing. Student-specific due
dates are shown only when Canvas returns one on the submission. General dates
are labeled separately. Module progress with no requirements is not 0% complete.

Use Canvas-calculated enrollment grades; never average assignment percentages.
Show grading-period metadata and unposted grades separately. Retrieval time is
not the source's update time. Page views and participation events do not establish
attendance, effort, conceptual understanding, or academic integrity.

This is an exploratory factual report. Do not add speculative risk scores,
learning-gap diagnoses, or comparisons that reconstruct anonymous identities.
Use restrained color, readable labels, keyboard controls, and tables alongside
charts. Keep credentials on the local server and student information in private
local state. Export only at the faculty member's request.

Official sources: [Enrollments](https://developerdocs.instructure.com/services/canvas/resources/enrollments),
[Submissions](https://developerdocs.instructure.com/services/canvas/resources/submissions),
[Modules](https://developerdocs.instructure.com/services/canvas/resources/modules),
[Analytics](https://developerdocs.instructure.com/services/canvas/resources/analytics),
[Outcome results](https://developerdocs.instructure.com/services/canvas/resources/outcome_results).
