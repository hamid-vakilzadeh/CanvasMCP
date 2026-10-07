"""Synthetic Classic bank authoring, import, discovery and safety contracts."""

import copy
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch
import xml.etree.ElementTree as ET
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fastmcp import Client
from action_plans import PlanStore
from canvas_client import AsyncCanvasClient, CanvasAPIError, encode_cursor
from server import create_server
from tools.assistant import AssistantTools
from tools.question_banks import BankQuestion, QuestionBankTools, QTI_NS, qti_archive, upload_qti
from test_assistant_plans import FakeMCP, FakeProgress
from test_canvas_client import FakeHTTPClient, response


ESSAY = {'question_name': 'Synthetic explanation', 'question_text': '<p>Explain this synthetic example.</p>',
         'question_type': 'essay_question', 'points_possible': 2}
CHOICE = {'question_name': 'Synthetic choice', 'question_text': '<p>Choose A &amp; explain.</p>',
          'question_type': 'multiple_choice_question',
          'answers': [{'text': 'Option A', 'correct': True}, {'text': 'Option B', 'correct': False}]}


class BankCanvas:
    def __init__(self):
        self.calls = []
        self.bank = {'id': 9, 'context_id': 42, 'context_type': 'Course', 'title': 'Synthetic bank',
                     'assessment_question_count': 3, 'workflow_state': 'active'}
        self.banks = [self.bank]
        self.quiz = {'id': 21, 'quiz_type': 'practice_quiz', 'published': False}
        self.migration = {'id': 31, 'migration_type': 'qti_converter', 'workflow_state': 'running',
                          'user_id': 'SYNTHETIC_PRIVATE_SENTINEL',
                          'pre_attachment': {'upload_url': 'https://storage.example.invalid/upload?secret=synthetic',
                                             'upload_params': {'key': 'synthetic-storage-key'}}}
        self.group_result = None
        self.post_error = None
        self.next_bank_page = None

    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass

    async def get(self, endpoint, params=None):
        self.calls.append(('GET', endpoint, params))
        if endpoint == '/api/v1/question_banks/9': return copy.deepcopy(self.bank)
        if endpoint == '/api/v1/courses/42/quizzes/21': return copy.deepcopy(self.quiz)
        if endpoint == '/api/v1/courses/42/content_migrations/31': return copy.deepcopy(self.migration)
        raise AssertionError('Unexpected read endpoint')

    async def page(self, endpoint, *, params=None, cursor=None, limit=50, preserve_overflow=False):
        self.calls.append(('PAGE', endpoint, params, cursor, preserve_overflow))
        if endpoint == '/api/v1/question_banks':
            assert preserve_overflow
            return {'items': copy.deepcopy(self.next_bank_page if cursor else self.banks),
                    'next_cursor': encode_cursor('https://canvas.example.invalid/api/v1/question_banks?context_type=Course&context_id=42&page=2')
                        if self.next_bank_page is not None and not cursor else None}
        if endpoint == '/api/v1/question_banks/9/questions':
            return {'items': [{'id': 7, **ESSAY}], 'next_cursor': None}
        if endpoint.endswith('/migration_issues'):
            return {'items': [{'id': 1, 'issue_type': 'warning', 'workflow_state': 'active',
                               'description': 'Synthetic import warning', 'user_id': 'SYNTHETIC_PRIVATE_SENTINEL'}], 'next_cursor': None}
        raise AssertionError('Unexpected collection endpoint')

    async def post(self, endpoint, *, data=None, json_data=None):
        self.calls.append(('POST', endpoint, data, json_data))
        if self.post_error: raise self.post_error
        if endpoint.endswith('/content_migrations'): return copy.deepcopy(self.migration)
        if endpoint.endswith('/groups'):
            return self.group_result if self.group_result is not None else {'quiz_groups': [{'id': 11, **json_data['quiz_groups'][0]}]}
        raise AssertionError('Unexpected write endpoint')


class QuestionBankTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.canvas, self.store = BankCanvas(), PlanStore()
        for p in (patch.object(AsyncCanvasClient, 'from_environment', return_value=self.canvas),
                  patch('tools.question_banks.plan_store', self.store), patch('tools.assistant.plan_store', self.store),
                  patch.dict(os.environ, {'FERPA': 'false'})):
            p.start(); self.addCleanup(p.stop)
        self.tools, self.assistant = QuestionBankTools(FakeMCP()), AssistantTools(FakeMCP())

    async def apply(self, plan):
        return await self.assistant.canvas_apply_change(plan['plan_token'], True, progress=FakeProgress())

    async def test_discovery_native_arguments_and_apply_with_both_ferpa_modes(self):
        for enabled in ('false', 'true'):
            with patch.dict(os.environ, {'FERPA': enabled}), patch('tools.question_banks.upload_qti', new_callable=AsyncMock):
                async with Client(create_server()) as client:
                    for query, expected in (
                        ('create standalone question bank import', 'canvas_plan_question_bank_import'),
                        ('list question banks', 'canvas_list_question_banks'),
                        ('read bank questions', 'canvas_get_question_bank'),
                        ('bank import migration status', 'canvas_get_question_bank_import'),
                        ('random draw bank group', 'canvas_plan_question_bank_draw')):
                        found = await client.call_tool('canvas_search_tools', {'query': query})
                        self.assertIn(expected, {t['name'] for t in found.data})
                    plan = await client.call_tool('canvas_call_tool', {'name': 'canvas_plan_question_bank_import',
                        'arguments': {'course_id': 42, 'bank_id': 9, 'questions': [CHOICE, ESSAY]}})
                    result = await client.call_tool('canvas_apply_change', {'plan_token': plan.data['plan_token'], 'confirm': True})
                    self.assertEqual(result.data['status'], 'accepted')
                    self.assertNotIn('secret=', json.dumps(result.data))
                    self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL', json.dumps(result.data))

    async def test_invalid_question_payloads_never_create_plans(self):
        invalid = [{**ESSAY, 'answers': CHOICE['answers']}, {**CHOICE, 'answers': []},
            {**CHOICE, 'answers': [dict(a, correct=True) for a in CHOICE['answers']]},
            {**CHOICE, 'question_type': 'true_false_question'}, {**ESSAY, 'question_type': 'matching_question'},
            {**ESSAY, 'points_possible': float('nan')}, {**ESSAY, 'points_possible': True},
            {**ESSAY, 'student_id': 7}, {**ESSAY, 'question_text': '\x00'}, {**ESSAY, 'question_name': ' '},
            {**ESSAY, 'question_text': '\ufffe'}, {**ESSAY, 'question_text': 'x' * 16001}]
        for question in invalid:
            with self.subTest(question=question), self.assertRaises(ValueError):
                await self.tools.canvas_plan_question_bank_import(42, [question], bank_id=9)
        for args in ({}, {'bank_id': 9, 'bank_name': 'New'}, {'bank_name': ' '}):
            with self.assertRaises(ValueError): await self.tools.canvas_plan_question_bank_import(42, [ESSAY], **args)
        with self.assertRaises(ValueError): await self.tools.canvas_plan_question_bank_import(42, [], bank_id=9)
        self.assertFalse(self.store._plans)
        self.assertFalse(any(c[0] == 'POST' for c in self.canvas.calls))

    async def test_bank_scope_and_cursor_restrictions(self):
        for context in ({'context_id': 43}, {'context_type': 'Account'}, {'id': 10}, {'workflow_state': 'deleted'}):
            original = self.canvas.bank.copy()
            self.canvas.bank.update(context)
            with self.assertRaises(ValueError): await self.tools.canvas_get_question_bank(42, 9)
            self.canvas.bank = original
        cursor = encode_cursor('https://canvas.example.invalid/api/v1/question_banks?context_type=Course&context_id=43&page=2')
        with self.assertRaises(ValueError): await self.tools.canvas_list_question_banks(42, cursor)
        result = await self.tools.canvas_get_question_bank(42, 9, include_questions=True)
        self.assertEqual(result['items'][0]['question_name'], ESSAY['question_name'])

    async def test_name_collision_checks_every_page_and_rechecks_at_apply(self):
        self.canvas.next_bank_page = [{**self.canvas.bank, 'id': 10, 'title': 'New bank'}]
        with self.assertRaisesRegex(ValueError, 'already exists'):
            await self.tools.canvas_plan_question_bank_import(42, [ESSAY], bank_name='New bank')
        self.canvas.next_bank_page = None
        plan = await self.tools.canvas_plan_question_bank_import(42, [ESSAY], bank_name='New bank')
        self.canvas.banks.append({**self.canvas.bank, 'id': 10, 'title': 'New bank'})
        with self.assertRaisesRegex(ValueError, 'already exists'): await self.apply(plan)
        self.assertFalse(any(c[0] == 'POST' for c in self.canvas.calls))

    async def test_create_and_append_use_distinct_default_bank_settings(self):
        for target, key in (({'bank_name': 'New synthetic bank'}, 'name'), ({'bank_id': 9}, 'id')):
            plan = await self.tools.canvas_plan_question_bank_import(42, [ESSAY], **target)
            with patch('tools.question_banks.upload_qti', new_callable=AsyncMock) as upload:
                result = await self.apply(plan)
            self.assertEqual(result['status'], 'accepted')
            self.assertEqual(result['migration_id'], '31')
            data = next(c[2] for c in reversed(self.canvas.calls) if c[0] == 'POST')
            self.assertIn(f'settings[question_bank_{key}]', data)
            self.assertEqual(data['migration_type'], 'qti_converter')
            self.assertEqual(data['pre_attachment[size]'], len(upload.call_args.args[1]))
            with self.assertRaisesRegex(ValueError, 'already been used'): await self.apply(plan)

    async def test_stale_bank_and_quiz_reject_before_writing(self):
        plan = await self.tools.canvas_plan_question_bank_import(42, [ESSAY], bank_id=9)
        self.canvas.bank['title'] = 'Changed'
        with self.assertRaisesRegex(ValueError, 'stale'): await self.apply(plan)
        plan = await self.tools.canvas_plan_question_bank_draw(42, 21, 9, 'Synthetic draw', 2, 1)
        self.canvas.quiz['published'] = True
        with self.assertRaisesRegex(ValueError, 'stale'): await self.apply(plan)
        self.assertFalse(any(c[0] == 'POST' for c in self.canvas.calls))

    async def test_upload_failure_retains_migration_id_and_hides_signed_url(self):
        plan = await self.tools.canvas_plan_question_bank_import(42, [ESSAY], bank_id=9)
        with patch('tools.question_banks.upload_qti', side_effect=RuntimeError('https://storage.example.invalid/?secret=synthetic')):
            result = await self.apply(plan)
        self.assertEqual(result['status'], 'uncertain')
        self.assertEqual(result['migration_id'], '31')
        self.assertNotIn('secret=', json.dumps(result))
        self.assertEqual(sum(c[0] == 'POST' for c in self.canvas.calls), 1)

    async def test_request_failures_do_not_retry_or_claim_completion(self):
        for error, status in ((CanvasAPIError(403, 'denied', '/synthetic', 'Denied'), 'failed'),
                              (TimeoutError('synthetic'), 'uncertain')):
            self.canvas.post_error = error
            plan = await self.tools.canvas_plan_question_bank_import(42, [ESSAY], bank_id=9)
            result = await self.apply(plan)
            self.assertEqual(result['status'], status)
            self.assertIn('list_content_migrations', result['next_step'])

    async def test_migration_status_reports_warnings_not_verified_bank_completion(self):
        self.canvas.migration['workflow_state'] = 'completed'
        result = await self.tools.canvas_get_question_bank_import(42, 31)
        self.assertEqual(result['workflow_state'], 'completed')
        self.assertFalse(result['bank_verified'])
        self.assertEqual(result['issues'][0]['issue_type'], 'warning')
        self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL', json.dumps(result))

    async def test_draw_capacity_quiz_engine_and_silent_link_rejection(self):
        with self.assertRaises(ValueError): await self.tools.canvas_plan_question_bank_draw(42, 21, 9, 'Draw', 4, 1)
        self.canvas.quiz['quiz_type'] = 'quizzes.next'
        with self.assertRaises(ValueError): await self.tools.canvas_plan_question_bank_draw(42, 21, 9, 'Draw', 1, 1)
        self.canvas.quiz['quiz_type'] = 'practice_quiz'
        plan = await self.tools.canvas_plan_question_bank_draw(42, 21, 9, 'Draw', 2, 1.0)
        self.assertEqual((await self.apply(plan))['status'], 'completed')
        self.canvas.group_result = {'quiz_groups': [{'id': 11, 'name': 'Draw', 'pick_count': 2,
                                                     'question_points': 1, 'assessment_question_bank_id': None}]}
        plan = await self.tools.canvas_plan_question_bank_draw(42, 21, 9, 'Draw', 2, 1)
        self.assertEqual((await self.apply(plan))['status'], 'uncertain')


