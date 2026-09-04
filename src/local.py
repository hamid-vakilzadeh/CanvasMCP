"""Local Canvas MCP entry point. The MCP client owns this stdio process."""

import os
import sys

from canvas_credentials import configure_canvas_credentials


def main() -> None:
    try:
        configure_canvas_credentials(
            os.getenv("CANVAS_URL"), os.getenv("CANVAS_ACCESS_TOKEN")
        )
    except ValueError as exc:
        print(f"Canvas MCP configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    # Import only after local credentials have been validated.
    from fastmcp.utilities.logging import configure_logging
    from server import create_server

    configure_logging(level="WARNING", enable_rich_tracebacks=False)
    try:
        create_server().run(transport="stdio", show_banner=False)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
