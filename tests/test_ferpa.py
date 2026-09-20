"""Synthetic end-to-end checks for opt-in student-record exposure."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from fastmcp import Client
from action_plans import Mutation, plan_store
from canvas_client import AsyncCanvasClient, encode_cursor
from canvasAPI import base
from ferpa import AUTHORING_TOOLS, ferpa_enabled
from tools.base import validate_and_convert_params
from httpx2 import AsyncClient, ASGITransport
from reporting.tools import DashboardRequest, dashboard_request
from reporting.web import create_dashboard_app, start_dashboard
from discussion_watch import run_watcher
from server import DIRECT_WRITE_TOOLS, create_server
from test_canvas_client import FakeHTTPClient, response


class FerpaConfigTests(unittest.TestCase):
    def test_string_collection_conversion_remains_available_without_executing_expressions(self):
        with patch.dict(os.environ, {'FERPA': 'false'}):
            self.assertEqual(validate_and_convert_params(value="[1, {'key': 'text'}]"),
                             {'value':[1, {'key':'text'}]})
            expression = "__import__('builtins').print('synthetic execution marker')"
            with patch('builtins.print') as executed:
                self.assertEqual(validate_and_convert_params(value=expression), {'value':expression})
            executed.assert_not_called()
        with patch.dict(os.environ, {'FERPA':'true'}):
            self.assertEqual(validate_and_convert_params(value='1 + 2'), {'value':3})

    def test_default_false_true_false_and_invalid_settings(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ferpa_enabled())
        for value, expected in [('true', True), (' TRUE ', True), ('false', False), ('False', False)]:
            with self.subTest(value=value), patch.dict(os.environ, {'FERPA': value}):
                self.assertEqual(ferpa_enabled(), expected)
        for value in ('', '1', 'yes', 'treu'):
            with self.subTest(value=value), patch.dict(os.environ, {'FERPA': value}):
                with self.assertRaisesRegex(ValueError, 'FERPA must be true or false'):
                    create_server()

    def test_cli_reports_disabled_workflows_and_invalid_configuration(self):
        for args, value, message in [([], 'invalid', 'FERPA must'),
                                     (['dashboard', '--no-open'], 'false', 'FERPA=true'),
                                     (['watch', '--once'], 'false', 'FERPA=true')]:
            env = {**os.environ, 'FERPA': value, 'CANVAS_URL': 'https://canvas.example.invalid',
                   'CANVAS_ACCESS_TOKEN': 'synthetic-token'}
            run = subprocess.run([sys.executable, str(ROOT/'src/local.py'), *args],
                                 env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, '')
            self.assertIn(message, run.stderr)
            self.assertNotIn('synthetic-token', run.stderr)


class FerpaBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'FERPA': 'false'})
        env.start(); self.addCleanup(env.stop)

    async def test_catalog_discovery_and_direct_calls_exclude_all_unapproved_tools(self):
        server = create_server()
        registered = {t.name for t in await server._local_provider.list_tools()}
        blocked = registered - AUTHORING_TOOLS
        self.assertTrue(DIRECT_WRITE_TOOLS <= blocked)
        for name in blocked:
            self.assertIsNone(await server.get_tool(name), name)
        async with Client(server) as client:
            listed = {t.name for t in await client.list_tools()}
            self.assertEqual(len(listed), 14)
            self.assertTrue(listed <= AUTHORING_TOOLS | {'canvas_search_tools', 'canvas_call_tool'})
            for query in ('student grades submissions', 'quiz uploaded images', 'discussion entries inbox',
                          'learning review report dashboard', 'student accommodations groups'):
                found = await client.call_tool('canvas_search_tools', {'query': query})
                self.assertTrue({t['name'] for t in found.data} <= AUTHORING_TOOLS)
            with patch('canvas_client.AsyncCanvasClient.from_environment') as network:
                for name in ('canvas_get_submission_review', 'canvas_plan_grade_change',
                             'canvas_get_student_report', 'canvas_dashboard_data', 'get_file',
                             'canvas_read_quiz_attachment', 'canvas_read_discussion_attachment'):
                    for tool, args in [(name, {}), ('canvas_call_tool', {'name': name, 'arguments': {}})]:
                        result = await client.call_tool(tool, args, raise_on_error=False)
                        self.assertTrue(result.is_error, name)
                network.assert_not_called()

    async def test_resources_prompts_and_capability_guidance_match_restricted_mode(self):
        async with Client(create_server()) as client:
            self.assertEqual({p.name for p in await client.list_prompts()}, {'build_canvas_course'})
            templates = {t.uri_template for t in await client.list_resource_templates()}
            self.assertEqual(templates, {'canvas://courses/{course_id}/overview', 'canvas://reference/actions/{domain}'})
            resources = {str(r.uri) for r in await client.list_resources()}
            self.assertNotIn('ui://canvas/student-dashboard.html', resources)
            for uri in ('canvas://courses/42/students/7/snapshot', 'canvas://courses/42/students/7/report'):
                with self.assertRaises(Exception):
                    await client.read_resource(uri)
            caps = (await client.call_tool('canvas_capabilities')).data
            self.assertFalse(caps['FERPA'])
            self.assertNotIn('canvas_plan_grade_change', caps['visible_tools'])
            grading = await client.read_resource('canvas://reference/actions/grading')
            self.assertEqual(json.loads(grading[0].text)['available_tools'], [])

    async def test_mixed_tool_arguments_rejected_before_any_canvas_request(self):
        attempts = [
            ('get_course', {'course_id':42, 'include_total_scores':True}),
            ('get_course', {'course_id':42, 'include_current_grading_period_scores':True}),
            ('list_assignments', {'course_id':42, 'include':['submission']}),
            ('list_assignment_groups', {'course_id':42, 'include':['submission']}),
            ('list_modules', {'course_id':42, 'student_id':7}),
            ('list_quiz_questions', {'course_id':42, 'quiz_id':21, 'quiz_submission_id':30}),
            ('list_files', {'context_type':'users', 'context_id':7}),
            ('get_folder', {'folder_id':'../files/101'}),
            ('canvas_plan_advanced_action', {'action':'set_assignment_extensions', 'course_id':42,
                                            'arguments':{'assignment_id':50,'extensions':[{'user_id':7}]}}),
            ('canvas_plan_assignment_change', {'course_id':42, 'operation':'update', 'assignment_id':50,
                                                'changes':{'assignment[submission][posted_grade]':'5'}}),
        ]
        async with Client(create_server()) as client:
            with patch('canvasAPI.base.requests.request') as sync, patch('canvas_client.AsyncCanvasClient.from_environment') as async_client:
                for name, arguments in attempts:
                    with self.subTest(name=name):
                        result = await client.call_tool('canvas_call_tool', {'name':name,'arguments':arguments}, raise_on_error=False)
                        self.assertTrue(result.is_error, result)
                sync.assert_not_called(); async_client.assert_not_called()

    async def test_ordinary_assignment_read_strips_nested_student_fields_but_keeps_authoring(self):
        raw = {'id':50,'name':'Synthetic assignment','points_possible':10,'grading_type':'points',
               'submission':{'body':'Synthetic response','score':8},
               'nested':{'enrollments':[{'grades':{'current_score':80}}], 'score_statistics':{'mean':80}},
               'rubric':[{'id':'criterion','points':10,'description':'Synthetic criterion'}]}
        original = copy.deepcopy(raw)
        with patch('tools.assignments.get_canvas_credentials', return_value=('https://canvas.example.invalid','synthetic-token')):
            with patch('tools.assignments.assignments.get_assignment', return_value=raw):
                async with Client(create_server()) as client:
                    result = await client.call_tool('canvas_call_tool', {'name':'get_assignment', 'arguments':{'course_id':42,'assignment_id':50}})
        self.assertEqual(result.data['points_possible'],10)
        self.assertEqual(result.data['rubric'][0]['points'],10)
        self.assertNotIn('submission',result.data)
        self.assertEqual(result.data['nested'],{})
        self.assertEqual(raw,original)

    async def test_forged_cursors_and_encoded_private_routes_are_blocked_before_http(self):
        fake=FakeHTTPClient()
        with patch('canvas_client.httpx2.AsyncClient',return_value=fake):
            client=AsyncCanvasClient('https://canvas.example.invalid','synthetic-token')
            for url in ('https://canvas.example.invalid/api/v1/courses/42/students/submissions',
                        'https://canvas.example.invalid/api/v1/courses?include[]=total_scores',
                        'https://canvas.example.invalid/api/v1/courses?as_user_id=7'):
                with self.assertRaises(ValueError):
                    await client.page('/api/v1/courses',cursor=encode_cursor(url))
            for path in ('/api/v1/courses/42/assignments/50/%73ubmissions/7','/api/graphql',
                         '/api/v1/folders/../files/101', '/api/v1/files/101'):
                with self.assertRaises(ValueError): await client.get(path)
            self.assertEqual(fake.get_calls,[]); self.assertEqual(fake.request_calls,[])
        with patch('canvasAPI.base.requests.request') as network:
            with self.assertRaises(ValueError):
                base._make_request('https://canvas.example.invalid','synthetic-token','GET',
                                   '/api/v1/courses/42/assignments/50', params={'include[]':['submission']})
            network.assert_not_called()

    async def test_allowed_pagination_and_response_redaction(self):
        url='https://canvas.example.invalid/api/v1/courses?page=2'
        fake=FakeHTTPClient(get_result=response(200,url=url,json=[{'id':42,'name':'Synthetic course',
                                                                 'enrollments':[{'grades':{'current_score':80}}]}]))
        with patch('canvas_client.httpx2.AsyncClient',return_value=fake):
            client=AsyncCanvasClient('https://canvas.example.invalid','synthetic-token')
            page=await client.page('/api/v1/courses',cursor=encode_cursor(url))
        self.assertEqual(page['items'],[{'id':42,'name':'Synthetic course'}])
        self.assertEqual(len(fake.get_calls),1)

    async def test_private_saved_plan_cannot_be_applied_in_restricted_mode(self):
        plan=await plan_store.create(action='grade_change',summary='Synthetic grade',preview={},
                                    mutations=[Mutation('PUT','/api/v1/courses/42/assignments/50/submissions/7',data={'submission[posted_grade]':'5'})])
        with patch('canvas_client.AsyncCanvasClient.from_environment') as network:
            async with Client(create_server()) as client:
                result=await client.call_tool('canvas_apply_change',{'plan_token':plan['plan_token'],'confirm':True},raise_on_error=False)
        self.assertTrue(result.is_error); network.assert_not_called()

    async def test_authoring_plan_and_apply_still_work(self):
        fake=AsyncMock()
        fake.__aenter__.return_value=fake
        fake.post.return_value={'page_id':11,'title':'Synthetic page','body':'<p>Synthetic authoring</p>'}
        with patch('canvas_client.AsyncCanvasClient.from_environment',return_value=fake):
            async with Client(create_server()) as client:
                plan=await client.call_tool('canvas_plan_page_change',{'course_id':42,'operation':'create',
                                         'changes':{'title':'Synthetic page','body':'<p>Synthetic authoring</p>'}})
                result=await client.call_tool('canvas_apply_change',{'plan_token':plan.data['plan_token'],'confirm':True})
        self.assertEqual(result.data['status'],'completed'); fake.post.assert_awaited_once()

    async def test_dashboard_cached_exports_and_watcher_cannot_bypass_flag(self):
        service=Mock()
        for action in ('report','list_reviews','export_review'):
            with self.assertRaisesRegex(ValueError,'FERPA=true'):
                await dashboard_request(DashboardRequest(action=action,course_id='42',student_id='7',job_id='synthetic'), service)
        with self.assertRaisesRegex(ValueError,'FERPA=true'): await start_dashboard(service)
        with self.assertRaisesRegex(ValueError,'FERPA=true'): await run_watcher(service,once=True)
        service.assert_not_called()
        self.assertEqual(service.mock_calls,[])

    async def test_local_browser_api_rejects_cached_report_export(self):
        service = Mock()
        app = create_dashboard_app(service, port=8765, bootstrap_secret='synthetic-bootstrap')
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://127.0.0.1:8765') as client:
            headers = {'Origin':'http://127.0.0.1:8765', 'X-Canvas-Dashboard':'1'}
            await client.post('/session', headers=headers, json={'secret':'synthetic-bootstrap'})
            result = await client.post('/api', headers=headers, json={'action':'export_review', 'job_id':'synthetic'})
        self.assertEqual(result.status_code, 400)
        self.assertIn('FERPA=true', result.json()['error'])
        self.assertEqual(service.mock_calls, [])

    async def test_enabled_catalog_and_records_are_unchanged_and_policy_is_per_server(self):
        restricted=create_server()
        with patch.dict(os.environ,{'FERPA':'true'}): enabled=create_server()
        async with Client(enabled) as client, Client(restricted) as limited:
            tools={t.name for t in await client.list_tools()}
            self.assertIn('canvas_get_submission_review',tools)
            self.assertIn('canvas_dashboard_data',tools)
            self.assertTrue((await client.call_tool('canvas_capabilities')).data['FERPA'])
            self.assertFalse((await limited.call_tool('canvas_capabilities')).data['FERPA'])
            fake=AsyncMock(); fake.__aenter__.return_value=fake
            fake.get.return_value={'score':8,'submission_history':[{'body':'Synthetic response'}]}
            with patch('canvas_client.AsyncCanvasClient.from_environment',return_value=fake):
                record=await client.call_tool('canvas_get_submission_review',{'course_id':42,'assignment_id':50,'student_id':7})
            self.assertIn('Synthetic response',json.dumps(record.data))
            self.assertIn('score',json.dumps(record.data))


if __name__=='__main__': unittest.main()
