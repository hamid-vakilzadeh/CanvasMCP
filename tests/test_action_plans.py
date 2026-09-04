"""Focused tests for the short-lived, one-use mutation plan store."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from action_plans import Mutation, PlanStore, fingerprint


class PlanStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_plan_is_publicly_described_and_can_only_be_consumed_once(self):
        store = PlanStore()

        public = await store.create(
            action="page_change",
            summary="Create a page",
            preview={"title": "Week 1"},
            mutations=[Mutation("POST", "/api/v1/courses/7/pages")],
        )

        self.assertEqual(public["action"], "page_change")
        self.assertEqual(public["mutation_count"], 1)
        self.assertNotIn("mutations", public)
        self.assertEqual(
            public["targets"],
            [{"method": "POST", "endpoint": "/api/v1/courses/7/pages"}],
        )
        self.assertIn("confirm=true", public["next_step"])

        consumed = await store.consume(public["plan_token"])
        self.assertEqual(consumed.summary, "Create a page")
        with self.assertRaisesRegex(ValueError, "already been used"):
            await store.consume(public["plan_token"])

    async def test_expired_plan_cannot_be_consumed(self):
        store = PlanStore()
        public = await store.create(
            action="assignment_change",
            summary="Update an assignment",
            preview={},
            mutations=[Mutation("PUT", "/api/v1/courses/7/assignments/9")],
        )
        store._plans[public["plan_token"]].expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        )

        with self.assertRaisesRegex(ValueError, "expired"):
            await store.consume(public["plan_token"])
        self.assertNotIn(public["plan_token"], store._plans)

    def test_fingerprint_is_stable_for_dictionary_key_order(self):
        self.assertEqual(
            fingerprint({"id": "1", "nested": {"a": 1, "b": 2}}),
            fingerprint({"nested": {"b": 2, "a": 1}, "id": "1"}),
        )
        self.assertNotEqual(fingerprint({"id": "1"}), fingerprint({"id": "2"}))


if __name__ == "__main__":
    unittest.main()
