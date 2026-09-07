# Student reporting and discussion monitoring

Implementation branch: `codex/student-reports`, based on `dev` at `d73846f`.

## Accepted scope

- Two faculty reports: an interactive individual-student dashboard and a comprehensive AI learning review of all accessible work in one selected course.
- Both embedded MCP Apps and a localhost browser interface, sharing one UI and data layer. No externally hosted MCP, model-provider connection, third-party auth, skill, or companion plugin.
- Resources define metric semantics, report structure, evidence requirements, and presentation. A tool fallback serves the same canonical references.
- Reuse and preserve existing tools/resources, stdio startup, environment credentials, and eval conversions.
- Complete pagination, authoritative Canvas grades, separate missing/late/excused/ungraded states, student-specific due dates only when available, and honest data freshness/coverage.
- Course outcome reads, rubric definitions, instructor feedback, submission text/history, discussion evidence, and available completed Classic Quiz essay/file-upload responses. No new automated-question review or New Quizzes answer access.
- Extract text PDFs, DOCX, PPTX, XLSX, CSV, and text. Preserve document locations; never execute macros/formulas. Explicit gaps for unsupported, scanned, visual/media, or inaccessible work.
- Existing AI clients analyze resumable evidence batches. No model inference on dashboard selection. No complete-review claim when evidence remains unreviewed.
- Faculty report: scope/coverage, overview, strengths, evidence-supported learning gaps, separate submission/participation patterns, prioritized support and follow-up, evidence appendix. Self-contained, printable HTML export.
- Retain the discussion watcher: independent two-minute polling, initial baseline, restart catch-up, new/edited entries and replies, queue-only AI workflow, faculty-approved drafts through existing plan/apply. No automatic messages or true webhooks.
- Shared account-isolated private SQLite storage outside the repository; no credentials, student text, or identifiers in diagnostics. Pending records survive; temporary report evidence and resolved draft text expire after 30 days. Explicit deletion controls.
- Read-only Canvas reporting; synthetic fixtures only; no personal configuration changes, live student writes, registry publication, or merge to main.

## Work and acceptance checklist

- [x] Commit existing guidance corrections on dev; push; create/push reporting branch.
- [x] Private state, account isolation, retention, durable jobs and watcher leases.
- [x] Shared complete reporting data service and backward-compatible snapshot adapters.
- [x] Evidence inventory, file extraction, resumable AI analysis and safe HTML rendering.
- [x] Canonical report resources, tool fallback, scoped reporting tools and discovery clues.
- [x] Shared accessible UI, embedded MCP Apps adapter, localhost adapter, safe session handling.
- [x] Independent watcher, review tools, stale/uncertain publication and duplicate protections.
- [x] Launcher commands and Git/npm packaging, documentation and installation verification.
- [x] Synthetic backend/transport/privacy tests, visual/keyboard/print QA, real synthetic AI review evaluation, measured calls/time/payload/coverage and usage where available.
- [x] Final requirement audit and clean git diff. Publication is recorded in the `codex/student-reports` branch history.

Results and limits are recorded in [REPORTING_VALIDATION.md](REPORTING_VALIDATION.md).
The embedded UI was tested with an MCP Apps SDK host harness; rendering inside
Codex Desktop itself remains unverified and the browser fallback is available.
The one synthetic AI review was manually assessed, not independently benchmarked;
per-review model billing metadata was unavailable. No efficiency percentage is claimed.

## Research (verified 2026-09-07)

- [Canvas instructor reports](https://community.instructure.com/en/kb/articles/660639-how-do-i-view-and-download-reports-in-course-analytics): missing, late, excused work; roster and activity reports.
- [KTH faculty use cases](https://intra.kth.se/en/utbildning/systemstod/data-informed-education/course-analytics/examples-1.1446629): individual/class progress, assessment performance and support opportunities. These establish useful categories, not popularity rankings.
- [Submissions](https://developerdocs.instructure.com/services/canvas/resources/submissions), [Enrollments](https://developerdocs.instructure.com/services/canvas/resources/enrollments), [Analytics](https://developerdocs.instructure.com/services/canvas/resources/analytics), [Outcome results](https://developerdocs.instructure.com/services/canvas/resources/outcome_results), [Discussions](https://developerdocs.instructure.com/services/canvas/resources/discussion_topics).
- [Canvas analytics interpretation](https://community.instructure.com/en/kb/articles/660625-how-do-i-view-course-analytics-in-a-course-as-an-instructor): page views are not evidence of academic integrity.
- [FastMCP custom HTML apps](https://gofastmcp.com/apps/low-level) and [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview), verified through Context7 and installed FastMCP 4.0.2. Host capability checks and browser fallback are required; Codex rendering is not assumed.

## Validation rules

Tests must cover >100 submissions, unknown/ungraded values, grading periods, weighted Canvas grades, excused work, unavailable analytics/outcomes, and modules without completion rules. UI tests must switch students while requests resolve out of order, test both adapters and fallback, and verify accessible tables and printable output. Evidence tests must cover all revisions, deduplication with retained provenance, extraction locations, inaccessible quiz answers, unsupported files, resume/cancel/delete, and invalid citations. Watcher tests must cover replies to old posts, >10 replies, cached/new entry overlays, edits/deletions, restart recovery, duplicates, errors, stale drafts, and ambiguous publication. Report actual metrics; no invented efficiency percentages.
