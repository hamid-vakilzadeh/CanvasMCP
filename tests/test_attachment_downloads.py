"""Original downloads use scoped Canvas access and private local paths only."""

import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fastmcp import Client
from canvas_client import AsyncCanvasClient
from reporting.documents import MAX_FILE_BYTES
from server import create_server
from tools.attachments import AttachmentTools, private_temp_root
from test_assistant_plans import FakeMCP
from test_assignment_attachments import SyntheticAttachments
from test_course_item_attachments import ItemCanvas
from ferpa_test_support import enable_synthetic_student_records

setUpModule = enable_synthetic_student_records


class OriginalDownloadTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.canvas = SyntheticAttachments()
        self.canvas.file.update(display_name='Synthetic.dms', filename='Synthetic.dms')
        self.data = b'\x00\xffSynthetic original bytes\r\n'
        self.download = AsyncMock(return_value=self.data)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        for target, replacement in (
            ('tools.attachments.AsyncCanvasClient.from_environment', self.canvas),
            ('tools.attachments.download_attachment', self.download),
            ('tools.attachments.private_temp_root', self.root),
        ):
            p = patch(target, replacement) if isinstance(replacement, AsyncMock) else patch(target, return_value=replacement)
            p.start(); self.addCleanup(p.stop)
        self.tools = AttachmentTools(FakeMCP())

    async def read(self, **kwargs):
        return await self.tools.canvas_read_assignment_attachment(42, 50, 100, student_id=7, **kwargs)

    def assert_download(self, result):
        self.assertTrue(result['downloaded'])
        self.assertFalse(result['content_extracted'])
        self.assertEqual(result['content_kind'], 'download')
        path = Path(result['local_path'])
        self.assertTrue(path.is_relative_to(self.root))
        self.assertEqual(path.read_bytes(), self.data)
        self.assertEqual(result['byte_count'], len(self.data))
        self.assertEqual(result['sha256'], hashlib.sha256(self.data).hexdigest())
        self.assertEqual(path.name, 'attachment.dms')
        if os.name == 'posix':
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertNotIn('verifier', str(result))
        self.assertNotIn(self.canvas.access_token, str(result))

    async def test_original_unknown_format_roundtrips_through_discovery_and_mcp(self):
        parsed = await self.read()
        self.assertEqual(parsed['gap_reasons'], ['unsupported_format'])
        self.assertTrue(parsed['original_download_available'])
        self.download.assert_not_awaited()
        with patch('tools.attachments.extract_isolated', AsyncMock()) as parser:
            async with Client(create_server()) as client:
                found = await client.call_tool('canvas_search_tools', {'query': 'download original unsupported assignment attachment'})
                self.assertIn('canvas_read_assignment_attachment', {t['name'] for t in found.data})
                result = await client.call_tool('canvas_call_tool', {
                    'name': 'canvas_read_assignment_attachment', 'arguments': {
                        'course_id': 42, 'assignment_id': 50, 'student_id': 7, 'file_id': 100,
                        'download_original': True}})
                self.assert_download(result.data)
            parser.assert_not_awaited()
        self.download.assert_awaited_once()

    async def test_quiz_and_discussion_original_downloads_use_the_same_scoped_pipeline(self):
        canvas = ItemCanvas()
        for file in canvas.files.values():
            file['display_name'] = 'Synthetic.dms'
        with patch.object(AsyncCanvasClient, 'from_environment', return_value=canvas):
            async with Client(create_server()) as client:
                for tool, args in (
                    ('canvas_read_quiz_attachment', {'course_id': 42, 'quiz_id': 21,
                        'quiz_submission_id': 30, 'question_id': 71, 'file_id': 101}),
                    ('canvas_read_discussion_attachment', {'course_id': 42, 'topic_id': 60,
                        'entry_id': 61, 'file_id': 201}),
                ):
                    result = await client.call_tool('canvas_call_tool', {'name': tool,
                        'arguments': {**args, 'download_original': True}})
                    self.assert_download(result.structured_content)
        self.assertTrue(all(c[0] in {'GET', 'PAGE'} for c in canvas.calls))

    async def test_download_preserves_anonymity_uses_generated_names_and_never_overwrites(self):
        self.canvas.file['display_name'] = '../../synthetic-private-name.dms'
        paths = []
        for _ in range(2):
            result = await self.tools.canvas_read_assignment_attachment(
                42, 50, 100, anonymous_id='anon-test', download_original=True)
            self.assert_download(result)
            self.assertNotIn('student_id', result)
            self.assertNotIn('synthetic-private-name', result['local_path'])
            paths.append(result['local_path'])
        self.assertNotEqual(*paths)
        self.assertTrue(all('/anonymous_submissions/' in call[0] for call in self.canvas.calls))

    async def test_invalid_combinations_and_unrelated_files_never_save(self):
        for args in ({'cursor': 'anything'}, {'archive_member': 'work.txt'}):
            with self.assertRaisesRegex(ValueError, 'cannot be combined'):
                await self.read(download_original=True, **args)
        self.assertEqual(self.canvas.calls, [])
        with self.assertRaises(ValueError):
            await self.read(attempt=1, download_original=True)
        self.download.assert_not_awaited()
        self.assertEqual(list(self.root.iterdir()), [])

    async def test_restricted_oversize_and_failed_downloads_do_not_save_files(self):
        for key, value, reason in (
            ('locked_for_user', True, 'file_access_restricted'),
            ('hidden_for_user', True, 'file_access_restricted'),
            ('size', MAX_FILE_BYTES + 1, 'file_size_limit'),
        ):
            original = self.canvas.file.get(key)
            self.canvas.file[key] = value
            result = await self.read(download_original=True)
            self.assertEqual(result['gap_reasons'], [reason])
            self.assertFalse(result['original_download_available'])
            self.assertFalse(result['downloaded'])
            self.canvas.file[key] = original
        self.download.assert_not_awaited()
        self.download.side_effect = RuntimeError('Synthetic private URL or response')
        result = await self.read(download_original=True)
        self.assertEqual(result['gap_reasons'], ['attachment_download_failed'])
        self.assertNotIn('Synthetic private', str(result))
        self.assertEqual(list(self.root.iterdir()), [])

    async def test_local_write_error_cleans_partial_directory_and_reports_fixed_code(self):
        original_open = os.open
        def deny_file(path, *args, **kwargs):
            if Path(path).name == 'attachment.dms':
                raise PermissionError('Synthetic private path')
            return original_open(path, *args, **kwargs)
        with patch('tools.attachments.os.open', side_effect=deny_file):
            result = await self.read(download_original=True)
        self.assertEqual(result['gap_reasons'], ['local_download_failed'])
        self.assertFalse(result['downloaded'])
        self.assertNotIn('Synthetic private', str(result))
        self.assertEqual(list(self.root.iterdir()), [])

    async def test_disabled_ferpa_blocks_download_before_network_or_disk(self):
        with patch.dict(os.environ, {'FERPA': 'false'}):
            async with Client(create_server()) as client:
                result = await client.call_tool('canvas_call_tool', {
                    'name': 'canvas_read_assignment_attachment', 'arguments': {
                        'course_id': 42, 'assignment_id': 50, 'student_id': 7, 'file_id': 100,
                        'download_original': True}}, raise_on_error=False)
        self.assertTrue(result.is_error)
        self.download.assert_not_awaited()
        self.assertEqual(self.canvas.calls, [])
        self.assertEqual(list(self.root.iterdir()), [])

    async def test_temp_directory_in_a_git_checkout_is_rejected(self):
        (self.root / '.git').mkdir()
        with patch('tools.attachments.private_temp_root', private_temp_root), \
             patch('tools.attachments.tempfile.gettempdir', return_value=str(self.root)):
            with self.assertRaisesRegex(ValueError, 'outside a Git repository'):
                await self.read(download_original=True)
        self.assertEqual(list(self.root.iterdir()), [self.root / '.git'])


if __name__ == '__main__':
    unittest.main()
