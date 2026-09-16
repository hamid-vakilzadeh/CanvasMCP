"""Synthetic regression coverage for grade preconditions and posting visibility."""

import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from action_plans import PlanStore, fingerprint
from canvas_client import AsyncCanvasClient, CanvasAPIError
from fastmcp import Client
from server import create_server
from tools.assistant import AssistantTools
from tools.grade_posting import GradePostingTools, grade_visibility
from test_assistant_plans import FakeMCP, FakeProgress


class SyntheticCanvas:
    def __init__(self):
        self.calls = []
        self.assignment = {'id': 9, 'course_id': 7, 'name': 'Synthetic assignment',
                           'published': True, 'post_manually': True, 'muted': True}
        self.submissions = {str(i): {
            'id': i + 100, 'user_id': i, 'assignment_id': 9, 'score': None, 'grade': None,
            'attempt': 1, 'body': 'Synthetic response', 'excused': False,
            'workflow_state': 'submitted', 'seconds_late': 100,
            'late_policy_status': 'late', 'points_deducted': 0,
            'rubric_assessment': {'criterion': {'points': 1, 'comments': 'Synthetic feedback'}},
            'submission_comments': [{'id': 1, 'comment': 'Synthetic comment'}],
            'submission_history': [{'attempt': 1, 'score': None, 'seconds_late': 100}],
            'posted_at': None, 'assignment_visible': True,
        } for i in (11, 12)}
        self.progress = {'id': 80, 'context_type': 'Course', 'context_id': 7,
                         'tag': 'post_assignment_grades', 'workflow_state': 'queued', 'completion': 0}
        self.response = {'data': {'postAssignmentGrades': {
            'progress': {'_id': '80', 'state': 'queued', 'completion': 0}, 'errors': None}}}
        self.readback_error = False

    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass

    async def get(self, endpoint, params=None):
        self.calls.append(('GET', endpoint, params))
        if endpoint == '/api/v1/progress/80':
            return copy.deepcopy(self.progress)
        if endpoint == '/api/v1/courses/7/assignments/9':
            return copy.deepcopy(self.assignment)
        if self.readback_error and any(c[0] == 'PUT' for c in self.calls):
            raise CanvasAPIError(503, 'unavailable', endpoint, 'Synthetic readback unavailable')
        if '/anonymous_submissions/' in endpoint:
            value = copy.deepcopy(self.submissions['11'])
            value.pop('user_id')
            value['anonymous_id'] = 'synthetic-anon'
        else:
            value = copy.deepcopy(self.submissions[endpoint.split('/')[-1]])
        # Reproduce time passing between planning and applying without sleeps.
        value['seconds_late'] += len(self.calls)
        value['submission_history'][0]['seconds_late'] += len(self.calls)
        return value

    async def put(self, endpoint, *, data=None, json_data=None):
        self.calls.append(('PUT', endpoint, data))
        key = '11' if '/anonymous_submissions/' in endpoint else endpoint.split('/')[-1]
        submission = self.submissions[key]
        if 'submission[posted_grade]' in data:
            submission.update(score=float(data['submission[posted_grade]']),
                              grade=data['submission[posted_grade]'], workflow_state='graded')
        if not self.assignment['post_manually']:
            submission['posted_at'] = '2026-09-16T10:00:00Z'
        return copy.deepcopy(submission)

    async def post(self, endpoint, *, json_data=None, data=None):
        self.calls.append(('POST', endpoint, json_data))
        if isinstance(self.response, Exception):
            raise self.response
        return copy.deepcopy(self.response)


class GradePostingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = PlanStore()
        self.canvas = SyntheticCanvas()
        for target in ('tools.assistant.plan_store', 'tools.grade_posting.plan_store'):
            p = patch(target, self.store); p.start(); self.addCleanup(p.stop)
        p = patch.object(AsyncCanvasClient, 'from_environment', return_value=self.canvas)
        p.start(); self.addCleanup(p.stop)
        self.assistant = AssistantTools(FakeMCP())
        self.posting = GradePostingTools(FakeMCP())

    async def grade_plan(self, **kwargs):
        return await self.assistant.canvas_plan_grade_change(7, 9, student_id=11, posted_grade='5', **kwargs)

    async def apply(self, plan):
        return await self.assistant.canvas_apply_change(plan['plan_token'], True, FakeProgress())

    def graded(self, student='11'):
        self.canvas.submissions[student].update(score=5, grade='5', workflow_state='graded')

    async def test_mcp_grade_plan_ignores_both_ticking_counters_and_reports_hidden_grade(self):
        async with Client(create_server()) as client:
            plan = await client.call_tool('canvas_plan_grade_change', {
                'course_id': 7, 'assignment_id': 9, 'student_id': 11, 'posted_grade': '5'})
            result = await client.call_tool('canvas_apply_change', {
                'plan_token': plan.data['plan_token'], 'confirm': True})
        self.assertEqual(result.data['status'], 'completed')
        self.assertEqual(result.data['applied'], 1)
        readback = result.data['results'][0]['grade_readback']
        self.assertEqual(readback['score'], 5)
        self.assertEqual(readback['student_visibility'], 'hidden')
        self.assertFalse(readback['student_visible'])
        self.assertIn('separate grade release', result.data['next_step'])
        self.assertEqual(sum(c[0] == 'PUT' for c in self.canvas.calls), 1)
        self.assertFalse(any(c[0] == 'POST' for c in self.canvas.calls))

    async def test_real_changes_remain_stale_including_nested_content(self):
        changes = [
            {'score': 3}, {'grade': '3'}, {'attempt': 2}, {'body': 'Changed synthetic response'},
            {'excused': True}, {'late_policy_status': 'none'}, {'points_deducted': 1},
            {'posted_at': '2026-09-16T09:00:00Z'}, {'assignment_visible': False},
            {'rubric_assessment': {'criterion': {'points': 2}}},
            {'submission_comments': [{'id': 1, 'comment': 'Changed feedback'}]},
            {'submission_history': [{'attempt': 1, 'score': 3, 'seconds_late': 110}]},
        ]
        for change in changes:
            with self.subTest(change=change):
                before = copy.deepcopy(self.canvas.submissions['11'])
                plan = await self.grade_plan()
                self.canvas.submissions['11'].update(change)
                with self.assertRaisesRegex(ValueError, 'stale'):
                    await self.apply(plan)
                self.canvas.submissions['11'] = before
        self.assertFalse(any(c[0] == 'PUT' for c in self.canvas.calls))

    def test_submission_comparison_is_explicit_and_does_not_mutate_raw_data(self):
        before = {'seconds_late': 1, 'submission_history': [{'seconds_late': 1, 'grade': None}]}
        after = {'seconds_late': 8, 'submission_history': [{'seconds_late': 8, 'grade': None}]}
        original = copy.deepcopy(before)
        self.assertEqual(fingerprint(before, kind='submission'), fingerprint(after, kind='submission'))
        self.assertNotEqual(fingerprint(before), fingerprint(after))
        self.assertEqual(before, original)

    async def test_posted_at_not_deprecated_muted_controls_grade_visibility(self):
        self.canvas.assignment['post_manually'] = False
        result = await self.apply(await self.grade_plan())
        self.assertTrue(self.canvas.assignment['muted'])
        self.assertTrue(result['results'][0]['grade_readback']['student_visible'])
        review = await self.assistant.canvas_get_submission_review(7, 9, student_id=11)
        self.assertEqual(review['grade_posting']['posting_status'], 'posted')

    async def test_failed_readback_does_not_misreport_or_retry_accepted_grade(self):
        plan = await self.grade_plan()
        self.canvas.readback_error = True
        result = await self.apply(plan)
        self.assertEqual(result['applied'], 1)
        self.assertEqual(result['failed'], 0)
        readback = result['results'][0]['grade_readback']
        self.assertEqual(readback['readback_status'], 'unavailable')
        self.assertIsNone(readback['student_visible'])
        self.assertEqual(sum(c[0] == 'PUT' for c in self.canvas.calls), 1)

    async def test_anonymous_grade_update_keeps_anonymous_route_and_reports_visibility(self):
        plan = await self.assistant.canvas_plan_grade_change(7, 9, anonymous_id='synthetic-anon', posted_grade='5')
        result = await self.apply(plan)
        self.assertEqual(result['results'][0]['grade_readback']['student_visibility'], 'hidden')
        self.assertTrue(all('/anonymous_submissions/synthetic-anon' in c[1] for c in self.canvas.calls))
        self.assertNotIn('user_id', plan['preview']['grade_posting'])

    async def test_release_targets_only_hidden_selected_students_and_requires_readback(self):
        self.graded(); self.graded('12')
        self.canvas.submissions['12']['posted_at'] = '2026-09-16T09:00:00Z'
        plan = await self.posting.canvas_plan_grade_release(7, 9, [11, 12])
        self.assertFalse(any(c[0] == 'POST' for c in self.canvas.calls))
        pending = self.store._plans[plan['plan_token']]
        self.assertEqual(pending.mutations[0].json_data['variables']['input'], {
            'assignmentId': '9', 'onlyStudentIds': ['11'], 'gradedOnly': True})
        self.assertEqual(plan['preview']['skipped'], [{'student_id': '12', 'reason': 'already_visible'}])
        accepted = await self.apply(plan)
        self.assertEqual(accepted['status'], 'accepted')
        self.assertEqual(accepted['progress_id'], '80')
        self.assertFalse(accepted['student_visibility_verified'])
        status = await self.posting.canvas_get_grade_posting_status(7, 9, [11], 80)
        self.assertEqual(status['status'], 'pending')
        self.canvas.progress['workflow_state'] = 'completed'
        status = await self.posting.canvas_get_grade_posting_status(7, 9, [11], 80)
        self.assertEqual(status['status'], 'visibility_not_verified')
        self.canvas.submissions['11']['posted_at'] = '2026-09-16T10:00:00Z'
        status = await self.posting.canvas_get_grade_posting_status(7, 9, [11], 80)
        self.assertEqual(status['status'], 'completed')
        self.assertTrue(status['all_visible'])
        with self.assertRaisesRegex(ValueError, 'already been used'):
            await self.apply(plan)

    async def test_release_stale_grade_or_policy_blocks_write(self):
        self.graded()
        for change in ('grade', 'policy'):
            plan = await self.posting.canvas_plan_grade_release(7, 9, [11])
            if change == 'grade': self.canvas.submissions['11']['score'] = 3
            else: self.canvas.assignment['post_manually'] = False
            with self.assertRaisesRegex(ValueError, 'stale'):
                await self.apply(plan)
        self.assertFalse(any(c[0] == 'POST' for c in self.canvas.calls))

    async def test_graphql_errors_empty_ack_and_lost_response_never_report_completed(self):
        self.graded()
        for response, expected in [
            ({'errors': [{'message': 'Synthetic permission error'}]}, 'failed'),
            ({'data': {'postAssignmentGrades': None}, 'errors': [{'message': 'Synthetic execution error'}]}, 'uncertain'),
            ({'data': {'postAssignmentGrades': {'errors': [{'message': 'Synthetic validation error'}]}}}, 'failed'),
            ({'data': {'postAssignmentGrades': None}}, 'uncertain'),
            (CanvasAPIError(0, 'timeout', '/api/graphql', 'Synthetic timeout'), 'uncertain'),
            (CanvasAPIError(403, 'denied', '/api/graphql', 'Synthetic denied'), 'failed'),
        ]:
            with self.subTest(expected=expected, response=response):
                plan = await self.posting.canvas_plan_grade_release(7, 9, [11])
                self.canvas.response = response
                before = sum(c[0] == 'POST' for c in self.canvas.calls)
                result = await self.apply(plan)
                self.assertEqual(result['status'], expected)
                self.assertFalse(result['student_visibility_verified'])
                self.assertEqual(sum(c[0] == 'POST' for c in self.canvas.calls), before + 1)

    async def test_release_rejects_ungraded_unknown_unavailable_or_anonymous_targets(self):
        for update in ({}, {'score': 5, 'assignment_visible': False}, {'score': 5, 'posted_at': '2026-09-16T09:00:00Z'}):
            original = copy.deepcopy(self.canvas.submissions['11'])
            self.canvas.submissions['11'].update(update)
            with self.assertRaises(ValueError): await self.posting.canvas_plan_grade_release(7, 9, [11])
            self.canvas.submissions['11'] = original
        self.graded()
        for ids in ([], [11, '11'], [True], [0]):
            with self.assertRaises(ValueError): await self.posting.canvas_plan_grade_release(7, 9, ids)
        self.canvas.assignment['anonymous_grading'] = True
        with self.assertRaisesRegex(ValueError, 'anonymous'): await self.posting.canvas_plan_grade_release(7, 9, [11])
        self.canvas.assignment['anonymous_grading'] = False
        self.canvas.assignment['published'] = False
        with self.assertRaisesRegex(ValueError, 'Publish'): await self.posting.canvas_plan_grade_release(7, 9, [11])
        self.assertEqual(self.store._plans, {})

    async def test_status_checks_progress_scope_failure_and_unavailable_assignment(self):
        self.graded()
        self.canvas.submissions['11']['posted_at'] = '2026-09-16T10:00:00Z'
        self.canvas.progress['workflow_state'] = 'failed'
        result = await self.posting.canvas_get_grade_posting_status(7, 9, [11], 80)
        self.assertEqual(result['status'], 'failed')
        self.canvas.progress['context_id'] = 8
        with self.assertRaisesRegex(ValueError, 'requested course'):
            await self.posting.canvas_get_grade_posting_status(7, 9, [11], 80)
        self.canvas.assignment['published'] = False
        result = await self.posting.canvas_get_grade_posting_status(7, 9, [11])
        self.assertFalse(result['all_visible'])

    def test_missing_fields_and_zero_grade_are_not_confused(self):
        self.assertIsNone(grade_visibility({})['student_visible'])
        self.assertEqual(grade_visibility({'score': None, 'posted_at': None})['student_visibility'], 'no_grade')
        self.assertEqual(grade_visibility({'posted_at': None})['student_visibility'], 'unknown')
        self.assertTrue(grade_visibility({'score': 0, 'posted_at': '2026-09-16', 'assignment_visible': True})['student_visible'])
        self.assertIsNone(grade_visibility({'score': 5, 'posted_at': '2026-09-16'})['student_visible'])

    async def test_release_tools_are_discoverable_and_work_through_mcp_proxy(self):
        self.graded()
        async with Client(create_server()) as client:
            tools = await client.call_tool('canvas_search_tools', {'query': 'post release hidden grades student visibility'})
            names = {t['name'] for t in tools.data}
            self.assertIn('canvas_plan_grade_release', names)
            self.assertIn('canvas_get_grade_posting_status', names)
            result = await client.call_tool('canvas_call_tool', {'name': 'canvas_plan_grade_release',
                'arguments': {'course_id': 7, 'assignment_id': 9, 'student_ids': [11]}})
            applied = await client.call_tool('canvas_apply_change', {'plan_token': result.data['plan_token'], 'confirm': True})
            self.assertEqual(applied.data['status'], 'accepted')
            status = await client.call_tool('canvas_call_tool', {'name': 'canvas_get_grade_posting_status',
                'arguments': {'course_id': 7, 'assignment_id': 9, 'student_ids': [11], 'progress_id': '80'}})
            self.assertEqual(status.data['status'], 'pending')


if __name__ == '__main__': unittest.main()
