"""Focused tests for instructor resources and reusable Canvas prompts."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastmcp import FastMCP

from instructor_experience import register_instructor_experience


class FakeCanvasClient:
    """Small async context manager with deterministic Canvas responses."""

    @classmethod
    def from_environment(cls) -> "FakeCanvasClient":
        return cls()

    async def __aenter__(self) -> "FakeCanvasClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get(self, endpoint: str, params: dict | None = None):
        if endpoint == "/api/v1/courses/42":
            return {
                "id": "42",
                "name": "Accounting Systems",
                "course_code": "AIS 301",
                "workflow_state": "available",
                "term": {"id": "9", "name": "Fall"},
                "ignored_large_field": "not included",
            }
        if endpoint.endswith("/enrollments"):
            return [{"id": "70", "user_id": "7", "enrollment_state": "active"}]
        if endpoint.endswith("/users/7/progress"):
            return {"requirement_count": 10, "requirement_completed_count": 8}
        if endpoint.endswith("/students/submissions"):
            return [
                {
                    "id": "91",
                    "assignment_id": "11",
                    "workflow_state": "submitted",
                    "missing": False,
                    "assignment": {"id": "11", "name": "Case"},
                    "body": "omitted from the compact view",
                }
            ]
        if endpoint.endswith("/analytics/users/7/activity"):
            raise RuntimeError("analytics permission denied")
        raise AssertionError(f"Unexpected GET {endpoint} {params}")

    async def page(
        self,
        endpoint: str,
        *,
        params: dict | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ):
        if endpoint.endswith("/modules"):
            items = [{"id": "1", "name": "Welcome", "position": 1, "published": True}]
        elif endpoint.endswith("/pages"):
            items = [{"page_id": "2", "url": "welcome", "title": "Welcome", "published": True}]
        elif endpoint.endswith("/assignments"):
            items = [{"id": "3", "name": "Case", "points_possible": 20, "published": True}]
        elif endpoint.endswith("/quizzes"):
            items = [{"id": "4", "title": "Check", "quiz_type": "assignment", "published": False}]
        elif endpoint.endswith("/students/submissions"):
            items = [
                {
                    "id": "91",
                    "assignment_id": "11",
                    "workflow_state": "submitted",
                    "missing": False,
                    "assignment": {"id": "11", "name": "Case"},
                    "body": "omitted from the compact view",
                }
            ]
        elif endpoint.endswith('/enrollments'):
            items = await self.get(endpoint, params)
        else:
            raise AssertionError(f"Unexpected page {endpoint} {params} {cursor} {limit}")
        return {"items": items, "next_cursor": None, "count": len(items)}


class InstructorExperienceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mcp = FastMCP("test")
        register_instructor_experience(self.mcp)

    async def test_registers_resources_templates_and_prompts(self):
        resources = await self.mcp.list_resources()
        templates = await self.mcp.list_resource_templates()
        prompts = await self.mcp.list_prompts()

        self.assertEqual(
            {str(resource.uri) for resource in resources},
            {"canvas://reference/content-creation"},
        )
        self.assertEqual(
            {template.uri_template for template in templates},
            {
                "canvas://courses/{course_id}/overview",
                "canvas://courses/{course_id}/students/{student_id}/snapshot",
                "canvas://reference/actions/{domain}",
            },
        )
        self.assertEqual(
            {prompt.name for prompt in prompts},
            {
                "build_canvas_course",
                "grade_with_rubric",
                "review_student_progress",
                "contact_students",
                "review_grading_queue",
            },
        )

    async def test_static_references_explain_authoring_and_plan_apply(self):
        action = await self.mcp.read_resource("canvas://reference/actions/pages")
        action_payload = json.loads(action.contents[0].content)
        self.assertEqual(action_payload["domain"], "pages")
        self.assertIn("canvas_plan_page_change", action_payload["visible_tools"])
        self.assertIn("canvas_apply_change", action_payload["mutation_rule"])

        guide = await self.mcp.read_resource("canvas://reference/content-creation")
        self.assertIn("Canvas HTML Editor Allowlist", guide.contents[0].content)
        self.assertEqual(guide.contents[0].mime_type, "text/markdown")

    async def test_course_overview_is_compact(self):
        with patch(
            "resources.instructor_support.AsyncCanvasClient", FakeCanvasClient
        ):
            result = await self.mcp.read_resource("canvas://courses/42/overview")
        payload = json.loads(result.contents[0].content)

        self.assertEqual(payload["course"]["id"], "42")
        self.assertEqual(payload["modules"][0]["name"], "Welcome")
        self.assertEqual(payload["quizzes"][0]["title"], "Check")
        self.assertNotIn("ignored_large_field", payload["course"])
        self.assertEqual(payload["warnings"], [])

    async def test_student_snapshot_degrades_when_a_section_is_forbidden(self):
        with patch(
            "resources.instructor_support.AsyncCanvasClient", FakeCanvasClient
        ):
            result = await self.mcp.read_resource(
                "canvas://courses/42/students/7/snapshot"
            )
        payload = json.loads(result.contents[0].content)

        self.assertEqual(payload["student_id"], "7")
        self.assertEqual(payload["submissions"][0]["assignment_id"], "11")
        self.assertNotIn("body", payload["submissions"][0])
        self.assertNotIn("activity", payload)
        self.assertEqual(payload["warnings"][0]["section"], "activity")

    async def test_prompts_direct_writes_through_preview_and_apply(self):
        cases = {
            "build_canvas_course": {
                "arguments": {"course_id": "42", "learning_objectives": "Analyze controls"},
                "contains": "canvas_plan_",
            },
            "grade_with_rubric": {
                "arguments": {"course_id": "42", "assignment_id": "11", "student_id": "7"},
                "contains": "canvas_plan_grade_change",
            },
            "review_student_progress": {
                "arguments": {"course_id": "42", "student_id": "7"},
                "contains": "predicting",
            },
            "contact_students": {
                "arguments": {
                    "course_id": "42",
                    "audience": "students missing the case",
                    "purpose": "offer help",
                },
                "contains": "separate private conversation",
            },
            "review_grading_queue": {
                "arguments": {"course_id": "42"},
                "contains": "canvas_list_grading_queue",
            },
        }
        for name, case in cases.items():
            with self.subTest(prompt=name):
                result = await self.mcp.render_prompt(name, case["arguments"])
                text = result.messages[0].content.text
                self.assertIn(case["contains"], text)
                self.assertIn("canvas_apply_change", text)


if __name__ == "__main__":
    unittest.main()
