# Canvas MCP

Canvas MCP gives an AI client direct access to Canvas LMS through one local
**stdio** process. The client starts the process and communicates over
stdin/stdout. Canvas MCP does not start an HTTP listener, send analytics, or use
Unkey or another authentication service.

The process reads a Canvas URL and personal access token from the MCP client and
connects directly to Canvas. Canvas and its file-upload service still require
network access; "local" describes the MCP server and credential flow.

## What it can do

The server is designed for instructors and course authors. Common workflows are
available immediately:

- inspect courses, modules, pages, assignments, and quizzes;
- list students and review enrollment, progress, submissions, and activity;
- find submissions awaiting review and inspect comments or rubric assessments;
- review Canvas Inbox conversations and plan private student outreach;
- create and maintain pages, assignments, announcements, discussions, modules,
  module items, Classic Quizzes, and New Quizzes;
- upload local files and start complete or selective course copies; and
- plan grades, submission comments, publishing changes, and deletions before
  applying them.

New Quizzes must be available at the institution. If Canvas rejects a New
Quizzes endpoint because it is unavailable or the token lacks permission, the
tool returns that Canvas capability or permission error.

### Compact tool catalog

Only 23 tools are visible initially. This keeps the tool schemas much smaller
than registering every Canvas endpoint at once.

In a serialized `tools/list` measurement, the visible schemas are about 20.7 KB,
down from 161.3 KB for the previous 118-tool catalog. That is an 87% reduction;
discovery adds at most five relevant schemas only when they are needed.

| Area | Visible tools |
| --- | --- |
| Discovery | `canvas_capabilities`, `canvas_search_tools`, `canvas_call_tool` |
| Courses and students | `canvas_list_courses`, `canvas_get_course_structure`, `canvas_list_course_people`, `canvas_get_student_snapshot`, `canvas_analyze_student_engagement`, `canvas_list_grading_queue`, `canvas_get_submission_review` |
| Communication | `canvas_list_inbox`, `canvas_get_conversation`, `canvas_plan_communication`, `canvas_plan_announcement_change` |
| Authoring | `canvas_plan_page_change`, `canvas_plan_assignment_change`, `canvas_plan_discussion_change`, `canvas_plan_module_change`, `canvas_plan_quiz_change`, `canvas_plan_file_upload`, `canvas_plan_course_copy` |
| Grades and execution | `canvas_plan_grade_change`, `canvas_apply_change` |

There is one server mode and no legacy profile. The broader Canvas API catalog is
available through FastMCP Tool Search:

1. Call `canvas_search_tools` with a natural-language request such as "manage
   assignment overrides" or "show quiz question groups."
2. Review the returned matches. Search returns at most five tools.
3. Call the discovered read action with `canvas_call_tool`. Direct low-level
   writes are excluded from discovery; use the visible planning tools for every
   write.

The existing flexible argument converter remains available to discovered tools,
including clients that serialize list or object arguments as text.

The bundled `resource://content-creation-reference` resource contains Canvas-safe
HTML and CSS guidance for creating course content.

### Plan before applying writes

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
criterion assessments, posted grades, excuses, and private comments. Upload
plans include a SHA-256 fingerprint and are rejected if the local file changes
after review.

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
the 23-tool catalog, and exercise discovery, planning, background-task compatible
tools, resources, and credential isolation. Node tests cover launcher argument
and stdio forwarding, missing `uv`, exit status, and termination. Tests do not
require a real Canvas account or token.

The implementation follows the official
[Canvas API documentation](https://developerdocs.instructure.com/services/canvas),
[FastMCP Tool Search documentation](https://gofastmcp.com/servers/transforms/tool-search),
and [FastMCP Tasks documentation](https://gofastmcp.com/servers/tasks).
