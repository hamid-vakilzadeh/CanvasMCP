# Canvas MCP

Canvas MCP gives an AI client direct access to Canvas LMS through one local
**stdio** process. The client starts the process and communicates over
stdin/stdout. Normal MCP startup has no HTTP listener. An optional student
dashboard can open a private loopback-only browser interface; the MCP transport
remains stdio. Canvas MCP does not send analytics or use Unkey or another
authentication service.

The process reads a Canvas URL and personal access token from the MCP client and
connects directly to Canvas. Canvas and its file-upload service still require
network access; "local" describes the MCP server and credential flow.

## What it can do

The server is designed for instructors and course authors. Common workflows are
available immediately:

- inspect courses, modules, pages, assignments, and quizzes;
- list students and review enrollment, progress, submissions, and activity;
- explore an interactive student dashboard and generate evidence-linked faculty
  learning reviews with the connected AI client;
- monitor selected discussions locally and save drafts for faculty review;
- find submissions awaiting review and inspect comments or rubric assessments;
- review and grade essay and file-upload questions in completed Classic Quiz attempts;
- review Canvas Inbox conversations and plan private student outreach;
- create and maintain pages, assignments, announcements, discussions, modules,
  module items, Classic Quizzes, New Quizzes, and assignment rubrics;
- upload local files and start complete or selective course copies; and
- post planned discussion entries or replies, and plan grades, submission
  comments, publishing changes, and deletions before
  applying them.

New Quizzes must be available at the institution. If Canvas rejects a New
Quizzes endpoint because it is unavailable or the token lacks permission, the
tool returns that Canvas capability or permission error.

### Compact tool catalog

The initial catalog declares 27 tools as model-visible and one bridge as app-only.
Hosts that do not honor MCP Apps visibility may show all 28. This keeps the schemas much smaller
than registering every Canvas endpoint at once.

The current serialized model-visible schemas measure 25,431 bytes (27 tools);
the full host catalog measures 26,838 bytes (28 tools). Discovery adds at most
five relevant schemas when needed. These are payload measurements, not model
token counts or evidence of a measured reasoning improvement. See
[reporting validation](REPORTING_VALIDATION.md) for measured workflow results.

| Area | Visible tools |
| --- | --- |
| Discovery | `canvas_capabilities`, `canvas_search_tools`, `canvas_call_tool` |
| Courses and students | `canvas_list_courses`, `canvas_get_course_structure`, `canvas_list_course_people`, `canvas_get_student_snapshot`, `canvas_analyze_student_engagement`, `canvas_list_grading_queue`, `canvas_get_submission_review`, `canvas_get_quiz_submission_review` |
| Reports | `canvas_open_student_dashboard`; discover report data, learning-review and discussion-watch tools as needed |
| Communication | `canvas_list_inbox`, `canvas_get_conversation`, `canvas_plan_communication`, `canvas_plan_announcement_change` |
| Authoring | `canvas_plan_page_change`, `canvas_plan_assignment_change`, `canvas_plan_discussion_change`, `canvas_plan_discussion_entry`, `canvas_plan_module_change`, `canvas_plan_quiz_change`, `canvas_plan_file_upload`, `canvas_plan_course_copy` |
| Grades and execution | `canvas_plan_grade_change`, `canvas_plan_quiz_submission_grade`, `canvas_apply_change` |

There is one server mode and no legacy profile. The broader Canvas API catalog is
available through FastMCP Tool Search:

1. Call `canvas_search_tools` with a natural-language request such as "manage
   assignment overrides" or "show quiz question groups."
2. Review the returned matches. Search returns at most five tools.
3. Call the discovered read action with `canvas_call_tool`. Direct low-level
   writes are excluded from discovery; use planning tools for every Canvas
   write. Report jobs and queue decisions update private local state.

The existing flexible argument converter remains available to discovered tools,
including clients that serialize list or object arguments as text.

The bundled `resource://content-creation-reference` resource contains Canvas-safe
HTML and CSS guidance for creating course content.

### Student reports and discussion monitoring

