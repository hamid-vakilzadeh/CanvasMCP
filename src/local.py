"""Local Canvas MCP entry point. The MCP client owns this stdio process."""

import os
import sys

from canvas_credentials import configure_canvas_credentials
from private_diagnostics import configure_private_diagnostics


def main() -> None:
    configure_private_diagnostics()
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
