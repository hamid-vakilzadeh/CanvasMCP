# Canvas MCP

Connect your AI assistant to Canvas LMS for course authoring, grading, communication,
and student review. Canvas MCP runs locally over **stdio**, using your Canvas API
token. There is no hosted MCP endpoint or third-party authentication service.
It connects directly to Canvas, so internet access is still required.

## What you can do

- Create and manage course content, assignments, rubrics, modules, and quizzes.
- Review submissions, grade written quiz answers, and provide feedback.
- Read uploaded documents, spreadsheets, images, and files inside ZIP attachments.
- Work with discussions, Inbox messages, student groups, and quiz accommodations.
- Explore student dashboards, prepare learning reviews, and monitor discussions.

Student-record features require `FERPA=true`. Available actions also depend on
your Canvas permissions and the features enabled by your institution.

The assistant starts with a compact tool set and discovers additional tools when
needed. Changes use a **preview, then apply** workflow so you can review what will
happen before Canvas is updated.

## Install

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), your Canvas
URL, and a personal Canvas API access token. `uv` manages Python and dependencies.

```sh
git clone https://github.com/hamid-vakilzadeh/CanvasMCP.git
cd CanvasMCP
uv sync --frozen --no-dev
```

Use `git switch dev` before syncing if you want the development version.

## Connect your AI client

Add a local **stdio** MCP server. For Codex, put this in `~/.codex/config.toml`,
replacing the path and credentials:

```toml
[mcp_servers.canvas]
command = "uv"
args = [
  "--directory", "/absolute/path/to/CanvasMCP",
  "run", "--frozen", "--no-dev", "python", "src/local.py",
]
startup_timeout_sec = 60
tool_timeout_sec = 300

[mcp_servers.canvas.env]
CANVAS_URL = "https://your-school.instructure.com"
CANVAS_ACCESS_TOKEN = "your_canvas_api_token"
FERPA = "false"
```

Other MCP clients use the same command, arguments, and environment values in their
own configuration format. If the client cannot find `uv`, use its absolute path.
Restart the connection after updating the installation or configuration.
See the [official Codex MCP guide](https://developers.openai.com/codex/mcp) for
client-specific setup.

### npm / npx option

With Node.js 20 or later, you can install the launcher from your checkout:

```sh
npm install -g .
```

Use `command = "canvas-mcp"` and `args = []` in place of the `uv` command above,
keeping the same environment values. The launcher still requires `uv`.

To build a local package for `npx`:

```sh
npm ci
npm pack
```

Use `command = "npx"` and
`args = ["--yes", "--package", "/absolute/path/to/package.tgz", "canvas-mcp"]`,
replacing the path with the tarball produced by `npm pack`.

## Student access and privacy

| Setting | Access |
| --- | --- |
| `FERPA=false` or unset | Course structure and content authoring. Student-record workflows are hidden and blocked. |
| `FERPA=true` | Also enables student records, grading, attachment reading, communication, reports, and monitoring. |

This setting applies to tool search and execution. Restart the MCP connection
when changing it. It controls feature access; it is not a certification of legal
compliance and does not change Canvas permissions.

Keep credentials in your client's environment configuration, never in the
repository. Attachment parsing uses temporary local files; optional reports and
monitoring can save data locally. The AI client receives tool results and may
retain them, so a local MCP server does **not** mean a local AI model or local-only
conversation storage. Use synthetic data in public examples and bug reports.

## Using Canvas MCP

Ask for the task you want: “Create a weekly module,” “Review submissions waiting
for feedback,” or “Show a student's progress.” The assistant can discover the
relevant tools and their current argument requirements.

For ZIP attachments, the reader lists the files first, then reads selected members.
Supported images are returned as image content; documents and spreadsheets return
text with source locations. Unreadable files and extraction limits are reported
explicitly. Password-protected and nested ZIP archives are not supported.
Readers also recognize Canvas files embedded or linked in submitted quiz essays.
Use `download_original=true` to save an attachment privately for local inspection,
including formats the reader cannot parse. Downloads retain the 25 MiB size limit.

See [Reports and dashboards](REPORTING.md) for the optional reporting workflow.
Tool schemas and built-in resources provide the detailed operational guidance.

## Development

```sh
uv run --frozen --no-dev python -m unittest discover -s tests -v
npm test
```

Tests use synthetic data and do not require a live Canvas account.
The integration follows the [Canvas API documentation](https://developerdocs.instructure.com/services/canvas)
and uses [FastMCP](https://gofastmcp.com/).