Ask the AI client to open the student dashboard for a course and student. The
server uses an embedded MCP App when the host advertises support; otherwise it
returns a private localhost browser link. A student selection reads Canvas
without invoking a model. The browser version is also available with
`canvas-mcp dashboard` using the same Canvas environment variables.

A comprehensive learning review is separate: the server collects evidence,
including supported documents, and the existing AI client reads bounded batches
and saves cited findings. The result is a printable, self-contained faculty HTML
report with explicit coverage gaps. There is no built-in model provider or key.

Discussion monitoring uses `canvas-mcp watch` in a separate local process.
Configure selected topics through the MCP tools. The first scan is a baseline;
later posts and edits enter a private queue. AI decisions and drafts wait for
faculty review, and sending still requires plan/apply.

See [setup, workflows, privacy and limitations](REPORTING.md) and the canonical
`canvas://reports/templates` resources. No skill or companion plugin is required.

### Plan before applying writes

#### Student groups and group sets

Discover **student project groups** with `canvas_search_tools`, then use the
returned tools through `canvas_call_tool`. Canvas calls a **group set** a
`group_category`; the MCP parameter `group_set_id` is that category ID. These
course project groups are separate from assignment groups used for grade weights.

| Tool | Purpose |
| --- | --- |
| `canvas_list_group_sets` | List group sets and their signup/leader settings. |
| `canvas_list_groups` | List groups in a course, optionally within `group_set_id`. |
| `canvas_get_group` | View group details, member names, or membership records and states. |
| `canvas_plan_group_set_change` | Create/rename a group set; edit signup, leader selection, and group size settings. |
| `canvas_plan_group_change` | Create a group within a set or edit its name and plain-text description. |
| `canvas_plan_group_membership_change` | Add, move, or remove explicitly selected students. |

All changes use `canvas_apply_change` after preview. Create a set first, reuse its
returned ID to create groups, then reuse each group's ID to plan memberships.
For example, these are separate synthetic planner argument objects:

```json
{"course_id":"42","operation":"create","changes":{"name":"Project teams"}}
```

```json
{"course_id":"42","operation":"create","group_set_id":"20","changes":{"name":"Team A","description":"Project collaboration"}}
```

```json
{"course_id":"42","group_id":"30","operation":"add","student_ids":["7","8"]}
```

Use `operation="update"` with `group_set_id` for a set, or `group_id` for a
group. Group-set changes accept `self_signup` (`"enabled"`, `"restricted"`, or
`null`), `auto_leader` (`"first"`, `"random"`, or `null`), and `group_limit`
(positive integer or `null`). Native `null` clears a setting. A group size limit
requires self-signup. When disabling signup, clear an existing group limit too.
Renaming a set preserves its existing settings, including a returned signup
deadline: Canvas's update implementation can reset omitted settings, so the
planner resends those values. Changing signup away from `enabled` clears its
deadline, shown in the preview's `settings_sent`.

Read lists return `next_cursor`; follow it for a complete list. `canvas_get_group`
defaults to `view="members"` (paginated user names); `view="memberships"` returns
membership IDs and states, and `view="details"` avoids roster retrieval.
The membership planner reads all pages before planning and never replaces the
entire roster via `members[]`. It skips students already in the requested state.
Moving between groups in the same set requires `allow_moves=true`; the preview
names the groups each student will leave. Membership changes can affect access
to group work and group-assignment grading, and Canvas may notify students.
The apply result distinguishes successful, failed, and uncertain writes; an
invitation/request is not reported as confirmed membership. Inspect uncertain
results before retrying, especially after creating a group or group set.

This workflow covers collaborative course project groups. Account/community
groups, differentiation tags, deleting groups/sets, and automatic/random student
allocation are outside this tool set. Group names, memberships, and configuration
changes invalidate captured plans before any write. Tests use synthetic records;
no live memberships were changed during development.

