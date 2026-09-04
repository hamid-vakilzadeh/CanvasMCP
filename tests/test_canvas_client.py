"""Unit tests for Canvas origin checks, cursors, and read-only retries."""

from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

import httpx2


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canvas_client import (
    AsyncCanvasClient,
    CanvasAPIError,
    decode_cursor,
    encode_cursor,
)


def response(status: int, *, url: str, json=None, headers=None) -> httpx2.Response:
    return httpx2.Response(
        status,
        json=json,
        headers=headers,
        request=httpx2.Request("GET", url),
    )


class FakeHTTPClient:
    def __init__(self, *, request_results=None, get_result=None, get_results=None):
        self.request_results = list(request_results or [])
        self.get_result = get_result
        self.get_results = list(get_results or [])
        self.request_calls = []
        self.get_calls = []

    async def request(self, method, url, **kwargs):
        self.request_calls.append((method, url, kwargs))
        result = self.request_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        if self.get_results:
            result = self.get_results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        return self.get_result

    async def aclose(self):
        pass


class CanvasClientTests(unittest.IsolatedAsyncioTestCase):
    def test_cursor_round_trip_and_invalid_cursor(self):
        url = "https://school.example/api/v1/courses?page=2&per_page=50"
        self.assertEqual(decode_cursor(encode_cursor(url)), url)
        with self.assertRaisesRegex(ValueError, "Invalid pagination cursor"):
            decode_cursor("%%%%")

    def test_absolute_urls_must_keep_the_canvas_origin(self):
        client = AsyncCanvasClient("https://school.example", "token")
        self.addAsyncCleanup(client._client.aclose)
        self.assertEqual(
            client._url("https://school.example/api/v1/courses?page=2"),
            "https://school.example/api/v1/courses?page=2",
        )
        with self.assertRaisesRegex(ValueError, "changed origin"):
            client._url("https://attacker.example/api/v1/courses?page=2")

    async def test_page_bounds_limit_and_returns_opaque_same_origin_cursor(self):
        next_url = "https://school.example/api/v1/courses?page=2&per_page=100"
        fake = FakeHTTPClient(
            get_result=response(
                200,
                url="https://school.example/api/v1/courses?per_page=100",
                json=[{"id": value} for value in range(105)],
                headers={"Link": f'<{next_url}>; rel="next"'},
            )
        )
        with patch("canvas_client.httpx2.AsyncClient", return_value=fake):
            client = AsyncCanvasClient("https://school.example", "token")
            page = await client.page("/api/v1/courses", params={"state": "available"}, limit=500)

        self.assertEqual(page["count"], 100)
        self.assertEqual(len(page["items"]), 100)
        self.assertEqual(decode_cursor(page["next_cursor"]), next_url)
        self.assertEqual(fake.get_calls[0][1]["params"], {"state": "available", "per_page": 100})

    async def test_page_rejects_cross_origin_next_link_and_forged_cursor(self):
        fake = FakeHTTPClient(
            get_result=response(
                200,
                url="https://school.example/api/v1/courses",
                json=[],
                headers={
                    "Link": '<https://attacker.example/collect-token>; rel="next"'
                },
            )
        )
        with patch("canvas_client.httpx2.AsyncClient", return_value=fake):
            client = AsyncCanvasClient("https://school.example", "token")
            with self.assertRaisesRegex(ValueError, "changed origin"):
                await client.page("/api/v1/courses")
            with self.assertRaisesRegex(ValueError, "changed origin"):
                await client.page(
                    "/api/v1/courses",
                    cursor=encode_cursor("https://attacker.example/collect-token"),
                )
        self.assertEqual(len(fake.get_calls), 1)

    async def test_get_retries_retryable_response_but_post_does_not(self):
        retryable = response(
            503,
            url="https://school.example/api/v1/courses",
            json={"message": "try later"},
            headers={"Retry-After": "0"},
        )
        success = response(
            200,
            url="https://school.example/api/v1/courses",
            json=[{"id": "7"}],
        )
        read_fake = FakeHTTPClient(request_results=[retryable, success])
        with (
            patch("canvas_client.httpx2.AsyncClient", return_value=read_fake),
            patch("canvas_client.asyncio.sleep", new=AsyncMock()) as sleep,
        ):
            client = AsyncCanvasClient("https://school.example", "token")
            self.assertEqual(await client.get("/api/v1/courses"), [{"id": "7"}])
        self.assertEqual(len(read_fake.request_calls), 2)
        sleep.assert_awaited_once_with(0.0)

        write_fake = FakeHTTPClient(request_results=[retryable])
        with patch("canvas_client.httpx2.AsyncClient", return_value=write_fake):
            client = AsyncCanvasClient("https://school.example", "token")
            with self.assertRaises(CanvasAPIError) as caught:
                await client.post("/api/v1/courses", data={"course[name]": "Test"})
        self.assertEqual(caught.exception.status, 503)
        self.assertEqual(len(write_fake.request_calls), 1)

    async def test_paginated_get_uses_the_same_read_retry_policy(self):
        retryable = response(
            503,
            url="https://school.example/api/v1/courses",
            json={"message": "try later"},
            headers={"Retry-After": "0"},
        )
        success = response(
            200,
            url="https://school.example/api/v1/courses",
            json=[{"id": "7"}],
        )
        fake = FakeHTTPClient(get_results=[retryable, success])
        with (
            patch("canvas_client.httpx2.AsyncClient", return_value=fake),
            patch("canvas_client.asyncio.sleep", new=AsyncMock()) as sleep,
        ):
            client = AsyncCanvasClient("https://school.example", "token")
            page = await client.page("/api/v1/courses")

        self.assertEqual(page["items"], [{"id": "7"}])
        self.assertEqual(len(fake.get_calls), 2)
        sleep.assert_awaited_once_with(0.0)


if __name__ == "__main__":
    unittest.main()