class QTIFormatTests(unittest.IsolatedAsyncioTestCase):
    def test_bank_only_package_preserves_html_scoring_types_and_unique_question_ids(self):
        true_false = {**CHOICE, 'question_type': 'true_false_question',
                      'answers': [{'text': 'True', 'correct': False}, {'text': 'False', 'correct': True}]}
        inputs = [CHOICE, true_false, ESSAY, {**ESSAY, 'question_type': 'file_upload_question'}]
        data = [BankQuestion.model_validate(q).model_dump() for q in inputs]
        roots = []
        for _ in range(2):
            with ZipFile(BytesIO(qti_archive(data, 'Synthetic bank'))) as archive:
                self.assertEqual(archive.namelist(), ['questions.xml', 'imsmanifest.xml'])
                manifest = ET.fromstring(archive.read('imsmanifest.xml'))
                resource = manifest.find('.//{*}resource')
                self.assertEqual(resource.attrib['href'], 'questions.xml')
                self.assertEqual(resource.attrib['type'], 'associatedcontent/imscc_xmlv1p1/learning-application-resource')
                roots.append(ET.fromstring(archive.read('questions.xml')))
        ns = {'q': QTI_NS}
        items = roots[0].findall('q:objectbank/q:item', ns)
        self.assertEqual(len(items), 4)
        self.assertIsNone(roots[0].find('.//q:assessment', ns))
        self.assertEqual(roots[0].find('.//q:fieldentry', ns).text, 'Synthetic bank')
        self.assertEqual(items[0].find('q:presentation/q:material/q:mattext', ns).text, CHOICE['question_text'])
        self.assertEqual(items[0].find('.//q:varequal', ns).text, '1')
        self.assertEqual(items[1].find('.//q:varequal', ns).text, '2')
        self.assertEqual(items[0].find('.//q:setvar', ns).text, '100')
        for item in items[2:]: self.assertIsNone(item.find('.//q:setvar', ns))
        self.assertNotEqual(items[0].attrib['ident'], roots[1].find('q:objectbank/q:item', ns).attrib['ident'])
        self.assertNotEqual(roots[0][0].attrib['ident'], roots[1][0].attrib['ident'])
        with ZipFile(BytesIO(qti_archive(data, 'Synthetic bank', append=True))) as archive:
            append_root = ET.fromstring(archive.read('questions.xml'))
        self.assertNotEqual(append_root[0].attrib['ident'], roots[0][0].attrib['ident'])
        self.assertTrue(append_root[0].attrib['ident'].startswith('i'))

    async def test_unpaginated_bank_index_does_not_lose_overflow(self):
        fake = FakeHTTPClient(get_result=response(200, url='https://canvas.example.invalid/api/v1/question_banks',
                                                 json=[{'id': i} for i in range(105)]))
        with patch('canvas_client.httpx2.AsyncClient', return_value=fake):
            async with AsyncCanvasClient('https://canvas.example.invalid', 'synthetic-token') as client:
                result = await client.page('/api/v1/question_banks', preserve_overflow=True, limit=100)
        self.assertEqual(result['count'], 105)
        self.assertEqual(len(result['items']), 105)
        self.assertIsNone(result['next_cursor'])

    async def test_upload_uses_separate_client_without_canvas_token(self):
        uploader = AsyncMock()
        uploader.__aenter__.return_value = uploader
        uploader.post.return_value = response(201, url='https://storage.example.invalid/upload', json={'id': 1})
        with patch('tools.question_banks.httpx2.AsyncClient', return_value=uploader) as factory:
            await upload_qti({'upload_url': 'https://storage.example.invalid/upload', 'upload_params': {'key': 'test'}}, b'zip')
        self.assertNotIn('headers', factory.call_args.kwargs)
        self.assertEqual(uploader.post.call_args.kwargs['files']['file'][1], b'zip')
        for url in ('http://storage.example.invalid/upload', 'https://user:secret@storage.example.invalid/upload', None):
            with self.assertRaises(ValueError): await upload_qti({'upload_url': url}, b'zip')


if __name__ == '__main__': unittest.main()
