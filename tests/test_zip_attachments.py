"""Synthetic ZIP extraction, private parsing, and MCP attachment workflows."""

import base64
import io
import json
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fastmcp import Client
from openpyxl import Workbook
from reporting import archives
from reporting.documents import extract_isolated
from server import create_server
from canvas_client import AsyncCanvasClient
from tools.attachments import AttachmentTools
from test_assistant_plans import FakeMCP
from test_assignment_attachments import SyntheticAttachments
from test_course_item_attachments import ItemCanvas, png
from ferpa_test_support import enable_synthetic_student_records

setUpModule = enable_synthetic_student_records


def make_zip(entries, compression=zipfile.ZIP_DEFLATED):
    data = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(data, 'w', compression) as archive:
            for name, content in entries:
                archive.writestr(name, content)
    return data.getvalue()


def workbook():
    book = Workbook()
    book.active['A1'] = 2
    book.active['A2'] = '=A1*3'
    stream = io.BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


class ArchiveParserTests(unittest.IsolatedAsyncioTestCase):
    def test_inventory_reports_members_without_claiming_contents_read(self):
        data = make_zip([('work/', ''), ('work/notes.txt', 'Synthetic text'),
                         ('work/video.mp4', b'video'), ('nested.zip', make_zip([]))])
        result = archives.extract_archive(data)
        self.assertFalse(result['complete'])
        self.assertFalse(result['archive']['contents_read'])
        self.assertTrue(result['archive']['inventory_complete'])
        self.assertEqual(result['archive']['entry_count'], 4)
        entries = [json.loads(s['text']) for s in result['segments']]
        self.assertTrue(entries[1]['readable'])
        self.assertFalse(entries[0]['readable'])
        self.assertEqual({g['reason'] for g in result['gaps']},
                         {'unsupported_format', 'nested_archive_not_supported', 'archive_contents_not_read'})
        self.assertNotIn('Synthetic text', str(result))

    async def test_isolated_members_return_text_formulas_and_original_image_and_cleanup(self):
        image = png()
        data = make_zip([('work/notes.txt', 'Synthetic evidence'),
                         ('work/table.xlsx', workbook()), ('work/diagram.png', image)])
        with tempfile.TemporaryDirectory() as directory:
            for member in ('work/notes.txt', 'work/table.xlsx', 'work/diagram.png'):
                with self.subTest(member=member):
                    result = await extract_isolated(data, 'work.zip', Path(directory), archive_member=member)
                    self.assertEqual(list(Path(directory).iterdir()), [])
                    self.assertEqual(result['archive']['member'], member)
                    self.assertEqual(len(result['archive']['sha256']), 64)
                    if member.endswith('.png'):
                        self.assertEqual(base64.b64decode(result['image_data']), image)
                        self.assertEqual(result['image']['mime_type'], 'image/png')
                    elif member.endswith('.xlsx'):
                        self.assertIn('Formula: =A1*3', str(result))
                        self.assertFalse(result['complete'])
                        self.assertIn('formula_result_unavailable_not_calculated', str(result))
                    else:
                        self.assertTrue(result['complete'])
                        self.assertIn('Synthetic evidence', str(result))
                        self.assertTrue(result['segments'][0]['location'].startswith(member + ' / '))

    def test_unsafe_paths_links_duplicates_and_nested_archives_are_not_read(self):
        link = zipfile.ZipInfo('link.txt')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        entries = [(name, 'Synthetic') for name in
                   ('../outside.txt', '/absolute.txt', 'C:/drive.txt', 'dir\\file.txt')]
        entries += [(link, '/private/file'), ('repeat.txt', 'one'), ('repeat.txt', 'two'),
                    ('inside.zip', make_zip([('safe.txt', 'nested')]))]
        data = make_zip(entries)
        with patch.object(zipfile.ZipFile, 'extract', side_effect=AssertionError('no disk extraction')), \
             patch.object(zipfile.ZipFile, 'extractall', side_effect=AssertionError('no disk extraction')):
            for name, reason in (
                ('../outside.txt', 'unsafe_archive_path'), ('/absolute.txt', 'unsafe_archive_path'),
                ('C:/drive.txt', 'unsafe_archive_path'), ('dir\\file.txt', 'unsafe_archive_path'),
                ('link.txt', 'archive_special_file_not_supported'),
                ('repeat.txt', 'duplicate_archive_member'), ('inside.zip', 'nested_archive_not_supported'),
            ):
                with self.subTest(name=name):
                    result = archives.extract_archive(data, name)
                    self.assertFalse(result['complete'])
                    self.assertEqual(result['segments'], [])
                    self.assertEqual(result['gaps'][0]['reason'], reason)

    def test_broken_missing_encrypted_and_unsupported_members_report_fixed_codes(self):
        data = make_zip([('work.txt', 'Synthetic')], zipfile.ZIP_STORED)
        self.assertEqual(archives.extract_archive(b'not a ZIP')['gaps'][0]['reason'], 'archive_parse_failed')
        self.assertEqual(archives.extract_archive(make_zip([]))['gaps'][0]['reason'], 'empty_archive')
        self.assertEqual(archives.extract_archive(data, 'absent.txt')['gaps'][0]['reason'], 'archive_member_not_found')
        corrupted = data.replace(b'Synthetic', b'Different')
        self.assertEqual(archives.extract_archive(corrupted, 'work.txt')['gaps'][0]['reason'], 'archive_parse_failed')
        for offset, value, reason in ((6, 1, 'encrypted_archive_member'),
                                      (8, 99, 'archive_compression_not_supported')):
            altered = bytearray(data)
            central = altered.index(b'PK\x01\x02')
            struct.pack_into('<H', altered, offset, value)
            struct.pack_into('<H', altered, central + offset + 2, value)
            result = archives.extract_archive(bytes(altered), 'work.txt')
            self.assertEqual(result['gaps'][0]['reason'], reason)

    def test_archive_entry_expansion_member_and_image_limits(self):
        data = make_zip([('work.txt', 'x' * 2000), ('image.png', b'x' * 1000)])
        for constant, maximum, member, reason in (
            ('MAX_ARCHIVE_ENTRIES', 1, None, 'archive_entry_limit'),
            ('MAX_EXPANDED_BYTES', 200, None, 'archive_expansion_limit'),
            ('MAX_FILE_BYTES', 1000, 'work.txt', 'file_size_limit'),
            ('MAX_IMAGE_BYTES', 500, 'image.png', 'image_size_limit'),
        ):
            with self.subTest(reason=reason), patch.object(archives, constant, maximum):
                self.assertEqual(archives.extract_archive(data, member)['gaps'][0]['reason'], reason)
        with patch.object(archives, 'MAX_FILE_BYTES', 1):
            self.assertEqual(archives.extract_archive(data)['gaps'][0]['reason'], 'file_size_limit')
        oversized_name = make_zip([('x' * 1100 + '.txt', 'Synthetic')])
        self.assertEqual(archives.extract_archive(oversized_name)['gaps'][0]['reason'], 'archive_member_name_limit')


class ZipAttachmentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.canvas = SyntheticAttachments()
        self.canvas.file.update(display_name='Synthetic work.ZIP', filename='work.zip',
                                **{'content-type': 'application/zip'})
        self.data = make_zip([('notes.txt', 'Synthetic content'), ('table.xlsx', workbook()),
                              ('diagram.png', png()), ('long.txt', 'abcdef' * 5000)])
        self.canvas.file['size'] = len(self.data)
        self.download = AsyncMock(return_value=self.data)
        p = patch.object(AsyncCanvasClient, 'from_environment', return_value=self.canvas)
        p.start(); self.addCleanup(p.stop)
        p = patch('tools.attachments.download_attachment', self.download)
        p.start(); self.addCleanup(p.stop)
        self.tools = AttachmentTools(FakeMCP())

    async def read(self, **kwargs):
        return await self.tools.canvas_read_assignment_attachment(42, 50, 100, student_id=7, **kwargs)

    async def test_inventory_and_member_read_are_discoverable_through_mcp(self):
        inventory = await self.tools.canvas_list_assignment_attachments(42, 50, student_id=7)
        self.assertTrue(inventory['files'][0]['supported_format'])
        self.assertNotIn('unavailable_reason', inventory['files'][0])
        async with Client(create_server()) as client:
            found = await client.call_tool('canvas_search_tools', {'query': 'read ZIP assignment attachment'})
            self.assertIn('canvas_read_assignment_attachment', {t['name'] for t in found.data})
            args = {'course_id': 42, 'assignment_id': 50, 'student_id': 7, 'file_id': 100}
            listing = await client.call_tool('canvas_call_tool', {
                'name': 'canvas_read_assignment_attachment', 'arguments': args})
            self.assertEqual(listing.data['content_kind'], 'archive_inventory')
            self.assertFalse(listing.data['extraction_complete'])
            self.assertIn('archive_contents_not_read', listing.data['gap_reasons'])
            self.assertFalse(listing.data['all_content_returned'])
            self.assertIn('notes.txt', str(listing.data['chunks']))
            self.assertNotIn('Synthetic content', str(listing.data))
            last_page = await client.call_tool('canvas_call_tool', {
                'name': 'canvas_read_assignment_attachment',
                'arguments': {**args, 'cursor': listing.data['next_cursor']}})
            self.assertTrue(last_page.data['all_content_returned'])
            self.assertEqual(last_page.data['chunks'][0]['kind'], 'coverage_gap')
            for member in ('notes.txt', 'table.xlsx', 'diagram.png'):
                result = await client.call_tool('canvas_call_tool', {
                    'name': 'canvas_read_assignment_attachment',
                    'arguments': {**args, 'archive_member': member}})
                public = result.structured_content
                self.assertEqual(public['archive_member'], member)
                self.assertNotIn('verifier', str(public))
                self.assertNotIn(self.canvas.access_token, str(public))
                if member.endswith('.png'):
                    images = [c for c in result.content if c.type == 'image']
                    self.assertEqual(len(images), 1)
                    self.assertEqual(base64.b64decode(images[0].data), png())
                elif member.endswith('.xlsx'):
                    self.assertIn('Formula: =A1*3', str(public))
                else:
                    self.assertIn('Synthetic content', str(public['chunks']))

    async def test_member_cursor_stays_bound_and_reuses_parsed_snapshot(self):
        result = await self.read(archive_member='long.txt')
        self.assertFalse(result['all_content_returned'])
        cursor = result['next_cursor']
        for member in (None, 'notes.txt'):
            with self.assertRaisesRegex(ValueError, 'different request'):
                await self.read(archive_member=member, cursor=cursor)
        chunks = result['chunks'][:]
        while result['next_cursor']:
            result = await self.read(archive_member='long.txt', cursor=result['next_cursor'])
            chunks.extend(result['chunks'])
        self.download.assert_awaited_once()
        self.assertEqual(len(self.canvas.calls), 1)
        self.assertEqual(''.join(c['text'] for c in chunks), 'abcdef' * 5000)
        self.assertTrue(result['extraction_complete'])

    async def test_archive_selection_does_not_bypass_scope_or_restrictions(self):
        with self.assertRaisesRegex(ValueError, 'not attached'):
            await self.read(attempt=1, archive_member='notes.txt')
        self.download.assert_not_awaited()
        self.canvas.file['locked_for_user'] = True
        result = await self.read(archive_member='notes.txt')
        self.assertEqual(result['gap_reasons'], ['file_access_restricted'])
        self.download.assert_not_awaited()
        self.canvas.file['locked_for_user'] = False
        self.canvas.file['display_name'] = 'Synthetic.txt'
        with self.assertRaisesRegex(ValueError, 'only supported for ZIP'):
            await self.read(archive_member='notes.txt')
        self.download.assert_not_awaited()

    async def test_truncated_inventory_and_member_report_incomplete_coverage(self):
        with patch('tools.attachments.MAX_SNAPSHOT_CHARACTERS', 100):
            listing = await self.read()
            self.assertFalse(listing['archive']['inventory_complete'])
            self.assertFalse(listing['extraction_complete'])
            self.assertIn('attachment_output_limit', listing['gap_reasons'])
            member = await self.read(archive_member='long.txt')
            self.assertFalse(member['archive']['contents_read'])
            self.assertFalse(member['extraction_complete'])
            self.assertIn('attachment_output_limit', member['gap_reasons'])

    async def test_zip_members_work_for_quiz_and_discussion_sources(self):
        canvas = ItemCanvas()
        for file in canvas.files.values():
            file.update(display_name='Synthetic.zip', size=len(self.data))
        with patch.object(AsyncCanvasClient, 'from_environment', return_value=canvas):
            async with Client(create_server()) as client:
                for tool, args in (
                    ('canvas_read_quiz_attachment', {'course_id': 42, 'quiz_id': 21,
                        'quiz_submission_id': 30, 'question_id': 71, 'file_id': 101}),
                    ('canvas_read_discussion_attachment', {'course_id': 42, 'topic_id': 60,
                        'entry_id': 61, 'file_id': 201}),
                ):
                    result = await client.call_tool('canvas_call_tool', {'name': tool,
                        'arguments': {**args, 'archive_member': 'notes.txt'}})
                    self.assertIn('Synthetic content', str(result.structured_content['chunks']))
                    self.assertTrue(result.structured_content['extraction_complete'])


if __name__ == '__main__':
    unittest.main()
