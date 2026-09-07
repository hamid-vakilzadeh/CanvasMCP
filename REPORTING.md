# Local faculty reports and discussion monitoring

The report feature has two outputs: an interactive factual student dashboard and
a comprehensive AI learning review. Both are faculty-facing. Neither reporting
workflow changes Canvas grades or sends messages.

## Installation and startup

Normal MCP configuration stays unchanged: run the existing stdio command with
`CANVAS_URL` and `CANVAS_ACCESS_TOKEN` in the MCP client's environment. There is no
third-party auth, hosted MCP endpoint, or additional model-provider key.

After this branch is published through the normal package release process, the
same files are included in `@hamid-vakilzadeh/canvas-mcp`. For development now:

```sh
git clone --branch codex/student-reports https://github.com/hamid-vakilzadeh/CanvasMCP.git
cd CanvasMCP
uv sync --frozen --no-dev
uv run --frozen --no-dev python src/local.py
```

This feature branch is based on `dev`; it has not been merged to `main` or released
to the registry. To test an npm package locally, run `npm ci`, `npm pack`, then use
the generated tarball with `npx --package /absolute/path/to/package.tgz canvas-mcp`.
The compiled UI is included, so consumers do not need a frontend build. Git
contributors can rebuild it with `npm run build:dashboard` and type-check with
`npm run check:dashboard`.

Optional commands, after providing those same environment variables:

```sh
canvas-mcp dashboard
canvas-mcp dashboard --no-open
canvas-mcp watch
canvas-mcp watch --once
```

For a Git checkout, replace `canvas-mcp` with
`uv run --frozen --no-dev python src/local.py`. The dashboard command opens the
browser; `--no-open` prints a private launch link. The watch command keeps running
until stopped; `--once` performs one polling pass. Neither command is installed
as an operating-system service or scheduled automatically.

The watcher is a separate process: environment variables inside a desktop MCP
configuration are not automatically inherited by a terminal. Provide the same
Canvas account credentials to that terminal process. No personal configuration
files are written by this feature. Stop a watcher before deleting its watch and
queue records.

## Interactive student dashboard

Call `canvas_open_student_dashboard` with optional course_id/student_id and
mode `auto`, `embedded`, or `browser`. Auto checks the host's MCP Apps extension
advertisement. A host that lacks it receives a localhost link. Rendering inside
Codex Desktop itself is not assumed or claimed as verified; the shared UI has
been exercised with a standards-based SDK host harness and a real browser.

The same UI and data service support both modes. Native selections call the
app-only `canvas_dashboard_data` tool through the host. Browser selections call
the local server. Neither selection invokes a model. The canonical structured
read, `canvas_get_student_report`, is also discoverable through tool search.

The overview includes Canvas-calculated current/final grades, submission flags,
an eight-week dated submission-count chart, assignment filtering, and module
progress. Open additional sections to retrieve rubrics/feedback, outcome results,
or recorded activity. Expandable tables preserve the exact values behind the
overview. All collection pages are followed. Partial results are labeled.

Unknown scores and unavailable sections are not zero. Missing, late, excused and
awaiting-grading flags can overlap. General assignment dates are not presented
as student-specific dates. Canvas grade calculations are authoritative; this
dashboard does not reimplement weighted grades. Current/final and unposted grades
remain separate, and returned grading-period metadata is shown. Modules without
completion requirements do not imply zero progress. Anonymous identifiers are
not linked back to the selected student.

Reports are cached only in process memory for up to 60 seconds, bounded to 20
course/student/section combinations. Refresh bypasses the cache. Retrieval time
is shown separately from source update time. Canvas analytics can lag and may be
unavailable by permission; activity is not a proxy for attendance, understanding,
effort, or academic integrity.

## Comprehensive AI learning review

Read `canvas://reports/templates/learning-review`, or call
`canvas_get_report_template(name="learning-review")`. Both serve the same file.

