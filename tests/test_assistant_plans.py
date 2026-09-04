"""Tests for assistant-facing plan creation and application semantics."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from action_plans import Mutation, PlanStore, Precondition, fingerprint
import tools.assistant as assistant_module
from tools.assistant import AssistantTools, QuizQuestionGradeUpdate


class FakeMCP:
    def tool(self, fn, **_kwargs):
        return fn


class FakeProgress:
    def __init__(self):
        self.total = None
        self.messages = []
        self.incremented = 0

    async def set_total(self, total):
        self.total = total

    async def set_message(self, message):
        self.messages.append(message)

    async def increment(self, amount=1):
        self.incremented += amount


class FakeCanvasClient:
    def __init__(
        self, *, get_values=None, page_values=None, post_values=None, put_values=None
    ):
        self.get_values = list(get_values or [])
        self.page_values = list(page_values or [])
        self.post_values = list(post_values or [])
        self.put_values = list(put_values or [])
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        pass

    async def get(self, endpoint, params=None):
        self.calls.append(("GET", endpoint, params))
        return self.get_values.pop(0)

    async def page(self, endpoint, *, params=None, cursor=None, limit=50):
        self.calls.append(("PAGE", endpoint, params, cursor, limit))
        return self.page_values.pop(0)

    async def post(self, endpoint, *, data=None, json_data=None):
        self.calls.append(("POST", endpoint, data, json_data))
        value = self.post_values.pop(0) if self.post_values else {"id": "created"}
        if isinstance(value, Exception):
            raise value
        return value

    async def put(self, endpoint, *, data=None, json_data=None):
        self.calls.append(("PUT", endpoint, data, json_data))
        value = self.put_values.pop(0) if self.put_values else {"updated": True}
        if isinstance(value, Exception):
            raise value
        return value

    async def patch(self, endpoint, *, data=None, json_data=None):
        self.calls.append(("PATCH", endpoint, data, json_data))
        value = self.put_values.pop(0) if self.put_values else {"updated": True}
        if isinstance(value, Exception):
            raise value
        return value

    async def delete(self, endpoint, params=None):
        self.calls.append(("DELETE", endpoint, params))
        return {"deleted": True}


class AssistantPlanTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = PlanStore()
        self.store_patch = patch("tools.assistant.plan_store", self.store)
        self.store_patch.start()
        self.addCleanup(self.store_patch.stop)
        self.tools = AssistantTools(FakeMCP())

    async def test_communication_plan_creates_one_private_mutation_per_recipient(self):
        plan = await self.tools.canvas_plan_communication(
            recipient_ids=[11, "12"],
            body="Please check Canvas.",
            subject="A private note",
            course_id=7,
        )

        pending = self.store._plans[plan["plan_token"]]
        self.assertEqual(plan["mutation_count"], 2)
        self.assertTrue(plan["preview"]["private"])
        self.assertEqual(
            [mutation.data["recipients[]"] for mutation in pending.mutations],
            [["11"], ["12"]],
        )
        for mutation in pending.mutations:
            self.assertIs(mutation.data["group_conversation"], False)
            self.assertIs(mutation.data["force_new"], True)
            self.assertEqual(mutation.data["context_code"], "course_7")

    async def test_private_messages_apply_separately_and_token_is_one_use(self):
        plan = await self.tools.canvas_plan_communication(
            recipient_ids=["11", "12"], body="Private update"
        )
        client = FakeCanvasClient(post_values=[{"id": "a"}, {"id": "b"}])
        progress = FakeProgress()
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            result = await self.tools.canvas_apply_change(
                plan["plan_token"], True, progress
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["applied"], 2)
        posts = [call for call in client.calls if call[0] == "POST"]
        self.assertEqual([call[2]["recipients[]"] for call in posts], [["11"], ["12"]])
        self.assertEqual(progress.total, 2)
        self.assertEqual(progress.incremented, 2)
        for message in progress.messages:
            self.assertNotIn("11", message)
            self.assertNotIn("12", message)
            self.assertNotIn("Private update", message)

        with self.assertRaisesRegex(ValueError, "already been used"):
            await self.tools.canvas_apply_change(plan["plan_token"], True, FakeProgress())

    async def test_stale_precondition_rejects_all_writes_and_consumes_plan(self):
        endpoint = "/api/v1/courses/7/assignments/9/submissions/11"
        public = await self.store.create(
            action="grade_change",
            summary="Update grade",
            preview={},
            mutations=[Mutation("PUT", endpoint, data={"submission[posted_grade]": "9"})],
            preconditions=[Precondition(endpoint, fingerprint({"grade": "8"}))],
        )
        client = FakeCanvasClient(get_values=[{"grade": "7"}])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            with self.assertRaisesRegex(ValueError, "stale"):
                await self.tools.canvas_apply_change(
                    public["plan_token"], True, FakeProgress()
                )

        self.assertEqual([call[0] for call in client.calls], ["GET"])
        with self.assertRaisesRegex(ValueError, "already been used"):
            await self.store.consume(public["plan_token"])

    async def test_created_quiz_id_is_substituted_into_item_endpoints(self):
        plan = await self.tools.canvas_plan_quiz_change(
            course_id="7",
            engine="classic",
            operation="create",
            changes={
                "title": "Check-in",
                "items": [{"question_name": "Question 1", "question_text": "2 + 2?"}],
            },
        )
        client = FakeCanvasClient(post_values=[{"id": 321}, {"id": 654}])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            result = await self.tools.canvas_apply_change(
                plan["plan_token"], True, FakeProgress()
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(client.calls[1][1], "/api/v1/courses/7/quizzes/321/questions")
        self.assertEqual(
            client.calls[1][2]["question[question_text]"], "2 + 2?"
        )

    async def test_list_courses_uses_canvas_state_array_parameter(self):
        client = FakeCanvasClient(
            page_values=[{"items": [], "next_cursor": None, "count": 0}]
        )
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            await self.tools.canvas_list_courses(state="completed", limit=25)

        call = client.calls[0]
        self.assertEqual(call[0], "PAGE")
        self.assertEqual(call[1], "/api/v1/courses")
        self.assertEqual(call[2]["state[]"], ["completed"])
        self.assertNotIn("enrollment_state", call[2])
        self.assertEqual(call[4], 25)

    async def test_list_courses_all_omits_state_filter(self):
        client = FakeCanvasClient(
            page_values=[{"items": [], "next_cursor": None, "count": 0}]
        )
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            await self.tools.canvas_list_courses(state="all")

        self.assertNotIn("state[]", client.calls[0][2])
        self.assertNotIn("enrollment_state", client.calls[0][2])

    async def test_module_add_item_plans_post_to_items_collection(self):
        public = await self.tools.canvas_plan_module_change(
            course_id=7,
            operation="add_item",
            module_id=9,
            changes={"type": "Page", "page_url": "week-1"},
        )

        pending = self.store._plans[public["plan_token"]]
        self.assertEqual(pending.action, "module_item_change")
        self.assertEqual(len(pending.mutations), 1)
        mutation = pending.mutations[0]
        self.assertEqual(mutation.method, "POST")
        self.assertEqual(mutation.endpoint, "/api/v1/courses/7/modules/9/items")
        self.assertEqual(mutation.data["module_item[type]"], "Page")
        self.assertEqual(mutation.data["module_item[page_url]"], "week-1")

    async def test_create_and_update_reject_empty_changes(self):
        with self.assertRaisesRegex(ValueError, "requires at least one field"):
            await self.tools.canvas_plan_page_change(
                course_id=7, operation="create", changes={}
            )

        client = FakeCanvasClient(get_values=[{"id": "9", "name": "Existing"}])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            with self.assertRaisesRegex(ValueError, "requires at least one field"):
                await self.tools.canvas_plan_assignment_change(
                    course_id=7,
                    operation="update",
                    assignment_id=9,
                    changes=None,
                )
        self.assertEqual(len(self.store._plans), 0)

    async def test_page_url_is_encoded_as_one_path_segment(self):
        client = FakeCanvasClient(get_values=[{"page_id": "31", "title": "Week 1"}])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            public = await self.tools.canvas_plan_page_change(
                course_id=7,
                operation="update",
                page_url="Week 1/Intro?draft=true",
                changes={"title": "Updated"},
            )

        expected = "/api/v1/courses/7/pages/Week%201%2FIntro%3Fdraft%3Dtrue"
        self.assertEqual(client.calls[0][1], expected)
        pending = self.store._plans[public["plan_token"]]
        self.assertEqual(pending.mutations[0].endpoint, expected)
        self.assertEqual(pending.preconditions[0].endpoint, expected)

    async def test_engagement_progress_omits_student_identifiers(self):
        client = FakeCanvasClient(page_values=[{
            "items": [{"assignment_id": "9", "missing": True}],
            "next_cursor": None,
        }])
        progress = FakeProgress()
        with patch.object(assistant_module.AsyncCanvasClient, "from_environment", return_value=client):
            result = await self.tools.canvas_analyze_student_engagement(
                course_id="7", student_ids=["987654321"], progress=progress,
            )
        self.assertEqual(result["students"][0]["student_id"], "987654321")
        self.assertTrue(progress.messages)
        self.assertNotIn("987654321", " ".join(progress.messages))

    async def test_engagement_empty_roster_uses_nonzero_progress_total(self):
        client = FakeCanvasClient(
            page_values=[{"items": [], "next_cursor": None, "count": 0}]
        )
        progress = FakeProgress()
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            result = await self.tools.canvas_analyze_student_engagement(
                course_id=7, progress=progress
            )

        self.assertEqual(progress.total, 1)
        self.assertEqual(progress.incremented, 0)
        self.assertEqual(result["evaluated"], 0)
        self.assertEqual(result["matched"], 0)
        self.assertEqual(result["students"], [])

    async def test_assignment_arrays_use_rails_array_parameters(self):
        public = await self.tools.canvas_plan_assignment_change(
            course_id=7,
            operation="create",
            changes={
                "name": "Upload",
                "submission_types": ["online_upload", "online_text_entry"],
                "allowed_extensions": ["pdf", "docx"],
            },
        )

        data = self.store._plans[public["plan_token"]].mutations[0].data
        self.assertEqual(data["assignment[name]"], "Upload")
        self.assertEqual(
            data["assignment[submission_types][]"],
            ["online_upload", "online_text_entry"],
        )
        self.assertEqual(
            data["assignment[allowed_extensions][]"], ["pdf", "docx"]
        )

    async def test_classic_quiz_answers_are_recursively_form_encoded(self):
        public = await self.tools.canvas_plan_quiz_change(
            course_id=7,
            engine="classic",
            operation="create",
            changes={
                "title": "Check-in",
                "items": [
                    {
                        "question_name": "Q1",
                        "question_type": "multiple_choice_question",
                        "answers": [
                            {"answer_text": "Four", "answer_weight": 100},
                            {"answer_text": "Five", "answer_weight": 0},
                        ],
                    }
                ],
            },
        )

        pending = self.store._plans[public["plan_token"]]
        self.assertEqual(pending.mutations[0].data["quiz[title]"], "Check-in")
        question = pending.mutations[1]
        self.assertEqual(question.data["question[answers][0][answer_text]"], "Four")
        self.assertEqual(question.data["question[answers][0][answer_weight]"], 100)
        self.assertEqual(question.data["question[answers][1][answer_text]"], "Five")
        self.assertEqual(question.data["question[answers][1][answer_weight]"], 0)

    async def test_override_arrays_and_module_prerequisites_are_form_encoded(self):
        override = await self.tools.canvas_plan_advanced_action(
            action="create_assignment_override",
            course_id=7,
            arguments={
                "assignment_id": 9,
                "title": "Section extension",
                "student_ids": [11, 12],
            },
        )
        override_data = self.store._plans[override["plan_token"]].mutations[0].data
        self.assertEqual(
            override_data["assignment_override[student_ids][]"], [11, 12]
        )

        module = await self.tools.canvas_plan_module_change(
            course_id=7,
            operation="create",
            changes={"name": "Week 2", "prerequisite_module_ids": [4, 5]},
        )
        module_data = self.store._plans[module["plan_token"]].mutations[0].data
        self.assertEqual(
            module_data["module[prerequisite_module_ids][]"], [4, 5]
        )

    async def test_course_copy_date_substitutions_are_recursively_encoded(self):
        public = await self.tools.canvas_plan_course_copy(
            source_course_id=7,
            destination_course_id=8,
            date_shift_options={
                "shift_dates": True,
                "old_start_date": "2026-01-12",
                "new_start_date": "2026-08-24",
                "day_substitutions": {"1": "2", "3": "4"},
            },
        )

        data = self.store._plans[public["plan_token"]].mutations[0].data
        self.assertIs(data["date_shift_options[shift_dates]"], True)
        self.assertEqual(data["date_shift_options[old_start_date]"], "2026-01-12")
        self.assertEqual(data["date_shift_options[new_start_date]"], "2026-08-24")
        self.assertEqual(data["date_shift_options[day_substitutions][1]"], "2")
        self.assertEqual(data["date_shift_options[day_substitutions][3]"], "4")

    async def test_new_quiz_create_uses_post_and_item_prefix(self):
        public = await self.tools.canvas_plan_quiz_change(
            course_id=7,
            engine="new",
            operation="create",
            changes={
                "title": "New Quiz",
                "items": [
                    {
                        "position": 1,
                        "entry": {
                            "title": "Question 1",
                            "item_body": "<p>Question</p>",
                        },
                    }
                ],
            },
        )

        pending = self.store._plans[public["plan_token"]]
        create, item = pending.mutations
        self.assertEqual(create.method, "POST")
        self.assertEqual(create.endpoint, "/api/quiz/v1/courses/7/quizzes")
        self.assertEqual(create.data["quiz[title]"], "New Quiz")
        self.assertEqual(item.method, "POST")
        self.assertEqual(
            item.endpoint,
            "/api/quiz/v1/courses/7/quizzes/{created_quiz_id}/items",
        )
        self.assertEqual(item.data["item[position]"], 1)
        self.assertEqual(item.data["item[entry][title]"], "Question 1")
        self.assertEqual(item.data["item[entry][item_body]"], "<p>Question</p>")

    async def test_new_quiz_update_uses_patch(self):
        client = FakeCanvasClient(get_values=[{"id": "21", "title": "Before"}])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            public = await self.tools.canvas_plan_quiz_change(
                course_id=7,
                engine="new",
                operation="update",
                quiz_id=21,
                changes={"title": "After"},
            )

        mutation = self.store._plans[public["plan_token"]].mutations[0]
        self.assertEqual(mutation.method, "PATCH")
        self.assertEqual(mutation.endpoint, "/api/quiz/v1/courses/7/quizzes/21")
        self.assertEqual(mutation.data, {"quiz[title]": "After"})

    async def test_assignment_group_fields_are_unprefixed(self):
        public = await self.tools.canvas_plan_advanced_action(
            action="create_assignment_group",
            course_id=7,
            arguments={"name": "Exams", "position": 2, "group_weight": 40},
        )

        data = self.store._plans[public["plan_token"]].mutations[0].data
        self.assertEqual(data, {"name": "Exams", "position": 2, "group_weight": 40})
        self.assertNotIn("assignment_group[name]", data)

    async def test_create_rubric_encodes_criteria_and_assignment_association(self):
        assignment = {
            "id": "9",
            "name": "Reflection",
            "points_possible": 10,
            "published": False,
        }
        client = FakeCanvasClient(get_values=[assignment])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            public = await self.tools.canvas_plan_advanced_action(
                action="create_rubric",
                course_id=7,
                arguments={
                    "assignment_id": 9,
                    "title": "Reflection rubric",
                    "use_for_grading": True,
                    "criteria": [
                        {
                            "description": "Insight",
                            "points": 10,
                            "ratings": [
                                {"description": "Strong", "points": 10},
                                {"description": "Developing", "points": 5},
                                {"description": "Missing", "points": 0},
                            ],
                        }
                    ],
                },
            )

        pending = self.store._plans[public["plan_token"]]
        mutation = pending.mutations[0]
        self.assertEqual(mutation.method, "POST")
        self.assertEqual(mutation.endpoint, "/api/v1/courses/7/rubrics")
        self.assertEqual(mutation.data["rubric[title]"], "Reflection rubric")
        self.assertEqual(
            mutation.data["rubric[criteria][0][ratings][1][description]"],
            "Developing",
        )
        self.assertEqual(
            mutation.data["rubric[criteria][0][ratings][1][points]"], 5
        )
        self.assertEqual(
            mutation.data["rubric_association[association_id]"], "9"
        )
        self.assertEqual(
            mutation.data["rubric_association[association_type]"], "Assignment"
        )
        self.assertIs(mutation.data["rubric_association[use_for_grading]"], True)
        self.assertEqual(public["preview"]["rubric"]["points_possible"], 10)
        self.assertEqual(public["warnings"], [])
        self.assertEqual(len(pending.preconditions), 1)

    async def test_assignment_group_delete_preserves_move_destination(self):
        snapshot = {"id": "9", "name": "Old group"}
        client = FakeCanvasClient(get_values=[snapshot])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            public = await self.tools.canvas_plan_advanced_action(
                action="delete_assignment_group",
                course_id=7,
                arguments={"assignment_group_id": 9, "move_assignments_to": 10},
            )

        pending = self.store._plans[public["plan_token"]]
        mutation = pending.mutations[0]
        self.assertEqual(mutation.method, "DELETE")
        self.assertEqual(mutation.endpoint, "/api/v1/courses/7/assignment_groups/9")
        self.assertEqual(mutation.data, {"move_assignments_to": 10})

        applying_client = FakeCanvasClient(get_values=[snapshot])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=applying_client,
        ):
            result = await self.tools.canvas_apply_change(
                public["plan_token"], True, FakeProgress()
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            applying_client.calls[-1],
            (
                "DELETE",
                "/api/v1/courses/7/assignment_groups/9",
                {"move_assignments_to": 10},
            ),
        )

    async def test_grading_queue_sends_workflow_state_to_canvas(self):
        client = FakeCanvasClient(
            page_values=[{"items": [], "next_cursor": None, "count": 0}]
        )
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            result = await self.tools.canvas_list_grading_queue(
                course_id=7,
                assignment_ids=[9],
                workflow_state="pending_review",
                progress=FakeProgress(),
            )

        params = client.calls[0][2]
        self.assertEqual(params["workflow_state"], "pending_review")
        self.assertEqual(params["assignment_ids[]"], ["9"])
        self.assertEqual(result["workflow_state"], "pending_review")

    async def test_selected_course_copy_items_are_sent_immediately(self):
        public = await self.tools.canvas_plan_course_copy(
            source_course_id=7,
            destination_course_id=8,
            selective_import=True,
            selected_items={"assignments": [11, 12], "pages": ["welcome"]},
        )

        pending = self.store._plans[public["plan_token"]]
        data = pending.mutations[0].data
        self.assertEqual(data["select[assignments][]"], [11, 12])
        self.assertEqual(data["select[pages][]"], ["welcome"])
        self.assertNotIn("selective_import", data)
        self.assertFalse(public["preview"]["selective_import"])

    async def test_staged_selective_copy_exposes_follow_up_and_plans_selection(self):
        staged = await self.tools.canvas_plan_course_copy(
            source_course_id=7,
            destination_course_id=8,
            selective_import=True,
        )
        staged_pending = self.store._plans[staged["plan_token"]]
        self.assertIs(staged_pending.mutations[0].data["selective_import"], True)
        self.assertTrue(any("canvas_get_course_copy_selection" in warning for warning in staged["warnings"]))

        client = FakeCanvasClient(get_values=[{"id": "44", "workflow_state": "waiting_for_select"}])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            follow_up = await self.tools.canvas_plan_advanced_action(
                action="apply_course_copy_selection",
                course_id=8,
                arguments={
                    "migration_id": 44,
                    "selection_properties": {
                        "copy[all_assignments]": "1",
                        "copy[assignment_11]": "1",
                    },
                },
            )

        mutation = self.store._plans[follow_up["plan_token"]].mutations[0]
        self.assertEqual(mutation.method, "PUT")
        self.assertEqual(mutation.endpoint, "/api/v1/courses/8/content_migrations/44")
        self.assertEqual(
            mutation.data,
            {"copy[all_assignments]": "1", "copy[assignment_11]": "1"},
        )

    async def test_plan_targets_expose_all_quiz_mutations(self):
        public = await self.tools.canvas_plan_quiz_change(
            course_id=7,
            engine="classic",
            operation="create",
            changes={"title": "Quiz", "items": [{"question_text": "Q1"}]},
        )

        self.assertEqual(public["mutation_count"], 2)
        self.assertEqual(len(public["targets"]), 2)
        self.assertEqual(public["targets"][0]["method"], "POST")
        self.assertEqual(public["targets"][1]["label"], "quiz-item:1")

    async def test_changed_file_is_rejected_before_canvas_request(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reading.pdf"
            path.write_bytes(b"first version")
            public = await self.tools.canvas_plan_file_upload(7, str(path))
            path.write_bytes(b"second version with different size")

            client = FakeCanvasClient()
            with patch.object(
                assistant_module.AsyncCanvasClient,
                "from_environment",
                return_value=client,
            ):
                result = await self.tools.canvas_apply_change(
                    public["plan_token"], True, FakeProgress()
                )

        self.assertEqual(client.calls, [])
        self.assertEqual(result["status"], "failed")
        self.assertIn("local file changed", result["results"][0]["error"])

    async def test_storage_upload_does_not_receive_canvas_authorization_header(self):
        observed = {}

        class FakeResponse:
            status_code = 200
            headers = {}

            @staticmethod
            def json():
                return {"id": "uploaded"}

        class FakeUploader:
            def __init__(self, **kwargs):
                observed["client_kwargs"] = kwargs

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, url, **kwargs):
                observed["url"] = url
                observed["post_kwargs"] = kwargs
                return FakeResponse()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reading.pdf"
            path.write_bytes(b"course content")
            public = await self.tools.canvas_plan_file_upload(7, str(path))
            mutation = self.store._plans[public["plan_token"]].mutations[0]
            client = FakeCanvasClient(
                post_values=[
                    {
                        "upload_url": "https://uploads.example/files",
                        "upload_params": {"key": "signed-storage-key"},
                    }
                ]
            )

            with patch.object(assistant_module.httpx2, "AsyncClient", FakeUploader):
                result = await self.tools._upload(client, mutation)

        self.assertEqual(result, {"id": "uploaded"})
        self.assertEqual(observed["url"], "https://uploads.example/files")
        self.assertNotIn("headers", observed["client_kwargs"])
        self.assertNotIn("headers", observed["post_kwargs"])

    async def test_dependent_quiz_items_are_skipped_when_create_fails(self):
        public = await self.tools.canvas_plan_quiz_change(
            course_id=7,
            engine="classic",
            operation="create",
            changes={"title": "Quiz", "items": [{"question_text": "Q1"}]},
        )
        client = FakeCanvasClient(post_values=[RuntimeError("create failed")])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            result = await self.tools.canvas_apply_change(
                public["plan_token"], True, FakeProgress()
            )

        self.assertEqual([call[0] for call in client.calls], ["POST"])
        self.assertEqual([item["status"] for item in result["results"]], ["failed", "skipped"])
        self.assertIn("not created", result["results"][1]["error"])

    async def test_anonymous_submission_review_uses_anonymous_endpoint(self):
        client = FakeCanvasClient(get_values=[{"id": "submission"}])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            await self.tools.canvas_get_submission_review(
                course_id=7, assignment_id=9, anonymous_id="anon-42"
            )

        self.assertEqual(
            client.calls[0][1],
            "/api/v1/courses/7/assignments/9/anonymous_submissions/anon-42",
        )

    async def test_anonymous_grade_plan_includes_recursive_rubric_payload(self):
        endpoint = "/api/v1/courses/7/assignments/9/anonymous_submissions/anon-42"
        client = FakeCanvasClient(get_values=[{"grade": None, "workflow_state": "submitted"}])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            public = await self.tools.canvas_plan_grade_change(
                course_id=7,
                assignment_id=9,
                anonymous_id="anon-42",
                posted_grade="9",
                rubric_assessment={
                    "criterion_1": {"points": 4, "comments": "Clear analysis"}
                },
            )

        pending = self.store._plans[public["plan_token"]]
        self.assertEqual(client.calls[0][1], endpoint)
        self.assertEqual(pending.mutations[0].endpoint, endpoint)
        self.assertEqual(pending.mutations[0].data["submission[posted_grade]"], "9")
        self.assertEqual(
            pending.mutations[0].data["rubric_assessment[criterion_1][points]"], 4
        )
        self.assertEqual(
            pending.mutations[0].data["rubric_assessment[criterion_1][comments]"],
            "Clear analysis",
        )
        self.assertEqual(public["preview"]["identifier_type"], "anonymous_id")

    async def test_discussion_entry_plan_posts_to_topic(self):
        client = FakeCanvasClient(
            get_values=[{"id": "55", "title": "Weekly reflection", "published": False}]
        )
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            public = await self.tools.canvas_plan_discussion_entry(
                course_id=7,
                topic_id=55,
                operation="post_entry",
                message="  Instructor example  ",
            )

        pending = self.store._plans[public["plan_token"]]
        self.assertEqual(
            pending.mutations[0].endpoint,
            "/api/v1/courses/7/discussion_topics/55/entries",
        )
        self.assertEqual(pending.mutations[0].data, {"message": "Instructor example"})
        self.assertEqual(public["preview"]["topic"]["title"], "Weekly reflection")
        self.assertIn("immediately", public["warnings"][0])

    async def test_discussion_reply_validates_parent_and_applies(self):
        topic = {"id": "55", "title": "Weekly reflection", "published": False}
        entry_payload = [
            {
                "id": "91",
                "user_name": "Student",
                "message": "<p>Original contribution</p>",
            }
        ]
        planning_client = FakeCanvasClient(get_values=[topic, entry_payload])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=planning_client,
        ):
            public = await self.tools.canvas_plan_discussion_entry(
                course_id=7,
                topic_id=55,
                operation="post_reply",
                entry_id=91,
                message="Thanks for connecting those ideas.",
            )

        pending = self.store._plans[public["plan_token"]]
        self.assertEqual(public["preview"]["parent_entry"]["message"], "Original contribution")
        self.assertEqual(pending.preconditions[0].params, {"ids[]": ["91"]})
        self.assertEqual(
            pending.mutations[0].endpoint,
            "/api/v1/courses/7/discussion_topics/55/entries/91/replies",
        )

        applying_client = FakeCanvasClient(
            get_values=[entry_payload], post_values=[{"id": "92"}]
        )
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=applying_client,
        ):
            result = await self.tools.canvas_apply_change(
                public["plan_token"], True, FakeProgress()
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            applying_client.calls[-1],
            (
                "POST",
                "/api/v1/courses/7/discussion_topics/55/entries/91/replies",
                {"message": "Thanks for connecting those ideas."},
                None,
            ),
        )

    async def test_discussion_reply_requires_parent_and_rejects_blank_message(self):
        with self.assertRaisesRegex(ValueError, "requires entry_id"):
            await self.tools.canvas_plan_discussion_entry(
                7, 55, "post_reply", "Reply without a parent"
            )
        with self.assertRaisesRegex(ValueError, "non-whitespace"):
            await self.tools.canvas_plan_discussion_entry(
                7, 55, "post_entry", "   "
            )

    async def test_comment_only_grade_plan_preserves_comment_snapshot_and_applies(self):
        endpoint = "/api/v1/courses/7/assignments/9/submissions/11"
        before = {
            "grade": "8",
            "workflow_state": "graded",
            "submission_comments": [
                {"id": "1", "author_name": "Instructor", "comment": "Earlier note"}
            ],
        }
        planning_client = FakeCanvasClient(get_values=[before])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=planning_client,
        ):
            public = await self.tools.canvas_plan_grade_change(
                course_id=7,
                assignment_id=9,
                student_id=11,
                comment="New feedback",
                comment_attempt=2,
            )

        pending = self.store._plans[public["plan_token"]]
        self.assertEqual(
            pending.preconditions[0].params["include[]"],
            ["submission_comments", "rubric_assessment", "submission_history", "visibility"],
        )
        self.assertEqual(public["preview"]["recent_comments"][0]["comment"], "Earlier note")
        self.assertEqual(pending.mutations[0].data["comment[text_comment]"], "New feedback")
        self.assertEqual(pending.mutations[0].data["comment[attempt]"], 2)
        self.assertNotIn("submission[posted_grade]", pending.mutations[0].data)

        applying_client = FakeCanvasClient(get_values=[before])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=applying_client,
        ):
            result = await self.tools.canvas_apply_change(
                public["plan_token"], True, FakeProgress()
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(applying_client.calls[-1][0], "PUT")
        self.assertIn("notify", public["warnings"][0])

    async def test_grade_comment_validation_and_group_warning(self):
        with self.assertRaisesRegex(ValueError, "non-whitespace"):
            client = FakeCanvasClient(get_values=[{"grade": None}])
            with patch.object(
                assistant_module.AsyncCanvasClient,
                "from_environment",
                return_value=client,
            ):
                await self.tools.canvas_plan_grade_change(
                    7, 9, student_id=11, comment="   "
                )

        client = FakeCanvasClient(get_values=[{"grade": None}])
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            public = await self.tools.canvas_plan_grade_change(
                7, 9, student_id=11, comment="Group feedback", group_comment=True
            )
        self.assertTrue(any("group member" in warning for warning in public["warnings"]))

    async def test_quiz_submission_review_filters_mixed_quiz_to_manual_questions(self):
        submission_payload = {
            "quiz_submissions": [
                {
                    "id": "40",
                    "user_id": "11",
                    "attempt": 2,
                    "workflow_state": "complete",
                    "score": 7.5,
                }
            ]
        }
        answer_payload = {
            "quiz_submission_questions": [
                {
                    "id": "90",
                    "answer": "<p>Student explanation</p>",
                    "score": 3.5,
                    "comment": "Good start",
                },
                {"id": "91", "answer": "Choice A", "score": 1},
                {"id": "92"},
                {"id": "93", "answer": "Unclassified answer"},
            ]
        }
        client = FakeCanvasClient(
            get_values=[submission_payload, answer_payload],
            page_values=[
                {
                    "items": [
                        {
                            "id": "90",
                            "question_name": "Essay 1",
                            "question_type": "essay_question",
                            "question_text": "<p>Explain the control.</p>",
                            "points_possible": 5,
                        },
                        {"id": "91", "question_type": "multiple_choice_question"},
                        {"id": "92", "question_type": "file_upload_question"},
                        {"id": "93"},
                    ],
                    "next_cursor": None,
                    "count": 4,
                }
            ],
        )
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=client,
        ):
            review = await self.tools.canvas_get_quiz_submission_review(
                course_id=7, quiz_id=8, quiz_submission_id=40
            )

        self.assertEqual(review["question_count"], 2)
        self.assertEqual([q["question_id"] for q in review["questions"]], ["90", "92"])
        self.assertEqual(review["questions"][0]["answer"], "Student explanation")
        self.assertEqual(review["questions"][0]["score"], 3.5)
        self.assertFalse(review["questions"][1]["answer_available"])
        self.assertEqual(review["answers_unavailable"], 1)

    async def test_quiz_question_grade_plan_uses_documented_form_keys_and_applies(self):
        submission_payload = {
            "quiz_submissions": [
                {
                    "id": "40",
                    "user_id": "11",
                    "attempt": 2,
                    "workflow_state": "complete",
                    "score": 7.5,
                }
            ]
        }
        answer_payload = {
            "quiz_submission_questions": [
                {"id": "90", "answer": "Response", "score": 3.0, "comment": None},
                {"id": "91", "score": 1},
                {"id": "92"},
            ]
        }
        definition_page = {
            "items": [
                {
                    "id": "90",
                    "question_name": "Essay 1",
                    "question_type": "essay_question",
                    "question_text": "Explain.",
                    "points_possible": 5,
                },
                {"id": "91", "question_type": "multiple_choice_question"},
                {"id": "92", "question_type": "file_upload_question", "points_possible": 5},
            ],
            "next_cursor": None,
            "count": 3,
        }
        planning_client = FakeCanvasClient(
            get_values=[submission_payload, answer_payload],
            page_values=[definition_page],
        )
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=planning_client,
        ):
            public = await self.tools.canvas_plan_quiz_submission_grade(
                course_id=7,
                quiz_id=8,
                quiz_submission_id=40,
                question_updates=[
                    QuizQuestionGradeUpdate(
                        question_id=90, score=4.5, comment="Clear explanation"
                    ),
                    QuizQuestionGradeUpdate(question_id=92, score=4),
                ],
            )

        pending = self.store._plans[public["plan_token"]]
        data = pending.mutations[0].data
        self.assertEqual(data["quiz_submissions[][attempt]"], 2)
        self.assertEqual(data["quiz_submissions[][questions][90][score]"], 4.5)
        self.assertEqual(data["quiz_submissions[][questions][92][score]"], 4)
        self.assertFalse(any("[91]" in key for key in data))
        self.assertEqual(
            data["quiz_submissions[][questions][90][comment]"], "Clear explanation"
        )
        self.assertEqual(len(pending.preconditions), 2)
        self.assertIn("plan is the draft", public["warnings"][0].lower())

        applying_client = FakeCanvasClient(
            get_values=[submission_payload, answer_payload], put_values=[{"updated": True}]
        )
        with patch.object(
            assistant_module.AsyncCanvasClient,
            "from_environment",
            return_value=applying_client,
        ):
            result = await self.tools.canvas_apply_change(
                public["plan_token"], True, FakeProgress()
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(applying_client.calls[-1][0], "PUT")

    async def test_quiz_question_grade_plan_rejects_unknown_and_negative_scores(self):
        submission_payload = {
            "quiz_submissions": [
                {"id": "40", "user_id": "11", "attempt": 1, "workflow_state": "complete"}
            ]
        }
        answer_payload = {"quiz_submission_questions": [{"id": "90"}]}
        page = {
            "items": [{"id": "90", "question_type": "essay_question"}],
            "next_cursor": None,
            "count": 1,
        }
        for update, message in (
            (QuizQuestionGradeUpdate(question_id=999, score=1), "only manually graded"),
            (QuizQuestionGradeUpdate(question_id=90, score=-1), "cannot be negative"),
        ):
            client = FakeCanvasClient(
                get_values=[submission_payload, answer_payload], page_values=[page]
            )
            with patch.object(
                assistant_module.AsyncCanvasClient,
                "from_environment",
                return_value=client,
            ):
                with self.assertRaisesRegex(ValueError, message):
                    await self.tools.canvas_plan_quiz_submission_grade(
                        7, 8, 40, [update]
                    )

    async def test_quiz_grade_rejects_mixed_batch_with_auto_or_unknown_question(self):
        submission_payload = {
            "quiz_submissions": [
                {"id": "40", "user_id": "11", "attempt": 1, "workflow_state": "complete"}
            ]
        }
        # A missing score does not make an automatically graded question eligible.
        for question_type in (
            "multiple_choice_question", "true_false_question", "short_answer_question",
            "fill_in_multiple_blanks_question", "multiple_answers_question",
            "multiple_dropdowns_question", "matching_question", "numerical_question",
            "calculated_question", "text_only_question", "future_question_type", None,
        ):
            with self.subTest(question_type=question_type):
                client = FakeCanvasClient(
                    get_values=[submission_payload, {"quiz_submission_questions": [{"id": "91"}]}],
                    page_values=[{
                        "items": [
                            {"id": "90", "question_type": "essay_question"},
                            {"id": "91", "question_type": question_type},
                        ],
                        "next_cursor": None,
                        "count": 2,
                    }],
                )
                with patch.object(
                    assistant_module.AsyncCanvasClient, "from_environment", return_value=client
                ):
                    with self.assertRaisesRegex(ValueError, "only manually graded"):
                        await self.tools.canvas_plan_quiz_submission_grade(
                            7, 8, 40,
                            [
                                QuizQuestionGradeUpdate(question_id=90, score=3),
                                QuizQuestionGradeUpdate(question_id=91, comment="Feedback"),
                            ],
                        )
                self.assertFalse(self.store._plans)
                self.assertTrue(all(call[0] in {"GET", "PAGE"} for call in client.calls))

    async def test_auto_graded_only_quiz_has_no_manual_questions(self):
        client = FakeCanvasClient(
            get_values=[
                {"quiz_submissions": [{"id": "40", "attempt": 1, "workflow_state": "complete"}]},
                {"quiz_submission_questions": [{"id": "91", "question_type": "true_false_question"}]},
            ],
            page_values=[{"items": [], "next_cursor": None, "count": 0}],
        )
        with patch.object(
            assistant_module.AsyncCanvasClient, "from_environment", return_value=client
        ):
            review = await self.tools.canvas_get_quiz_submission_review(7, 8, 40)
        self.assertEqual(review["questions"], [])
        self.assertEqual(review["question_count"], 0)
        self.assertEqual(review["answers_unavailable"], 0)


if __name__ == "__main__":
    unittest.main()
