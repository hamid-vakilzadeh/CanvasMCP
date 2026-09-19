"""Synthetic attachment association, extraction, pagination and MCP workflows."""

import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from canvas_client import AsyncCanvasClient, CanvasAPIError
from fastmcp import Client
from reporting.documents import MAX_FILE_BYTES
from server import create_server
from tools.attachments import AttachmentTools, AssignmentFileLinks
from test_assistant_plans import FakeMCP


class SyntheticAttachments:
    base_url = 'https://canvas.example.invalid'
    access_token = 'synthetic-canvas-token'

    def __init__(self):
        self.calls = []
        self.file = {'id': 100, 'display_name': 'Synthetic worksheet.csv', 'filename': 'worksheet.csv',
                     'content-type': 'text/csv', 'size': 31,
                     'url': self.base_url + '/files/100/download?verifier=synthetic-private-verifier'}
        self.old_file = {**self.file, 'id': 101, 'display_name': 'Synthetic prior work.csv',
                         'url': self.base_url + '/files/101/download'}
        self.submission = {'id': 91, 'assignment_id': 50, 'user_id': 7, 'anonymous_id': 'anon-test',
                           'attempt': 2, 'attachments': [self.file],
                           'submission_history': [{'attempt': 1, 'attachments': [self.old_file]}]}
        self.assignment = {'id': 50, 'description': '<a href="/courses/42/files/100/download?wrap=1">Worksheet</a>'}
        self.failure = None

    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass

    async def get(self, endpoint, params=None):
        self.calls.append((endpoint, params))
        if self.failure:
            raise self.failure
        if '/submissions/' in endpoint or '/anonymous_submissions/' in endpoint:
            value = self.submission
        elif '/files/' in endpoint:
            value = self.file
        else:
            value = self.assignment
        return copy.deepcopy(value)


class AssignmentAttachmentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.canvas = SyntheticAttachments()
        p = patch.object(AsyncCanvasClient, 'from_environment', return_value=self.canvas)
        p.start(); self.addCleanup(p.stop)
        self.download = AsyncMock(return_value=b'Category,Amount\nSynthetic,12.50\n')
        p = patch('tools.attachments.download_attachment', self.download)
        p.start(); self.addCleanup(p.stop)
        self.attachments = AttachmentTools(FakeMCP())

    async def read(self, file_id=100, **kwargs):
        return await self.attachments.canvas_read_assignment_attachment(42, 50, file_id, student_id=7, **kwargs)

    async def test_real_isolated_csv_extraction_with_source_locations(self):
        inventory = await self.attachments.canvas_list_assignment_attachments(42, 50, student_id=7)
        self.assertEqual(inventory['files'][0]['file_id'], '100')
        self.assertEqual(inventory['resolved_attempt'], 2)
        self.assertNotIn('url', inventory['files'][0])
        result = await self.read()
        self.assertTrue(result['extraction_complete'])
        self.assertTrue(result['all_content_returned'])
        self.assertIsNone(result['next_cursor'])
        self.assertIn('[row 2]\nSynthetic | 12.50', result['chunks'][0]['text'])
        self.assertEqual(len(result['sha256']), 64)
        self.assertEqual(self.download.call_args.args, (self.canvas.file, self.canvas.base_url, self.canvas.access_token))
        public = json.dumps(result)
        self.assertNotIn('verifier', public)
        self.assertNotIn(self.canvas.access_token, public)
        self.assertNotIn('url', public)
        self.assertIsNone(self.canvas.calls[-1][1])  # No unnecessary history download.

    async def test_instruction_files_resolve_only_through_scoped_api_metadata(self):
        self.canvas.assignment['description'] += (
            '<a data-api-endpoint="https://canvas.example.invalid/api/v1/courses/42/files/100" '
            'href="https://canvas.example.invalid/files/100?verifier=AUTHORED">duplicate</a>'
            '<a href="https://outside.example.invalid/files/999">external</a>'
            '<img src="/courses/999/files/102/preview">'
            '<a href="//canvas.example.invalid:443/files/103/download">same origin</a>')
        result = await self.attachments.canvas_list_assignment_attachments(42, 50, source='assignment')
        self.assertEqual([item['file_id'] for item in result['files']], ['100', '103'])
        self.assertEqual(len(self.canvas.calls), 1)
        result = await self.attachments.canvas_read_assignment_attachment(42, 50, 100, source='assignment')
        self.assertEqual(self.canvas.calls[-1][0], '/api/v1/courses/42/files/100')
        self.assertTrue(result['extraction_complete'])
        self.assertNotIn('AUTHORED', self.download.call_args.args[0]['url'])

    async def test_only_attached_file_and_selected_attempt_can_be_read(self):
        with self.assertRaisesRegex(ValueError, 'not attached'):
            await self.read(101)
        with self.assertRaisesRegex(ValueError, 'not attached'):
            await self.read(100, attempt=1)
        with self.assertRaisesRegex(ValueError, 'attempt is unavailable'):
            await self.read(attempt=3)
        self.download.assert_not_awaited()
        inventory = await self.attachments.canvas_list_assignment_attachments(42, 50, student_id=7, attempt=1)
        self.assertEqual(inventory['files'][0]['file_id'], '101')
        result = await self.read(101, attempt=1)
        self.assertEqual(result['resolved_attempt'], 1)
        self.assertEqual(self.canvas.calls[-1][1], {'include[]': ['submission_history']})
        self.assertEqual(self.download.call_args.args[0]['id'], 101)

    async def test_anonymous_review_uses_anonymous_endpoint_and_omits_identity(self):
        result = await self.attachments.canvas_list_assignment_attachments(42, 50, anonymous_id='anon-test')
        self.assertEqual(result['files'][0]['file_id'], '100')
        result = await self.attachments.canvas_read_assignment_attachment(42, 50, 100, anonymous_id='anon-test')
        self.assertTrue(all('/anonymous_submissions/anon-test' in call[0] for call in self.canvas.calls))
        self.assertNotIn('user_id', json.dumps(result))
        self.assertNotIn('student_id', json.dumps(result))

    async def test_pagination_reuses_snapshot_preserves_every_character_and_gap(self):
        text = 'synthetic-' * 3100
        parsed = {'segments': [{'location': 'page 1', 'text': text}],
                  'gaps': [{'location': 'page 2', 'reason': 'no_extractable_text_or_scanned_page'}], 'complete': False}
        with patch('tools.attachments.extract_isolated', AsyncMock(return_value=parsed)) as extract:
            result = await self.read()
            self.assertFalse(result['all_content_returned'])
            self.assertFalse(result['extraction_complete'])
            self.assertEqual(result['gap_reasons'], ['no_extractable_text_or_scanned_page'])
            chunks = result['chunks'][:]
            self.canvas.submission['attachments'] = []  # Subsequent pages describe the same frozen read.
            while result['next_cursor']:
                result = await self.read(cursor=result['next_cursor'])
                chunks.extend(result['chunks'])
            self.assertEqual(''.join(c['text'] for c in chunks if c['kind'] == 'text'), text)
            self.assertEqual(chunks[-1]['kind'], 'coverage_gap')
            self.assertIn('page 2', chunks[-1]['text'])
            self.assertTrue(all(len(c['text']) <= 12_000 for c in chunks))
            self.assertTrue(result['all_content_returned'])
            self.assertEqual(len(self.canvas.calls), 1)
            extract.assert_awaited_once()
            self.download.assert_awaited_once()

    async def make_cursor(self):
        parsed = {'segments': [{'location': 'page 1', 'text': 'x' * 25_000}], 'gaps': [], 'complete': True}
        with patch('tools.attachments.extract_isolated', AsyncMock(return_value=parsed)):
            return (await self.read())['next_cursor']

    async def test_cursor_scope_expiry_tampering_and_cache_eviction(self):
        cursor = await self.make_cursor()
        with self.assertRaisesRegex(ValueError, 'different request'):
            await self.attachments.canvas_read_assignment_attachment(42, 50, 100, student_id=8, cursor=cursor)
        with self.assertRaises(ValueError): await self.read(101, cursor=cursor)
        with self.assertRaises(ValueError): await self.read(attempt=2, cursor=cursor)
        self.canvas.access_token = 'synthetic-other-account'
        with self.assertRaises(ValueError): await self.read(cursor=cursor)
        self.canvas.access_token = 'synthetic-canvas-token'
        for forged in ('https://outside.invalid/private', cursor.split(':')[0] + ':999999', cursor + '/x'):
            with self.assertRaises(ValueError): await self.read(cursor=forged)
        with patch('tools.attachments.time.monotonic', return_value=float('inf')):
            with self.assertRaisesRegex(ValueError, 'expired'): await self.read(cursor=cursor)
        self.assertEqual(len(self.attachments._snapshots), 0)
        cursor = await self.make_cursor()
        for _ in range(4): await self.make_cursor()
        self.assertEqual(len(self.attachments._snapshots), 4)
        with self.assertRaisesRegex(ValueError, 'expired'): await self.read(cursor=cursor)

    async def test_unsupported_oversize_and_restricted_files_do_not_download(self):
        for update, reason in [({'display_name': 'Synthetic.png'}, 'unsupported_format'),
                               ({'size': MAX_FILE_BYTES + 1}, 'file_size_limit'),
                               ({'locked_for_user': True}, 'file_access_restricted'),
                               ({'hidden_for_user': True}, 'file_access_restricted')]:
            original = copy.deepcopy(self.canvas.file)
            self.canvas.file.update(update)
            result = await self.read()
            self.assertFalse(result['extraction_complete'])
            self.assertEqual(result['gap_reasons'], [reason])
            self.assertEqual(result['chunks'][0]['kind'], 'coverage_gap')
            self.canvas.file.clear(); self.canvas.file.update(original)
        self.download.assert_not_awaited()

    async def test_download_and_parser_errors_are_explicit_and_do_not_leak_signed_urls(self):
        self.download.side_effect = RuntimeError(self.canvas.file['url'])
        result = await self.read()
        self.assertEqual(result['gap_reasons'], ['attachment_download_failed'])
        self.assertNotIn('verifier', json.dumps(result))
        self.download.side_effect = ValueError('private_attachment_location')
        self.assertEqual((await self.read())['gap_reasons'], ['private_attachment_location'])
        self.download.side_effect = None
        with patch('tools.attachments.extract_isolated', AsyncMock(side_effect=RuntimeError('private text'))):
            result = await self.read()
        self.assertEqual(result['gap_reasons'], ['document_parser_failed'])
        self.assertNotIn('private text', json.dumps(result))

    async def test_permission_errors_and_mismatched_canvas_records_block_download(self):
        self.canvas.failure = CanvasAPIError(403, 'canvas_permission_denied', '/synthetic', 'Synthetic denial')
        with self.assertRaises(CanvasAPIError): await self.read()
        self.canvas.failure = None
        for key, value in [('assignment_id', 99), ('user_id', 9)]:
            original = self.canvas.submission[key]
            self.canvas.submission[key] = value
            with self.assertRaisesRegex(ValueError, 'mismatched'): await self.read()
            self.canvas.submission[key] = original
        self.canvas.file['id'] = 999
        with self.assertRaisesRegex(ValueError, 'mismatched file'):
            await self.attachments.canvas_read_assignment_attachment(42, 50, 100, source='assignment')
        self.download.assert_not_awaited()

    async def test_invalid_arguments_and_empty_inventory(self):
        for kwargs in ({}, {'student_id': 7, 'anonymous_id': 'anon-test'}, {'anonymous_id': '../7'},
                       {'source': 'assignment', 'student_id': 7}, {'source': 'assignment', 'attempt': 1},
                       {'student_id': True}, {'student_id': 7, 'attempt': 0}, {'source': 'unknown'}):
            with self.assertRaises(ValueError):
                await self.attachments.canvas_list_assignment_attachments(42, 50, **kwargs)
        self.assertEqual(self.canvas.calls, [])
        for limit in (0, 6, True):
            with self.assertRaises(ValueError): await self.read(limit=limit)
        self.canvas.submission['attachments'] = []
        result = await self.attachments.canvas_list_assignment_attachments(42, 50, student_id=7)
        self.assertEqual(result['files'], [])
        with self.assertRaisesRegex(ValueError, 'not attached'): await self.read()

    async def test_output_limit_reports_gap_without_claiming_full_extraction(self):
        parsed = {'segments': [{'location': 'page 1', 'text': 'x' * 50_000}], 'gaps': [], 'complete': True}
        with patch('tools.attachments.MAX_SNAPSHOT_CHARACTERS', 13_000), \
                patch('tools.attachments.extract_isolated', AsyncMock(return_value=parsed)):
            result = await self.read(limit=5)
        self.assertFalse(result['extraction_complete'])
        self.assertTrue(result['all_content_returned'])
        self.assertEqual(result['gap_reasons'], ['attachment_output_limit'])
        self.assertEqual(result['chunks'][-1]['kind'], 'coverage_gap')

    async def test_mcp_discovery_and_schema_validated_read(self):
        async with Client(create_server()) as client:
            for query, name in [('read assignment attachment content PDF Word Excel', 'canvas_read_assignment_attachment'),
                                ('list assignment attachments', 'canvas_list_assignment_attachments')]:
                found = await client.call_tool('canvas_search_tools', {'query': query})
                self.assertIn(name, {item['name'] for item in found.data})
            visible = await client.list_tools()
            self.assertNotIn('canvas_read_assignment_attachment', {t.name for t in visible})
            result = await client.call_tool('canvas_call_tool', {'name': 'canvas_read_assignment_attachment',
                'arguments': {'course_id': 42, 'assignment_id': '50', 'file_id': 100, 'student_id': 7}})
            self.assertIn('Synthetic | 12.50', result.data['chunks'][0]['text'])
            self.assertTrue(result.data['extraction_complete'])
            for update in ({'file_id': True}, {'limit': True}, {'attempt': 0}, {'source': 'external'}):
                result = await client.call_tool('canvas_call_tool', {'name': 'canvas_read_assignment_attachment',
                    'arguments': {'course_id': 42, 'assignment_id': 50, 'file_id': 100, 'student_id': 7, **update}}, raise_on_error=False)
                self.assertTrue(result.is_error)


if __name__ == '__main__': unittest.main()