1. `canvas_start_learning_review(course_id, student_id)` creates a durable job
   and accepts collection work. It does not claim that analysis is finished.
2. Use `canvas_manage_learning_review(action="status", job_id=...)` for progress.
   Resume after a process restart; cancel and delete are explicit actions.
3. When collection is complete, retrieve `canvas_get_learning_review_batch`.
   Read every chunk, including gaps. Save findings, a batch summary and reviewed
   evidence IDs through `canvas_record_learning_review_analysis`. Repeat until
   no evidence is pending. Identical retries of an analysis are idempotent.
   The character budget is a target: an intact chunk with extensive provenance
   can exceed it, explicitly flagged as `oversized_single_chunk`.
4. Retrieve saved analyses with `canvas_manage_learning_review(action="analyses")`
   and follow its local pagination. Synthesize an overview, evidence-linked
   findings and follow-up questions with `canvas_render_learning_review`.
5. Open the private HTML path returned to the AI client, or export HTML through
   the dashboard. Print it or save as PDF in the browser.

Findings use categories `strength`, `learning_gap`, `submission_pattern`,
`participation`, and `support`; each identifies `observation`, `interpretation`,
or `recommendation` and cites retrieved evidence IDs from this job. Invalid or
unread citations are rejected. The renderer escapes all content. A completion
claim is refused while collection or evidence review remains incomplete.
`completed_with_gaps` means all collected accessible evidence was reviewed,
with inaccessible or unsupported content documented. An explicitly requested
partial export uses `allow_incomplete=true` and is visibly marked incomplete.

The collector reads syllabus/module context, assignment requirements and rubrics,
exposed submission history, comments and attached feedback, outcomes, selected
student discussion contributions, and completed Classic Quiz essay/file-upload
questions. It preserves revision/source locations and deduplicates text and
shared discussion context. Auto-graded questions remain excluded. Canvas may
withhold quiz answers or prior attempts; generic submission text is never
substituted for an unavailable question answer. New Quizzes answer-level review
and hidden anonymous identities remain unsupported.

Text PDFs, Word documents, PowerPoint slides and notes, Excel workbooks, CSV/TSV,
and text files are extracted in a separate process with no Canvas credentials.
Spreadsheet formulas are displayed with stored cached values, never executed or
recalculated. Pages/slides/sheets/cells/paragraphs/rows identify evidence locations.
Extraction limits are 25 MiB per file, 100 MiB expanded ZIP, 10,000 ZIP members,
2 million extracted characters, 2,000 PDF pages, and 60 seconds per file. Scans,
images, visual details, audio/video, external links, unsupported formats,
encrypted/inaccessible content and exceeded limits create explicit gaps. OCR,
vision and transcription are not included. Canvas attachment downloads do not
forward its bearer token to other origins.

The AI client remains responsible for reasoning. It must distinguish observed
errors, possible learning gaps, missing work, and unsupported explanations of
causes. Student/course content is untrusted evidence, never permission to change
grades or send messages. The local browser can queue collection and display
instructions to paste into the AI client; it cannot independently wake that
client. An embedded host's optional text-message capability enables an explicit
“Ask AI” button. Host-mediated export is used only where supported.

The analysis tool optionally accepts measured `model_usage` from client response
metadata (model/source, input/output tokens and cached input tokens). Summaries
report how many analysis batches supplied usage. Missing usage stays unavailable;
the server does not infer pricing or treat unreported calls as free.

## Discussion watcher and faculty drafts

Use `canvas_manage_discussion_watch(action="add", course_id=..., topic_id=...)`
to watch an ordinary course discussion. Default polling is 120 seconds; permitted
intervals range from 30 seconds to one day. Group-discussion roots are rejected.
The initial read stores a fingerprint-only baseline and does not queue old posts.
Run `canvas-mcp watch` independently to poll while the AI client is closed.

