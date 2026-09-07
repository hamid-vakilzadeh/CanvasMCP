"""Local Canvas MCP entry point. The MCP client owns this stdio process."""

import os
import sys
import argparse
import asyncio

from canvas_credentials import configure_canvas_credentials
from private_diagnostics import configure_private_diagnostics


def main() -> None:
    configure_private_diagnostics()
    parser = argparse.ArgumentParser(description='Local Canvas MCP and optional faculty workflows')
    parser.add_argument('command', nargs='?', choices=['watch', 'dashboard'], help='Omit for the stdio MCP server')
    parser.add_argument('--once', action='store_true', help='Poll discussion watches once, then exit')
    parser.add_argument('--no-open', action='store_true', help='Print a dashboard link instead of opening the browser')
    args = parser.parse_args()
    try:
        configure_canvas_credentials(
            os.getenv("CANVAS_URL"), os.getenv("CANVAS_ACCESS_TOKEN")
        )
    except ValueError as exc:
        print(f"Canvas MCP configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    # Override inherited diagnostic/telemetry settings before importing FastMCP.
    os.environ["FASTMCP_LOG_ENABLED"] = "false"
    os.environ["FASTMCP_TELEMETRY_MODE"] = "off"
    try:
        if args.command:
            async def optional_workflow():
                from reporting.runtime import runtime
                try:
                    if args.command == 'watch':
                        from discussion_watch import run_watcher
                        await run_watcher(runtime, once=args.once)
                    else:
                        import webbrowser
                        from reporting.web import start_dashboard, close_dashboards
                        result = await start_dashboard(runtime)
                        if args.no_open:
                            # This is an explicit user-facing launch link, never a diagnostic log.
                            print(result['url'], flush=True)
                        else:
                            webbrowser.open(result['url'])
                        try:
                            await asyncio.Event().wait()
                        finally:
                            await close_dashboards()
                finally:
                    await runtime.close()
            asyncio.run(optional_workflow())
            return
        import fastmcp
        from server import create_server

        fastmcp.settings.telemetry_mode = "off"
        configure_private_diagnostics()
        create_server().run(transport="stdio", show_banner=False)
    except KeyboardInterrupt:
        pass
    except Exception:
        # Unhandled startup/shutdown exceptions can contain request data or
        # local paths. Do not let Python print the exception and its traceback.
        print(
            "Canvas MCP stopped because of an internal error. "
            "Check the installation and configuration.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
