"""Synthetic quiz/discussion media, ownership checks, and answer-history fallback."""

import base64
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fastmcp import Client
from PIL import Image
from openpyxl import Workbook
from canvas_client import AsyncCanvasClient, CanvasAPIError
from action_plans import PlanStore
from reporting.documents import inspect_image
from server import create_server
from tools.assistant import AssistantTools
from tools.attachments import AttachmentTools
from test_assistant_plans import FakeMCP, FakeProgress


def png():
    stream = io.BytesIO()
    Image.new('RGB', (16, 12), 'purple').save(stream, format='PNG')
    return stream.getvalue()


class ItemCanvas:
    base_url = 'https://canvas.example.invalid'
    access_token = 'synthetic-secret'

    def __init__(self):
        self.calls = []
        self.quiz = {'id': 21, 'assignment_id': 50}
        self.quiz_submission = {'id': 30, 'quiz_id': 21, 'submission_id': 40, 'user_id': 7,
                                'attempt': 2, 'workflow_state': 'complete'}
        self.submission = {'id': 40, 'user_id': 7, 'assignment_id': 50, 'attempt': 2,
            'submission_history': [
                {'attempt': 1, 'submission_data': [{'question_id': 71, 'attachment_ids': [102]},
                                                  {'question_id': 72, 'text': 'Older synthetic answer', 'points': 1}]},
                {'attempt': 2, 'submission_data': [{'question_id': 71, 'attachment_ids': [101]},
                                                  {'question_id': 72, 'text': '<p>Current synthetic essay</p>', 'points': 0},
                                                  {'question_id': 73, 'text': 'Auto-graded answer'}]},
            ]}
        self.definitions = [{'id': 71, 'question_type': 'file_upload_question'},
                            {'id': 72, 'question_type': 'essay_question'},
                            {'id': 73, 'question_type': 'multiple_choice_question'}]
        self.answer_payload = {'quiz_submission_questions': [{'id': 71}, {'id': 72, 'answer': None}, {'id': 73}]}
        self.entry = {'id': 61, 'message': '<a href="/files/201/download?verifier=AUTHORED">Synthetic workbook</a>',
                      'attachments': [], 'deleted': False}
        self.files = {str(i): {'id': i, 'display_name': f'synthetic-{i}.{suffix}', 'size': 100,
                             'url': f'{self.base_url}/files/{i}/download?verifier=private'}
                      for i, suffix in ((101,'png'), (102,'png'), (201,'xlsx'))}
        self.failure = None

    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass

    async def get(self, endpoint, params=None):
        self.calls.append(('GET', endpoint, params))
        if self.failure: raise self.failure
        if endpoint == '/api/v1/courses/42/quizzes/21': result = self.quiz
        elif endpoint == '/api/v1/courses/42/quizzes/21/submissions/30': result = {'quiz_submissions': [self.quiz_submission]}
        elif endpoint == '/api/v1/courses/42/assignments/50/submissions/7': result = self.submission
        elif endpoint == '/api/v1/quiz_submissions/30/questions': result = self.answer_payload
        elif endpoint.startswith('/api/v1/files/'): result = self.files[endpoint.split('/')[-1]]
        else: raise AssertionError(f'Unexpected endpoint {endpoint}')
        return copy.deepcopy(result)

    async def page(self, endpoint, *, params=None, cursor=None, limit=100):
        self.calls.append(('PAGE', endpoint, params, cursor))
        if '/discussion_topics/' in endpoint:
            result = [self.entry] if endpoint == '/api/v1/courses/42/discussion_topics/60/entry_list' else []
            assert params == {'ids[]': ['61']} or params == {'ids[]': ['62']}
        else:
            assert endpoint == '/api/v1/courses/42/quizzes/21/questions'
            result = self.definitions
        return {'items': copy.deepcopy(result), 'next_cursor': None, 'count': len(result)}

    async def put(self, endpoint, *, data=None, json_data=None):
        self.calls.append(('PUT', endpoint, data))
        return {'updated': True}


class CourseItemAttachmentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.canvas = ItemCanvas()
        p = patch.object(AsyncCanvasClient, 'from_environment', return_value=self.canvas)
        p.start(); self.addCleanup(p.stop)
        self.image_bytes = png()
        self.download = AsyncMock(return_value=self.image_bytes)
        p = patch('tools.attachments.download_attachment', self.download)
        p.start(); self.addCleanup(p.stop)
        self.tools = AttachmentTools(FakeMCP())
        self.assistant = AssistantTools(FakeMCP())
        self.store = PlanStore()
        p = patch('tools.assistant.plan_store', self.store); p.start(); self.addCleanup(p.stop)

    async def quiz_read(self, **overrides):
        return await self.tools.canvas_read_quiz_attachment(**{
            'course_id':42, 'quiz_id':21, 'quiz_submission_id':30, 'question_id':71, 'file_id':101, **overrides})

    async def discussion_read(self, **overrides):
        return await self.tools.canvas_read_discussion_attachment(**{
            'course_id':42, 'topic_id':60, 'entry_id':61, 'file_id':201, **overrides})

    async def test_quiz_image_roundtrips_through_real_mcp_search_proxy(self):
        async with Client(create_server()) as client:
            for query, name in [('read Classic Quiz uploaded image attachment', 'canvas_read_quiz_attachment'),
                                ('read discussion workbook attachment', 'canvas_read_discussion_attachment')]:
                found = await client.call_tool('canvas_search_tools', {'query':query})
                self.assertIn(name, {t['name'] for t in found.data})
            result = await client.call_tool('canvas_call_tool', {'name':'canvas_read_quiz_attachment', 'arguments':{
                'course_id':42, 'quiz_id':21, 'quiz_submission_id':30, 'question_id':71, 'file_id':101}})
        images = [c for c in result.content if c.type == 'image']
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].mime_type, 'image/png')
        self.assertEqual(base64.b64decode(images[0].data), self.image_bytes)
        metadata = result.structured_content
        self.assertEqual(metadata['resolved_attempt'], 2)
        self.assertEqual(metadata['image'], {'mime_type':'image/png', 'width':16, 'height':12})
        self.assertNotIn('verifier', json.dumps(metadata))
        self.assertNotIn('user_id', metadata)
        self.assertTrue(all(call[0] in {'GET','PAGE'} for call in self.canvas.calls))

    async def test_quiz_rejects_wrong_file_question_attempt_and_associations(self):
        for override in ({'file_id':102}, {'question_id':72}, {'attempt':1}, {'attempt':3}, {'attempt':True}):
            with self.subTest(override=override), self.assertRaises(ValueError): await self.quiz_read(**override)
        self.download.assert_not_awaited()
        for field, value in [('quiz_id',99), ('submission_id',99), ('user_id',8)]:
            original = self.canvas.quiz_submission[field]
            self.canvas.quiz_submission[field] = value
            with self.assertRaises((ValueError, AssertionError)): await self.quiz_read()
            self.canvas.quiz_submission[field] = original
        self.download.assert_not_awaited()
        older = await self.quiz_read(attempt=1, file_id=102)
        self.assertEqual(older.structured_content['resolved_attempt'], 1)
        question_calls = [c for c in self.canvas.calls if c[1].endswith('/questions')]
        self.assertEqual(question_calls[-1][2]['quiz_submission_attempt'], 1)

    async def test_pending_review_quiz_is_readable_but_running_attempt_is_not(self):
        self.canvas.quiz_submission['workflow_state'] = 'pending_review'
        self.assertEqual((await self.quiz_read()).content[-1].type, 'image')
        self.canvas.quiz_submission['workflow_state'] = 'untaken'
        with self.assertRaisesRegex(ValueError, 'submitted'): await self.quiz_read()

    async def test_discussion_workbook_extracts_cells_formulas_and_cached_value_gaps(self):
        workbook = Workbook(); sheet = workbook.active; sheet.title = 'Synthetic analysis'
        sheet['A1'] = 0; sheet['B2'] = '=SUM(A1:A3)'
        data = io.BytesIO(); workbook.save(data); self.download.return_value = data.getvalue()
        result = await self.discussion_read()
        pages_read = [result.structured_content]
        while pages_read[-1]['next_cursor']:
            result = await self.discussion_read(cursor=pages_read[-1]['next_cursor'])
            pages_read.append(result.structured_content)
        text = '\n'.join(chunk['text'] for page in pages_read for chunk in page['chunks'])
        self.assertIn('cell A1]\n0', text)
        self.assertIn('Formula: =SUM(A1:A3)', text)
        self.assertIn('formula_result_unavailable_not_calculated', text)
        self.assertFalse(pages_read[0]['extraction_complete'])
        self.assertNotIn('AUTHORED', self.download.call_args.args[0]['url'])
        self.download.assert_awaited_once()

    async def test_discussion_direct_attachment_and_image_use_same_content_pipeline(self):
        self.canvas.entry.update(message='', attachment=self.canvas.files['101'])
        result = await self.discussion_read(file_id=101)
        self.assertEqual(result.content[-1].type, 'image')
        self.assertEqual(base64.b64decode(result.content[-1].data), self.image_bytes)

    async def test_discussion_rejects_sibling_deleted_external_and_unrelated_files(self):
        for overrides in ({'file_id':101}, {'entry_id':62}, {'topic_id':99}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError): await self.discussion_read(**overrides)
        self.canvas.entry['deleted'] = True
        with self.assertRaises(ValueError): await self.discussion_read()
        self.canvas.entry.update(deleted=False, message='<a href="https://outside.invalid/files/201">x</a>')
        with self.assertRaises(ValueError): await self.discussion_read()
        self.download.assert_not_awaited()

    async def test_permission_denial_and_mismatched_file_metadata_do_not_download(self):
        self.canvas.files['101']['id'] = 999
        with self.assertRaisesRegex(ValueError, 'mismatched file'): await self.quiz_read()
        self.canvas.failure = CanvasAPIError(403, 'canvas_permission_denied', '/synthetic', 'Denied')
        with self.assertRaises(CanvasAPIError): await self.quiz_read()
        self.download.assert_not_awaited()

    async def test_images_with_spoofed_bytes_limits_or_animation_return_gaps(self):
        self.download.return_value = b'<html>This is not an image</html>'
        result = await self.quiz_read()
        self.assertEqual(result.structured_content['gap_reasons'], ['image_decode_failed'])
        self.assertFalse(any(c.type == 'image' for c in result.content))
        self.canvas.files['101']['size'] = 9 * 1024 * 1024
        self.assertEqual((await self.quiz_read()).structured_content['gap_reasons'], ['image_size_limit'])
        stream = io.BytesIO()
        Image.new('RGB',(2,2),'red').save(stream, format='GIF', save_all=True,
                                       append_images=[Image.new('RGB',(2,2),'blue')])
        self.assertEqual(inspect_image(stream.getvalue())['gaps'][0]['reason'], 'animated_image_not_supported')
        with patch('reporting.documents.MAX_IMAGE_PIXELS', 10):
            self.assertEqual(inspect_image(self.image_bytes)['gaps'][0]['reason'], 'image_pixel_limit')

    def test_other_supported_image_formats_preserve_detected_mime_and_dimensions(self):
        for fmt, mime in [('JPEG', 'image/jpeg'), ('WEBP', 'image/webp'), ('GIF', 'image/gif')]:
            with self.subTest(format=fmt):
                stream = io.BytesIO()
                Image.new('RGB', (8, 6), 'blue').save(stream, format=fmt)
                result = inspect_image(stream.getvalue())
                self.assertTrue(result['complete'])
                self.assertEqual(result['image'], {'mime_type':mime, 'width':8, 'height':6})

    async def test_quiz_review_falls_back_to_matching_history_and_preserves_direct_answers(self):
        review = await self.assistant.canvas_get_quiz_submission_review(42,21,quiz_submission_id=30)
        self.assertEqual(review['question_count'], 2)
        self.assertEqual(review['answers_unavailable'], 0)
        self.assertEqual(review['questions'][0]['attachment_ids'], ['101'])
        essay = review['questions'][1]
        self.assertEqual(essay['answer'], 'Current synthetic essay')
        self.assertEqual(essay['answer_source'], 'assignment_submission_history')
        self.assertEqual(essay['score'], 0)
        self.assertTrue(essay['score_available'])
        self.canvas.answer_payload['quiz_submission_questions'][1].update(answer='Direct answer', score=2)
        review = await self.assistant.canvas_get_quiz_submission_review(42,21,quiz_submission_id=30)
        self.assertEqual(review['questions'][1]['answer'], 'Direct answer')
        self.assertEqual(review['questions'][1]['score'], 2)
        self.canvas.answer_payload['quiz_submission_questions'][1].pop('answer')
        self.canvas.submission['submission_history'].pop()
        review = await self.assistant.canvas_get_quiz_submission_review(42,21,quiz_submission_id=30)
        self.assertIsNone(review['questions'][1]['answer'])
        self.assertFalse(review['questions'][1]['answer_available'])

    async def test_quiz_grading_fallback_evidence_has_a_stale_guard(self):
        plan = await self.assistant.canvas_plan_quiz_submission_grade(42,21,30,question_updates=[{'question_id':72,'score':2}])
        self.assertEqual(len(self.store._plans[plan['plan_token']].preconditions), 3)
        self.canvas.submission['submission_history'][1]['submission_data'][1]['text'] = 'Changed after preview'
        with self.assertRaisesRegex(ValueError, 'stale'):
            await self.assistant.canvas_apply_change(plan['plan_token'], True, FakeProgress())
        self.assertFalse(any(c[0] == 'PUT' for c in self.canvas.calls))


if __name__ == '__main__': unittest.main()