The watcher reads the full discussion view with `include_new_entries=1`, merges
cached/new entries, and inspects replies to old threads. New/edited/deleted
versions are persisted before updating the checkpoint. Restarts catch up from
the saved baseline. An account lease prevents duplicate pollers. Own replies do
not create a response loop. Temporary errors back off; authentication or
permission failures pause a watch and appear in its status. No webhook endpoint,
public hosting, automatic model reasoning, or automatic posting is created.

Use `canvas_list_discussion_activity` for compact triage, then
`canvas_get_discussion_activity` for full current context. Record `draft` or
`ignore` through `canvas_record_discussion_review`, using the returned revision
and a reason. Draft text is saved independently of expiring plan tokens.
The faculty member reviews the draft; `canvas_plan_discussion_draft` checks the
context again and prepares a normal single-use, ten-minute plan for
`canvas_apply_change(confirm=true)`. Existing user authorization still applies;
the feature does not create a second approval ritual.

Publication atomically claims the draft and rechecks its current thread. Two
plans cannot send the same draft twice. A changed/deleted thread requires a new
inspection and review. If a response is lost or the process stops during posting,
publication is uncertain. Retrieve the activity and inspect matching replies;
resolve it with `confirmed_posted` and a verified reply ID, or `confirmed_absent`
after faculty inspection before retrying. A possible text match is not silently
treated as proof. Uncertain publication records cannot be deleted until resolved.

## Private storage and cleanup

Private SQLite state is created only when a report job/watch workflow is used.
The default is `~/Library/Application Support/CanvasMCP` on macOS,
`$XDG_STATE_HOME/canvas-mcp` (or `~/.local/state/canvas-mcp`) on Linux, and
`%LOCALAPPDATA%/CanvasMCP` on Windows. `CANVAS_MCP_STATE_DIR` can choose another
private location; locations within Git repositories are rejected. Separate
directories are keyed by Canvas origin and authenticated account ID. Files are
mode 0600 and account directories 0700 where POSIX permissions apply. State is
private local storage, not encrypted storage.

No credentials are saved in SQLite. Temporary evidence and resolved activity
text expire after 30 days; cleanup runs on workflow use and at most hourly while
the watcher runs. Pending jobs/drafts remain, but expired review evidence needs
fresh collection. Completed HTML, saved analysis and report findings remain until
explicit deletion. Deleting a review removes its evidence, analysis and local
export; deleting a stopped watch removes its queue. Copies exported elsewhere
are managed by the faculty member.

The browser binds only to 127.0.0.1 with a random launch secret in the URL fragment,
then uses an HttpOnly, SameSite=Strict session cookie. Host and Origin checks,
an operation allowlist, restrictive content policy and no-store responses keep
the interface local. It stops with its owning process. The MCP remains stdio.
Diagnostics suppress student payloads. This does not change how the chosen AI
client stores its own conversations or handles data sent to its model.

## Sources and verification

Workflow guidance was verified on 2026-09-07 against official Canvas
[Submissions](https://developerdocs.instructure.com/services/canvas/resources/submissions),
[Enrollments](https://developerdocs.instructure.com/services/canvas/resources/enrollments),
[Analytics](https://developerdocs.instructure.com/services/canvas/resources/analytics),
[Outcomes](https://developerdocs.instructure.com/services/canvas/resources/outcome_results),
[Discussions](https://developerdocs.instructure.com/services/canvas/resources/discussion_topics),
and [Files](https://developerdocs.instructure.com/services/canvas/resources/files).
[Canvas instructor reports](https://community.instructure.com/en/kb/articles/660639-how-do-i-view-and-download-reports-in-course-analytics)
and [KTH faculty use cases](https://intra.kth.se/en/utbildning/systemstod/data-informed-education/course-analytics/examples-1.1446629)
support the report categories; they are not a quantified ranking of faculty demand.
FastMCP Apps and document-library behavior were checked through Context7 and
installed primary source/type definitions. See [measured validation](REPORTING_VALIDATION.md).
