"""Small, dependency-free validation and display helpers."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sid(value: str | int) -> str:
    result = str(value)
    if not result or result in {".", ".."} or any(c in result for c in "/?#\\") or "%" in result:
        raise ValueError("Canvas IDs must be a single unencoded path segment")
    return result


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def safe_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        p = urlsplit(value)
        return value if p.scheme in {"http", "https"} and p.hostname and not p.username and not p.password else None
    except ValueError:
        return None


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(value: Any) -> str:
    parser = _Text()
    parser.feed(str(value or ""))
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())
