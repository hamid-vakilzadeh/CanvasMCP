"""Synthetic course-group CRUD, membership moves, pagination and MCP schemas."""

import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from action_plans import PlanStore
from canvas_client import AsyncCanvasClient, CanvasAPIError, encode_cursor, decode_cursor
from fastmcp import Client
from server import create_server
from tools.assistant import AssistantTools
from tools.groups import GroupTools
from test_assistant_plans import FakeMCP, FakeProgress


class SyntheticGroups:
    def __init__(self):
        self.calls = []
        self.category = {'id': 20, 'course_id': 42, 'context_type': 'Course', 'name': 'Synthetic projects',
                         'self_signup': 'enabled', 'auto_leader': 'first', 'group_limit': 4,
                         'self_signup_end_at': '2026-12-01T00:00:00Z', 'role': None}
        self.groups = {str(i): {'id': i, 'course_id': 42, 'context_type': 'Course',
            'group_category_id': 20, 'name': f'Synthetic group {i}', 'description': 'Synthetic description'} for i in (30, 31)}
        self.members = {str(i): [{'id': i + 100, 'group_id': i, 'user_id': i - 23,
                                 'workflow_state': 'accepted', 'moderator': False}] for i in (30, 31)}
        self.failures = []
        self.enrolled = {'7', '8', '9', '10'}
        self.collaborative = True
        self.page_error = False

    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass

    def payload(self, endpoint, params=None):
        path = urlsplit(endpoint).path
        page = int(parse_qs(urlsplit(endpoint).query).get('page', ['1'])[0])
        if path.endswith('/enrollments'):
            student = str(params['user_id'])
            return ([{'user_id': student, 'type': 'StudentEnrollment', 'enrollment_state': 'active'}]
                    if student in self.enrolled else []), False
        if path == '/api/v1/courses/42/group_categories':
            return ([self.category] if self.collaborative else []), False
        if path == '/api/v1/group_categories/20': return self.category, False
        if path in ('/api/v1/group_categories/20/groups', '/api/v1/courses/42/groups'):
            values = list(self.groups.values())
            return values[page - 1:page], page < len(values)
        group_id = path.split('/')[4]
        if path.endswith('/memberships'):
            values = self.members[group_id]
            return values[page - 1:page], page < len(values)
        if path.endswith('/users'):
            values = [{'id': r['user_id'], 'name': f"Synthetic student {r['user_id']}"} for r in self.members[group_id]]
            return values[page - 1:page], page < len(values)
        return self.groups[group_id], False

    async def get(self, endpoint, params=None):
        self.calls.append(('GET', endpoint, params))
        return copy.deepcopy(self.payload(endpoint, params)[0])

    async def page(self, endpoint, *, params=None, cursor=None, limit=50):
        self.calls.append(('PAGE', endpoint, params, cursor))
        url = decode_cursor(cursor) if cursor else endpoint
        if self.page_error and cursor:
            raise CanvasAPIError(403, 'denied', endpoint, 'Synthetic pagination failure')
        payload, more = self.payload(url, params)
        number = int(parse_qs(urlsplit(url).query).get('page', ['1'])[0])
        next_cursor = encode_cursor(f'https://canvas.example.invalid{endpoint}?page={number + 1}&per_page=100') if more else None
        return {'items': copy.deepcopy(payload), 'next_cursor': next_cursor, 'count': len(payload)}

    def fail(self):
        if self.failures:
            failure = self.failures.pop(0)
            if failure: raise failure

    async def post(self, endpoint, *, json_data=None, data=None):
        self.calls.append(('POST', endpoint, copy.deepcopy(json_data)))
        self.fail()
        if endpoint.endswith('/group_categories'):
            return {**self.category, **json_data, 'id': 21}
        if endpoint.endswith('/groups'):
            return {**self.groups['30'], **json_data, 'id': 32}
        group_id = endpoint.split('/')[4]
        user_id = int(json_data['user_id'])
        for peers in self.members.values():
            peers[:] = [m for m in peers if m['user_id'] != user_id]
        result = {'id': 200 + user_id, 'user_id': user_id, 'group_id': int(group_id), 'workflow_state': 'accepted'}
        self.members[group_id].append(result)
        return copy.deepcopy(result)

    async def put(self, endpoint, *, json_data=None, data=None):
        self.calls.append(('PUT', endpoint, copy.deepcopy(json_data)))
        self.fail()
        if endpoint.startswith('/api/v1/group_categories/'):
            self.category.update(json_data)
            return copy.deepcopy(self.category)
        group_id = endpoint.split('/')[4]
        if '/users/' in endpoint:
            member = next(m for m in self.members[group_id] if str(m['user_id']) == endpoint.split('/')[-1])
            member.update(json_data)
            return copy.deepcopy(member)
        self.groups[group_id].update(json_data)
        return copy.deepcopy(self.groups[group_id])

    async def delete(self, endpoint, params=None):
        self.calls.append(('DELETE', endpoint, params))
        self.fail()
        group_id, user_id = endpoint.split('/')[4], endpoint.split('/')[-1]
        self.members[group_id][:] = [m for m in self.members[group_id] if str(m['user_id']) != user_id]
        return {'ok': True}


class GroupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.canvas, self.store = SyntheticGroups(), PlanStore()
        for target in ('tools.groups.plan_store', 'tools.assistant.plan_store'):
            p = patch(target, self.store); p.start(); self.addCleanup(p.stop)
        p = patch.object(AsyncCanvasClient, 'from_environment', return_value=self.canvas)
        p.start(); self.addCleanup(p.stop)
        self.groups, self.assistant = GroupTools(FakeMCP()), AssistantTools(FakeMCP())

    async def apply(self, plan):
        return await self.assistant.canvas_apply_change(plan['plan_token'], True, FakeProgress())

    async def test_read_group_sets_groups_and_members_with_scoped_pagination(self):
        sets = await self.groups.canvas_list_group_sets(42)
        self.assertEqual(sets['items'][0]['id'], 20)
        first = await self.groups.canvas_list_groups(42, 20)
        second = await self.groups.canvas_list_groups(42, 20, first['next_cursor'])
        self.assertEqual([first['items'][0]['id'], second['items'][0]['id']], [30, 31])
        group = await self.groups.canvas_get_group(42, 30)
        self.assertEqual(group['items'][0]['name'], 'Synthetic student 7')
        memberships = await self.groups.canvas_get_group(42, 30, 'memberships')
        self.assertEqual(memberships['items'][0]['workflow_state'], 'accepted')
        details = await self.groups.canvas_get_group(42, 30, 'details')
        self.assertNotIn('items', details)
        with self.assertRaisesRegex(ValueError, 'different group collection'):
            await self.groups.canvas_get_group(42, 30, cursor=first['next_cursor'])

    async def test_create_group_set_and_group_are_read_only_plans_then_correct_routes(self):
        category = await self.groups.canvas_plan_group_set_change(42, 'create', {'name': 'Synthetic new set'})
        self.assertFalse(any(c[0] in {'POST', 'PUT'} for c in self.canvas.calls))
        self.assertEqual((await self.apply(category))['results'][0]['result']['id'], 21)
        plan = await self.groups.canvas_plan_group_change(42, 'create', {'name': 'Synthetic new group'}, group_set_id=20)
        mutation = self.store._plans[plan['plan_token']].mutations[0]
        self.assertEqual(mutation.endpoint, '/api/v1/group_categories/20/groups')
        self.assertEqual(mutation.json_data, {'name': 'Synthetic new group'})
        self.assertEqual((await self.apply(plan))['status'], 'completed')

    async def test_rename_group_set_preserves_all_reset_by_canvas_settings(self):
        plan = await self.groups.canvas_plan_group_set_change(42, 'update', {'name': 'Renamed set'}, group_set_id=20)
        sent = self.store._plans[plan['plan_token']].mutations[0].json_data
        self.assertEqual(sent, {'name': 'Renamed set', 'self_signup': 'enabled', 'auto_leader': 'first',
                                'group_limit': 4, 'self_signup_end_at': '2026-12-01T00:00:00Z'})
        self.assertEqual((await self.apply(plan))['status'], 'completed')
        self.assertEqual(self.canvas.category['self_signup'], 'enabled')
        with self.assertRaises(ValueError):
            await self.groups.canvas_plan_group_set_change(42, 'update', {'self_signup': None}, group_set_id=20)
        plan = await self.groups.canvas_plan_group_set_change(42, 'update',
            {'self_signup': None, 'group_limit': None, 'auto_leader': None}, group_set_id=20)
        self.assertIsNone(plan['preview']['settings_sent']['self_signup_end_at'])
        self.assertEqual((await self.apply(plan))['status'], 'completed')
        self.assertIsNone(self.canvas.category['self_signup'])

    async def test_edit_group_details_and_stale_guard(self):
        plan = await self.groups.canvas_plan_group_change(42, 'update',
            {'name': 'Synthetic renamed', 'description': ''}, group_id=30)
        self.canvas.groups['30']['name'] = 'Concurrent rename'
        with self.assertRaisesRegex(ValueError, 'stale'): await self.apply(plan)
        self.assertFalse(any(c[0] == 'PUT' for c in self.canvas.calls))
        plan = await self.groups.canvas_plan_group_change(42, 'update', {'description': ''}, group_id=30)
        self.assertEqual((await self.apply(plan))['status'], 'completed')
        self.assertEqual(self.canvas.groups['30']['description'], '')

    async def test_group_scope_and_tag_checks_prevent_wrong_context_writes(self):
        with self.assertRaisesRegex(ValueError, 'requested course'):
            await self.groups.canvas_plan_group_change(43, 'update', {'name': 'Wrong course'}, group_id=30)
        self.canvas.groups['30']['non_collaborative'] = True
        with self.assertRaisesRegex(ValueError, 'differentiation tags'):
            await self.groups.canvas_get_group(42, 30)
        self.canvas.collaborative = False
        with self.assertRaisesRegex(ValueError, 'collaborative course group set'):
            await self.groups.canvas_plan_group_set_change(42, 'update', {'name': 'Tag'}, group_set_id=20)
        self.assertEqual(self.store._plans, {})

    async def test_move_is_detected_across_pages_previewed_and_applied_without_bulk_replacement(self):
        with self.assertRaisesRegex(ValueError, 'allow_moves=true'):
            await self.groups.canvas_plan_group_membership_change(42, 30, 'add', [8])
        plan = await self.groups.canvas_plan_group_membership_change(42, 30, 'add', [7, 8], allow_moves=True)
        self.assertEqual(plan['preview']['changes'][0]['moves_from'], [{'group_id': '31', 'group_name': 'Synthetic group 31'}])
        self.assertEqual(plan['preview']['skipped'], [{'student_id': '7', 'reason': 'already_member'}])
        mutation = self.store._plans[plan['plan_token']].mutations[0]
        self.assertEqual(mutation.json_data, {'user_id': '8'})
        self.assertEqual((await self.apply(plan))['status'], 'completed')
        self.assertEqual({m['user_id'] for m in self.canvas.members['30']}, {7, 8})
        self.assertEqual(self.canvas.members['31'], [])

    async def test_remove_and_accept_existing_request_use_user_membership_routes(self):
        plan = await self.groups.canvas_plan_group_membership_change(42, 30, 'remove', [7, 9])
        self.assertEqual(plan['preview']['skipped'][0]['reason'], 'not_a_member')
        self.assertEqual((await self.apply(plan))['status'], 'completed')
        self.assertEqual(self.canvas.members['30'], [])
        self.canvas.members['30'] = [{'id': 99, 'group_id': 30, 'user_id': 9, 'workflow_state': 'requested'}]
        plan = await self.groups.canvas_plan_group_membership_change(42, 30, 'add', [9])
        mutation = self.store._plans[plan['plan_token']].mutations[0]
        self.assertEqual((mutation.method, mutation.endpoint, mutation.json_data),
                         ('PUT', '/api/v1/groups/30/users/9', {'workflow_state': 'accepted'}))
        self.assertEqual((await self.apply(plan))['status'], 'completed')

    async def test_changed_peer_membership_and_failed_pagination_block_all_writes(self):
        plan = await self.groups.canvas_plan_group_membership_change(42, 30, 'add', [9])
        self.canvas.members['31'].append({'id': 99, 'group_id': 31, 'user_id': 9, 'workflow_state': 'accepted'})
        with self.assertRaisesRegex(ValueError, 'stale'): await self.apply(plan)
        self.canvas.page_error = True
        with self.assertRaises(CanvasAPIError):
            await self.groups.canvas_plan_group_membership_change(42, 30, 'add', [10])
        self.assertFalse(any(c[0] in {'POST', 'PUT', 'DELETE'} for c in self.canvas.calls))
        self.assertEqual(self.store._plans, {})

    async def test_membership_errors_are_partial_or_uncertain_and_never_retried(self):
        for error, expected in [(CanvasAPIError(403, 'denied', '/synthetic', 'Synthetic denial'), 'failed'),
                                (CanvasAPIError(0, 'timeout', '/synthetic', 'Synthetic lost response'), 'uncertain')]:
            self.canvas.members['30'] = self.canvas.members['30'][:1]
            plan = await self.groups.canvas_plan_group_membership_change(42, 30, 'add', [9, 10])
            self.canvas.failures = [None, error]
            count = sum(c[0] == 'POST' for c in self.canvas.calls)
            result = await self.apply(plan)
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result[expected], 1)
            self.assertEqual(sum(c[0] == 'POST' for c in self.canvas.calls), count + 2)
            with self.assertRaisesRegex(ValueError, 'already been used'): await self.apply(plan)

    async def test_noop_invalid_arguments_unenrolled_students_and_unsupported_fields(self):
        for changes in ({}, {'name': ' '}, {'name': 'Valid', 'members': [7]}, {'name': None}):
            with self.assertRaises(ValueError): await self.groups.canvas_plan_group_change(42, 'create', changes, group_set_id=20)
        with self.assertRaises(ValueError):
            await self.groups.canvas_plan_group_set_change(42, 'create', {'name': 'Test', 'group_limit': 4})
        for students in ([7], [7, '7'], [], [True], [999]):
            with self.assertRaises(ValueError): await self.groups.canvas_plan_group_membership_change(42, 30, 'add', students)
        self.assertEqual(self.store._plans, {})

    async def test_mcp_discovery_and_native_nested_changes(self):
        async with Client(create_server()) as client:
            for query, name in [('create edit group sets', 'canvas_plan_group_set_change'),
                                ('student project groups create edit', 'canvas_plan_group_change'),
                                ('group members memberships add remove', 'canvas_plan_group_membership_change')]:
                found = await client.call_tool('canvas_search_tools', {'query': query})
                self.assertIn(name, {item['name'] for item in found.data})
            plan = await client.call_tool('canvas_call_tool', {'name': 'canvas_plan_group_set_change',
                'arguments': {'course_id': 42, 'operation': 'update', 'group_set_id': 20,
                              'changes': {'self_signup': None, 'group_limit': None}}})
            applied = await client.call_tool('canvas_apply_change', {'plan_token': plan.data['plan_token'], 'confirm': True})
            self.assertEqual(applied.data['status'], 'completed')
            self.assertIsNone(self.canvas.category['self_signup'])
            invalid = await client.call_tool('canvas_call_tool', {'name': 'canvas_plan_group_set_change',
                'arguments': {'course_id': 42, 'operation': 'create',
                              'changes': {'name': 'Synthetic', 'self_signup': 'enabled', 'group_limit': True}}}, raise_on_error=False)
            self.assertTrue(invalid.is_error)


if __name__ == '__main__': unittest.main()
