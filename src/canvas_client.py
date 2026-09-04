"""Async, bounded Canvas API client used by the assistant-facing tools."""

from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx2

from canvas_credentials import get_canvas_credentials


@dataclass(slots=True)
class CanvasAPIError(RuntimeError):
    status: int
    code: str
    endpoint: str
    detail: str

    def __str__(self) -> str:
        return f"{self.code}: {self.detail} ({self.endpoint})"


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port or (443 if scheme == "https" else 80 if scheme == "http" else None)
    return scheme, (parsed.hostname or "").lower(), port


def encode_cursor(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> str:
    try:
        padding = "=" * (-len(cursor) % 4)
        decoded = base64.b64decode(
            (cursor + padding).encode(), altchars=b"-_", validate=True
        ).decode()
        parsed = urlparse(decoded)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError
        return decoded
    except Exception as exc:
        raise ValueError("Invalid pagination cursor") from exc


class AsyncCanvasClient:
    """Small Canvas REST client with safe pagination and bounded retries."""

    RETRYABLE = {429, 502, 503, 504}

    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self._origin = _origin(self.base_url)
        self._client = httpx2.AsyncClient(
            timeout=httpx2.Timeout(30.0, connect=5.0),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json+canvas-string-ids",
                "User-Agent": "canvas-mcp-local/0.2",
            },
            follow_redirects=False,
        )

    @classmethod
    def from_environment(cls) -> "AsyncCanvasClient":
        return cls(*get_canvas_credentials())

    async def __aenter__(self) -> "AsyncCanvasClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    def _url(self, endpoint: str) -> str:
        if endpoint.startswith(("http://", "https://")):
            if _origin(endpoint) != self._origin:
                raise ValueError("Canvas pagination URL changed origin")
            return endpoint
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        return urljoin(self.base_url + "/", endpoint.lstrip("/"))

    @staticmethod
    def _error(response: httpx2.Response) -> CanvasAPIError:
        endpoint = urlparse(str(response.url)).path or "unknown endpoint"
        status = response.status_code
        code = {
            400: "canvas_bad_request",
            401: "canvas_authentication_failed",
            403: "canvas_permission_denied",
            404: "canvas_not_found",
            409: "canvas_conflict",
            429: "canvas_rate_limited",
        }.get(status, "canvas_request_failed")
        detail = response.reason_phrase or "Canvas API request failed"
        try:
            body = response.json()
            if isinstance(body, dict):
                errors = body.get("errors") or body.get("message") or body.get("error")
                if isinstance(errors, str):
                    detail = errors
                elif errors:
                    detail = json.dumps(errors, ensure_ascii=False)[:500]
        except Exception:
            pass
        return CanvasAPIError(status, code, endpoint, detail)

    @staticmethod
    def _retry_delay(response: httpx2.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return min(30.0, max(0.0, float(value)))
            except ValueError:
                try:
                    delta = parsedate_to_datetime(value).timestamp() - __import__("time").time()
                    return min(30.0, max(0.0, delta))
                except Exception:
                    pass
        return min(4.0, 0.5 * (2**attempt))

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        method = method.upper()
        url = self._url(endpoint)
        attempts = 3 if method in {"GET", "HEAD"} else 1
        response: httpx2.Response | None = None
        for attempt in range(attempts):
            try:
                response = await self._client.request(
                    method, url, params=params, data=data, json=json_data
                )
            except (httpx2.ConnectError, httpx2.TimeoutException) as exc:
                if attempt + 1 == attempts:
                    raise CanvasAPIError(
                        0,
                        "canvas_connection_failed",
                        urlparse(url).path,
                        type(exc).__name__,
                    ) from exc
                await asyncio.sleep(min(4.0, 0.5 * (2**attempt)))
                continue
            if response.status_code < 400:
                if response.status_code == 204 or not response.content:
                    return None
                return response.json()
            if response.status_code not in self.RETRYABLE or attempt + 1 == attempts:
                raise self._error(response)
            await asyncio.sleep(self._retry_delay(response, attempt))
        assert response is not None
        raise self._error(response)

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        *,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        return await self.request("POST", endpoint, data=data, json_data=json_data)

    async def put(
        self,
        endpoint: str,
        *,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        return await self.request("PUT", endpoint, data=data, json_data=json_data)

    async def patch(
        self,
        endpoint: str,
        *,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        return await self.request("PATCH", endpoint, data=data, json_data=json_data)

    async def delete(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("DELETE", endpoint, params=params)

    async def page(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        limit = min(100, max(1, limit))
        url = decode_cursor(cursor) if cursor else endpoint
        query = None if cursor else {**(params or {}), "per_page": limit}
        resolved_url = self._url(url)
        response: httpx2.Response | None = None
        for attempt in range(3):
            try:
                response = await self._client.get(resolved_url, params=query)
            except (httpx2.ConnectError, httpx2.TimeoutException) as exc:
                if attempt == 2:
                    raise CanvasAPIError(
                        0,
                        "canvas_connection_failed",
                        urlparse(resolved_url).path,
                        type(exc).__name__,
                    ) from exc
                await asyncio.sleep(min(4.0, 0.5 * (2**attempt)))
                continue
            if response.status_code < 400:
                break
            if response.status_code not in self.RETRYABLE or attempt == 2:
                raise self._error(response)
            await asyncio.sleep(self._retry_delay(response, attempt))
        assert response is not None
        payload = response.json()
        items = payload if isinstance(payload, list) else [payload]
        next_url = response.links.get("next", {}).get("url")
        if next_url:
            self._url(next_url)
        return {
            "items": items[:limit],
            "next_cursor": encode_cursor(next_url) if next_url else None,
            "count": min(len(items), limit),
        }
