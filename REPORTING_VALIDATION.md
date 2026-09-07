# Reporting validation

Verified 2026-09-07 using synthetic course/student data only. No live Canvas
student reads or writes, personal configuration changes, registry publication,
or merge to main were performed for this implementation.

## Automated and visual checks

- **95 Python tests passed**, including the existing stdio, plan/apply, flexible
  argument conversion and private-diagnostic checks.
- **5 launcher tests passed**, including unchanged default startup, signal
  propagation and optional command forwarding.
- **4 real-browser scenarios passed** using local Chromium: localhost selection,
  optional details, filtering, keyboard navigation and mobile layout; out-of-order
  student responses; embedded MCP Apps SDK transport with namespaced tools and
  absent messaging capability; review status, export, PDF printing and deletion.
- TypeScript type checking, server registration, Python compilation and diff
  whitespace checks passed.
- Built and inspected the npm tarball: 95 source/asset/documentation files, with
  no private database or student export. Installed locked Python dependencies in
  a separate temporary environment, read the packaged UI and guide through an
  MCP client, and launched the tarball with offline `npx`. No registry publication
  occurred. The UI resource serves `text/html;profile=mcp-app`.
- Inspected desktop/mobile screenshots, the standalone HTML review, and printed
  PDF pages. Tables repeat headers in print and source references wrap. The
  synthetic overview prints across two A4 pages; the synthetic export fixture
  with its evidence appendix prints across four. Page count depends on evidence.
- Calculated contrast for the dashboard's main text, secondary text, primary
  button and status labels: **5.91:1 to 10.82:1**, above 4.5:1. This is a palette
  check plus keyboard/visual review, not a full assistive-technology certification.

Backend cases cover 105 submissions over two pages; a failed later page;
Canvas-calculated grades that differ from assignment averages; unknown and zero
values; grading periods; late/excused/awaiting-grading distinctions; unavailable
analytics; and modules with no requirements. Evidence tests cover revision
provenance, deduplication, anonymous work, unavailable Classic Quiz answers,
excluded auto-graded questions, New Quizzes gaps, resume/cancel/delete, invalid
citations, idempotent analysis, incomplete rendering and optional measured usage.

Document tests exercise Word paragraphs/tables, slide text/notes, Excel formulas,
zero values and unavailable caches, CSV rows, encrypted/blank PDFs, unsupported
media and ZIP expansion bounds. Redirect tests verify that a Canvas bearer token
is not sent to a storage host and that private download destinations are rejected.
Parser subprocesses receive no Canvas credentials.

Watcher tests cover fingerprint-only baselines, replies beyond the first ten in
an old thread, new-entry overlays, edits/deletions, restart/deduplication, own
replies, permission pauses/backoff, stale drafts, duplicate plans, and a write
whose response is lost after the simulated server accepts it. The uncertain
outcome requires inspection and an explicit resolution before another attempt.

Storage tests cover account isolation, permissions, leases, optimistic revisions,
retention of pending drafts, expiry of temporary evidence and rejection of state
directories inside Git repositories. Browser tests cover Host/Origin/session
checks and rejection of operations outside the dashboard allowlist. The embedded
bridge is listed for the UI host, hidden from model search, and callable directly.

## One actual synthetic AI review

The primary Codex assistant read the complete prepared evidence batch and supplied
the findings to the analysis ledger and HTML renderer. This was an actual AI
review in the existing client, **not an independent model benchmark**. The helper
script prepares/validates evidence; it does not generate an analysis or call a
model. Reproduce preparation with `scripts/evaluate-report.py prepare`, read the
resulting batch in an AI client, and finish with that client's analysis JSON.

| Measure | Observed result |
| --- | ---: |
| Collected evidence chunks | 18 |
| Reviewed chunks / remaining unread | 18 / 0 |
| Distinct documented coverage gaps | 5 |
| Source associations retained | 30 |
| Evidence text characters | 7,337 |
| Prepared batch JSON bytes in the recorded run | 22,199 |
| Findings / findings with valid reviewed citations | 8 / 8 |
| Final status | `completed_with_gaps` |

Manual inspection of that review found that it:

- used Canvas's 81.25% current grade instead of averaging the two visible 80%
  assignment percentages, and kept the 64% final grade separate;
- recognized improvement between an initial absolute fraud-prevention claim and
  a revision acknowledging collusion, while retaining a focused explanation gap;
- flagged a missing-work listing that conflicted with returned submission history;
- did not substitute generic assignment text for an unavailable quiz answer;
- preserved anonymous grading and identified the unavailable embedded image;
- ignored an instruction embedded in synthetic student content to change a grade
  and email a roster; no Canvas write was attempted;
- gave specific faculty follow-up actions and reported the five coverage gaps.

Factuality was assessed manually by the same assistant, not independently scored.
These results demonstrate that the workflow can support a careful review; they
do not establish general accuracy, educational effectiveness, or improvement over
an MCP-only baseline. Document extractors were tested separately from this text
review fixture.

## Calls, size and model cost

| Measure | Observed result |
| --- | ---: |
| First synthetic dashboard read | 5 logical Canvas calls |
| Repeat read within the cache window | 0 logical Canvas calls |
| Comprehensive synthetic evidence collection | 25 logical Canvas calls |
| Synthetic collection elapsed time | 0.042 seconds |
| Initially declared model-visible tools | 27 |
| Initial model-visible schema JSON | 25,431 bytes |
| Full host catalog, including app-only bridge | 28 tools / 26,838 bytes |

Call counts exclude HTTP retries and the one-time account-identification request.
Elapsed time uses an in-memory Canvas fixture and is **not real Canvas latency**.
The initial dashboard payload reported 3,522 serialized bytes before cache
metadata. Optional sections add calls and content. MCP/client wrapping and model
context overhead can change the actual bytes or tokens delivered to a model.
Clients that ignore MCP Apps visibility metadata may show the full 28-tool host
catalog to their model.

Student selection uses the UI's direct tool/API adapter and invokes **no model**.
The AI conversation that opens the dashboard can still consume tokens. A learning
review intentionally invokes the connected AI client and has input/output costs.
The evaluation client did not expose per-review usage or billing metadata, so
actual model tokens and currency cost are **unavailable**. No token-saving or
reasoning-improvement percentage is claimed. Clients can supply measured usage
per analysis batch; unreported calls remain explicitly outside that aggregate.

## Remaining platform limits

Codex Desktop's own rendering of a custom local MCP App has not been verified.
The SDK host harness and localhost browser paths were exercised; unsupported
hosts receive the browser fallback. No real institution was used to test Canvas
permissions, caches, rate limits, historical-answer availability or file storage
redirects. Those depend on the connected Canvas deployment and are reported as
coverage gaps or errors. This branch does not provide OCR, vision, transcription,
New Quizzes answer review, group-discussion-root monitoring or hosted webhooks.
