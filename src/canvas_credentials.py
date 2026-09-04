"""Validate and provide credentials for direct Canvas API requests."""

from urllib.parse import urlsplit

_credentials: tuple[str, str] | None = None


def configure_canvas_credentials(
    base_url: str | None, access_token: str | None
) -> None:
    """Validate and store credentials for the lifetime of this local process."""
    global _credentials
    base_url = (base_url or "").strip().rstrip("/")
    access_token = (access_token or "").strip()
    missing = []
    if not base_url:
        missing.append("CANVAS_URL")
    if not access_token:
        missing.append("CANVAS_ACCESS_TOKEN")
    if missing:
        raise ValueError(
            "Set " + " and ".join(missing) + " in the MCP server's env configuration."
        )

    try:
        parsed = urlsplit(base_url)
        valid_url = (
            parsed.scheme in {"http", "https"}
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
            and not any(char.isspace() for char in base_url)
        )
        # Accessing port also validates malformed port numbers.
        parsed.port
    except ValueError:
        valid_url = False
    if not valid_url:
        raise ValueError(
            "CANVAS_URL must be an http(s) Canvas URL without credentials, query, or fragment."
        )
    if parsed.path.rstrip("/").endswith("/api/v1"):
        base_url = base_url[: -len("/api/v1")]
    if any(char.isspace() for char in access_token):
        raise ValueError("CANVAS_ACCESS_TOKEN must not contain whitespace.")

    _credentials = (base_url, access_token)


def get_canvas_credentials() -> tuple[str, str]:
    """Return the configured ``(Canvas URL, Canvas access token)`` pair."""
    if _credentials is None:
        raise ValueError("Canvas credentials have not been configured.")
    return _credentials