Verified 2026-09-17 against the official
[Groups and memberships API](https://developerdocs.instructure.com/services/canvas/resources/groups),
[Group Categories API](https://developerdocs.instructure.com/services/canvas/resources/group_categories),
[membership model](https://github.com/instructure/canvas-lms/blob/master/app/models/group_membership.rb),
and [group-set update policy](https://github.com/instructure/canvas-lms/blob/master/app/models/group_categories/params_policy.rb).

#### Saving grades and releasing them to students

`canvas_plan_grade_change` compares the submission again before applying a grade.
Its comparison excludes only the calculated `seconds_late` counter, recursively
including `submission_history`; elapsed time alone no longer invalidates a plan.
Scores, attempts, submission content, comments, rubric assessments, late-policy
deductions and posting state still invalidate a plan when they change. Other
Canvas record comparisons remain exact. Classic Quiz grading uses the same
counter normalization for its included assignment submission.

Canvas's `posted_grade` parameter saves a grade; it does **not** promise that a
student can see it. Grade application now reads the submission back and returns
`grade_readback`, separating the accepted write from its score and visibility.
`canvas_get_submission_review` also includes `grade_posting`. These use the
submission's `posted_at` and `assignment_visible` fields, not the deprecated
assignment `muted` flag. Missing evidence is reported as unknown. A failed
readback does not trigger a second write or turn an accepted write into a failure.
Comment-only writes store feedback immediately, but hidden grades can also hide
that feedback until release.

For hidden grades, discover **post release hidden grades student visibility**:

1. Use `canvas_get_grade_posting_status` with `course_id`, `assignment_id` and
   explicit `student_ids` to inspect saved grades and visibility.
2. Use `canvas_plan_grade_release` with those same identifiers. For example,
   `{"course_id":"7","assignment_id":"9","student_ids":["11","12"]}`
   targets two synthetic students. Already-visible grades are skipped. Save grades
   first; ungraded, unavailable, or indeterminate submissions cannot be released
   by this planner. Anonymous assignments must be released through Canvas Gradebook.
3. Review the preview and apply its token with `canvas_apply_change`. This calls
   Canvas's GraphQL `postAssignmentGrades` with `onlyStudentIds` and
   `gradedOnly=true`. It does not change the posting policy or release other
   students' grades. Released feedback may generate student notifications.
4. An `accepted` result means Canvas queued the release. Call
   `canvas_get_grade_posting_status` again with the returned `progress_id` and
   target identifiers. Report completion only when progress completes **and**
   the per-student readback confirms visibility. Inspect failures or uncertain
   results before retrying; the plan token is single use.

This checks Canvas API visibility, not whether students opened their grades.
Permissions and institutional Canvas versions can restrict release; GraphQL
errors, including those returned with HTTP 200, are reported explicitly.
Moderated grading must be finalized in Canvas before release. No live student
grade or release was used in verification; regression examples are synthetic.

Verified 2026-09-16 against the official
[Submissions API](https://developerdocs.instructure.com/services/canvas/resources/submissions),
[Assignments API](https://developerdocs.instructure.com/services/canvas/resources/assignments),
[GraphQL API](https://developerdocs.instructure.com/services/canvas/basics/file.graphql),
[grade-release mutation](https://github.com/instructure/canvas-lms/blob/master/app/graphql/mutations/post_assignment_grades.rb),
and [Progress API](https://developerdocs.instructure.com/services/canvas/resources/progress).

#### Student quiz time accommodations

Search for **quiz extra time 1.5x accommodations**, then call the discoverable
`canvas_plan_quiz_accommodations` through `canvas_call_tool`. Resolve the student's
Canvas ID from the course roster first. For example, this synthetic request plans
time-and-a-half for every current timed Classic Quiz, including unpublished ones:

```json
{
  "name": "canvas_plan_quiz_accommodations",
  "arguments": {
    "course_id": "42",
    "student_ids": ["7"],
    "engine": "classic",
    "scope": "all_timed",
    "time_multiplier": 1.5
  }
}
```

Use `scope="selected"` with `quiz_ids` for specific quizzes. Provide exactly one
of `time_multiplier` or `extra_time_minutes` (0–10080). A multiplier is converted
to extra whole minutes per quiz, rounded up: a 45-minute quiz at 1.5× receives
23 extra minutes, for 68 minutes total. The preview shows existing Classic Quiz
allowances and the resulting limits. Extra minutes replace the prior allowance;
zero removes it. Attempts, grades, publication state and availability dates are
not changed. Classic attempts already underway need separate end-time moderation.

For New Quizzes use `engine="new"` and **assignment IDs**, not Classic Quiz IDs.
Selected/all-timed scope supports per-quiz minutes or a calculated multiplier;
`scope="course"` supports fixed `extra_time_minutes` only. The optional
`apply_to_in_progress_quiz_sessions=true` is available only for New Quizzes course
scope. The documented API has no course-wide multiplier field and exposes no
current accommodation read in this tool; existing New Quizzes settings therefore
appear as unavailable, not zero.

Review the preview, then use `canvas_apply_change` with its token and
`confirm=true`. Classic quiz/settings changes and changed all-timed inventories
invalidate stale plans. New Quizzes HTTP 200 responses can still contain individual
failures; the apply result reports applied, failed and uncertain student changes.
Inspect uncertain results in Canvas before preparing another plan.

`all_timed` covers the quizzes found when planning; quizzes created later need a
new run. An availability/Until date can still cut off extra time, and preview dates
are defaults rather than resolved student/group/section overrides. Course scope
is the separate New Quizzes accommodation endpoint, not an ongoing Classic Quiz
automation.

Verified 2026-09-16 against the official
[Classic Quiz Extensions API](https://developerdocs.instructure.com/services/canvas/resources/quiz_extensions),
[New Quizzes Accommodations API](https://developerdocs.instructure.com/services/canvas/resources/new_quizzes_accommodations),
and [Canvas's Classic extension implementation](https://github.com/instructure/canvas-lms/blob/master/app/models/quizzes/quiz_extension.rb).
The New Quizzes resource's route definitions specify `/api/quiz/v1`; its curl
examples currently omit `/quiz`. The implementation follows the route definitions
and sends the documented top-level JSON array. Synthetic tests exercise both
engines, actual HTTP JSON encoding, pagination, stale plans, and partial/uncertain
results. No live student write was used to validate this feature. Restart the local
MCP connection after updating to load the new tool.

#### General write behavior

Every curated mutation uses two steps. A `canvas_plan_*` tool returns a preview
and a random plan token without changing Canvas. After reviewing the preview,
call `canvas_apply_change` with that token and `confirm=true`.

Plans are stored only in memory, expire after ten minutes, and can be used once.
Updates and deletions that captured existing Canvas state are rejected if that
state changes before the plan is applied. Batch operations report each success
and failure because Canvas cannot make them atomic. Private outreach creates a
separate conversation for each recipient so students are not exposed to one
another.

Grade plans support student IDs or Canvas anonymous-grading identifiers, rubric
criterion assessments, saved grades, excuses, and submission comments.
Comments are posted immediately when a plan is applied and Canvas may notify the
student, subject to Canvas posting and visibility settings. An unapplied plan is
a temporary local preview, not a Canvas draft comment. Canvas's
[SpeedGrader interface supports draft comments](https://community.instructure.com/en/kb/articles/664292),
but this MCP does not expose that workflow or moderated/provisional grading.

`canvas_get_quiz_submission_review` returns only essay and file-upload questions
from the version of the Classic Quiz presented for the attempt. These are the
question types that require manual grading. Auto-graded and unknown question types
are excluded, and the grading planner rejects updates to them. Canvas may omit
student answers or current per-question scores even when the instructor can see
the prompts; the tool reports those fields as unavailable. `canvas_plan_quiz_submission_grade`
can prepare question scores, question comments, or a total-score adjustment.
Canvas persists those edits after `canvas_apply_change`; the Classic Quiz scoring
endpoint used here has no documented draft parameter. Canvas's separate
[moderated grading API](https://developerdocs.instructure.com/services/canvas/resources/moderated_grading)
is not exposed by this MCP.

Discussion entries and entry-specific replies use the same plan/apply boundary.
The preview includes the topic and, for a reply, the parent entry. Applying a
plan publishes the message immediately and may notify participants.

These workflows follow the official Canvas API contracts for
[discussion entries and replies](https://developerdocs.instructure.com/services/canvas/resources/discussion_topics),
[assignment submissions and comments](https://developerdocs.instructure.com/services/canvas/resources/submissions),
[Classic Quiz submissions](https://developerdocs.instructure.com/services/canvas/resources/quiz_submissions),
and [quiz submission questions](https://developerdocs.instructure.com/services/canvas/resources/quiz_submission_questions).

Upload plans include a SHA-256 fingerprint and are rejected if the local file
changes after review.

Use `canvas_plan_advanced_action` with `create_rubric` to create an analytic
rubric and associate it with an assignment. The plan validates criteria and
ratings, compares the rubric total with the assignment points, and rejects the
write if the assignment changes before application.

Course copies may include selected source IDs in the initial plan. A staged
selective copy stops at Canvas's `waiting_for_select` state; discover
`canvas_get_course_copy_selection`, then use `canvas_plan_advanced_action` with
`apply_course_copy_selection` to preview and submit the chosen property keys.

### Local background work

Canvas MCP uses FastMCP 4's Tasks extension for longer operations. Engagement
analysis, grading-queue collection, and applying a change can run as background
tasks when the client supports MCP tasks; clients without task support execute
the same tools synchronously.

The task queue uses FastMCP's in-process memory backend and an embedded worker.
There is no Redis server, external worker, database, or cloud queue. Task handles,
progress, and results disappear when the MCP process exits. Canvas content
migrations can continue inside Canvas after the local task has submitted them.

### Privacy and diagnostics

The local entry point discards Python log messages, arguments, exception details,
and source paths before they reach a logging handler. Python logging diagnostics
contain only severity and a fixed component label, plus static startup and
configuration messages. FastMCP telemetry is disabled even if inherited
environment settings enable it. The server does not create log files or persist
Canvas responses, plans, or background-task results.
Progress messages use generic descriptions without student IDs or mutation labels.

Tool results and actionable tool errors include Canvas data for the user. The
AI client receives those results and may retain them in conversation history,
diagnostic logs, or provider storage. Running the MCP server locally does not
make the AI client or model local, and these server settings do not control the
client's retention. Treat client transcripts and saved API responses as private.

Use synthetic data in tests, bug reports, and screenshots. Keep credentials in
the MCP client's environment configuration. Environment files, logs, JSONL
transcripts, and the local `temp/` directory are excluded from Git; these ignore
rules do not remove files already committed. Inspect staged changes and package
contents before publishing.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) on the MCP
  client's `PATH`. `uv` manages the Python environment and can download the
  required Python version.
- A Canvas instance URL and personal Canvas API access token.
- Node.js 20 or later when using the npm/npx launcher.

The npm package includes the Python source and lockfile, so npm/npx installations
also require `uv`. The first launch can download Python and locked dependencies;
later launches reuse a user-owned cached environment.

## Install from a Git clone

```sh
git clone https://github.com/hamid-vakilzadeh/CanvasMCP.git
cd CanvasMCP
uv sync --frozen --no-dev
```

Use the absolute checkout path when configuring the MCP client.

## Configure Codex Desktop

Codex Desktop, the Codex CLI, and the IDE extension share MCP configuration. In
Codex Desktop, open **Settings > MCP servers**, add a **STDIO** server, enter the
command and environment values shown below, save, and restart. You can also edit
`~/.codex/config.toml` directly. See the
[official Codex MCP setup guide](https://developers.openai.com/codex/mcp).

For a Git clone:

```toml
[mcp_servers.canvas]
command = "uv"
args = [
  "--directory", "/absolute/path/to/CanvasMCP",
  "run", "--frozen", "--no-dev", "python", "src/local.py",
]
startup_timeout_sec = 30
tool_timeout_sec = 300

[mcp_servers.canvas.env]
CANVAS_URL = "https://your-school.instructure.com"
CANVAS_ACCESS_TOKEN = "your_canvas_api_token"
```

If Codex Desktop cannot find `uv`, replace `command = "uv"` with the absolute
path returned by `command -v uv` (`where uv` on Windows). Restart Codex after
changing the configuration, then use `/mcp` to confirm that `canvas` is connected.

The same server can be added from a terminal:

```sh
codex mcp add canvas \
  --env CANVAS_URL=https://your-school.instructure.com \
  --env CANVAS_ACCESS_TOKEN=your_canvas_api_token \
  -- uv --directory /absolute/path/to/CanvasMCP \
  run --frozen --no-dev python src/local.py
```

## Install with npm or npx

Install the launcher globally from a checkout:

```sh
npm install -g .
```

Then configure Codex with `command = "canvas-mcp"`, no arguments, and the same
two environment values:

```toml
[mcp_servers.canvas]
command = "canvas-mcp"
startup_timeout_sec = 30
tool_timeout_sec = 300

[mcp_servers.canvas.env]
CANVAS_URL = "https://your-school.instructure.com"
CANVAS_ACCESS_TOKEN = "your_canvas_api_token"
```

To test an installable npx package before publishing it, create a tarball:

```sh
npm pack
```

Then point Codex at that tarball:

```toml
[mcp_servers.canvas]
command = "npx"
args = [
  "--yes", "--package",
  "/absolute/path/to/hamid-vakilzadeh-canvas-mcp-0.2.0.tgz",
  "canvas-mcp",
]
startup_timeout_sec = 60
tool_timeout_sec = 300

[mcp_servers.canvas.env]
CANVAS_URL = "https://your-school.instructure.com"
CANVAS_ACCESS_TOKEN = "your_canvas_api_token"
```

Once `@hamid-vakilzadeh/canvas-mcp` is published to npm, the tarball path can be
replaced with the registry package name. Use `canvas-mcp.cmd` on Windows if the
MCP client requires the executable extension.

## Configure another MCP client

For clients that use `mcpServers` JSON, a Git-clone configuration looks like:

```json
{
  "mcpServers": {
    "canvas": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/CanvasMCP",
        "run", "--frozen", "--no-dev", "python", "src/local.py"
      ],
      "env": {
        "CANVAS_URL": "https://your-school.instructure.com",
        "CANVAS_ACCESS_TOKEN": "your_canvas_api_token"
      }
    }
  }
}
```

## Configuration and privacy

- `CANVAS_URL` and `CANVAS_ACCESS_TOKEN` are the only required server settings.
  `CANVAS_URL` may be the institution root or end in `/api/v1`.
- Put credentials in the MCP server's environment configuration. Canvas MCP does
  not read a dotenv file or accept credentials as tool arguments.
- Credentials remain in the local process and are sent only to Canvas and, for
  file uploads, the upload URL issued by Canvas. Diagnostics redact the token.
- The token determines which courses, students, content, and actions Canvas
  permits. Use a token for the faculty member who is running the MCP server.
- Active students are the default for roster and engagement workflows. Engagement
  results report explicit matched criteria and do not predict student risk.
- stdout is reserved for MCP JSON-RPC; diagnostics go to stderr. The process stops
  when the MCP client closes it.

## Development and verification

```sh
uv run --frozen --no-dev python -m unittest discover -s tests -v
npm test
npm pack --dry-run
```

The Python tests launch the real stdio server against a fake Canvas API, inspect
the 26-tool catalog, and exercise discovery, planning, background-task compatible
tools, resources, and credential isolation. Node tests cover launcher argument
and stdio forwarding, missing `uv`, exit status, and termination. Tests do not
require a real Canvas account or token.

The implementation follows the official
[Canvas API documentation](https://developerdocs.instructure.com/services/canvas),
[FastMCP Tool Search documentation](https://gofastmcp.com/servers/transforms/tool-search),
and [FastMCP Tasks documentation](https://gofastmcp.com/servers/tasks).
