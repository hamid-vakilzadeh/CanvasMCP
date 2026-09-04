"""Catalog, discovery, and FastMCP Tasks integration tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from action_plans import Mutation, plan_store
from fastmcp import Client
from fastmcp.exceptions import ToolError
from fastmcp_tasks import call_tool_task
from server import DIRECT_WRITE_TOOLS, create_server
from tools.assistant import AssistantTools


class FakeWriteClient:
    @classmethod
    def from_environment(cls) -> "FakeWriteClient":
        return cls()

    async def __aenter__(self) -> "FakeWriteClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, endpoint, *, data=None, json_data=None):
        return {"id": "created", "endpoint": endpoint}

    async def page(self, endpoint, *, params=None, cursor=None, limit=50):
        return {"items": [], "next_cursor": None, "count": 0}


class ServerCatalogTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_is_compact_and_has_exact_curated_surface(self):
        server = create_server()
        async with Client(server) as client:
            tools = await client.list_tools()

        names = {tool.name for tool in tools}
        self.assertEqual(
            names,
            {*AssistantTools.VISIBLE_NAMES, "canvas_search_tools", "canvas_call_tool"},
        )
        payload = json.dumps(
            [tool.model_dump(mode="json") for tool in tools], separators=(",", ":")
        ).encode()
        self.assertLess(len(payload), 25_000)
        review_tool = next(tool for tool in tools if tool.name == "canvas_get_quiz_submission_review")
        self.assertNotIn("include_all_questions", review_tool.input_schema["properties"])

        for name in {
            "canvas_analyze_student_engagement",
            "canvas_list_grading_queue",
            "canvas_apply_change",
        }:
            tool = await server.get_tool(name)
            self.assertEqual(tool.task_config.mode, "optional")
        for name in DIRECT_WRITE_TOOLS:
            self.assertIsNone(await server.get_tool(name), name)

    async def test_search_exposes_reads_but_not_direct_mutation_tools(self):
        async with Client(create_server()) as client:
            result = await client.call_tool(
                "canvas_search_tools", {"query": "list course files create_page"}
            )
            discovered = {item["name"] for item in result.data}
            self.assertIn("list_files", discovered)
            self.assertNotIn("create_page", discovered)
            rubric_result = await client.call_tool(
                "canvas_search_tools",
                {"query": "create and attach an analytic rubric to an assignment"},
            )
            self.assertIn(
                "canvas_plan_advanced_action",
                {item["name"] for item in rubric_result.data},
            )
            with self.assertRaises(ToolError):
                await client.call_tool(
                    "canvas_call_tool",
                    {
                        "name": "create_page",
                        "arguments": {"course_id": "1", "title": "Unsafe write"},
                    },
                )

    async def test_apply_change_runs_as_a_real_background_task(self):
        plan = await plan_store.create(
            action="task_smoke",
            summary="Verify the embedded task worker",
            preview={},
            mutations=[Mutation("POST", "/api/v1/test", data={"value": "ok"})],
        )
        with patch("tools.assistant.AsyncCanvasClient", FakeWriteClient):
            async with Client(create_server()) as client:
                task = await call_tool_task(
                    client,
                    "canvas_apply_change",
                    {"plan_token": plan["plan_token"], "confirm": True},
                    timeout=10,
                )
                result = await task.result()

        self.assertTrue(task.task_id)
        self.assertEqual(result.data["status"], "completed")
        self.assertEqual(result.data["applied"], 1)

    async def test_optional_task_tools_keep_synchronous_fallback(self):
        plan = await plan_store.create(
            action="sync_fallback",
            summary="Verify synchronous fallback",
            preview={},
            mutations=[Mutation("POST", "/api/v1/test", data={"value": "ok"})],
        )
        with patch("tools.assistant.AsyncCanvasClient", FakeWriteClient):
            async with Client(create_server()) as client:
                engagement = await client.call_tool(
                    "canvas_analyze_student_engagement", {"course_id": "7"}
                )
                queue = await client.call_tool(
                    "canvas_list_grading_queue", {"course_id": "7"}
                )
                applied = await client.call_tool(
                    "canvas_apply_change",
                    {"plan_token": plan["plan_token"], "confirm": True},
                )

        self.assertEqual(engagement.data["evaluated"], 0)
        self.assertEqual(queue.data["count"], 0)
        self.assertEqual(applied.data["status"], "completed")


if __name__ == "__main__":
    unittest.main()
