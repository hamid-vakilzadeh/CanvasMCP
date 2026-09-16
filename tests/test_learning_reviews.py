import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from report_fixtures import SyntheticCanvas
from reporting.render import render_review
from reporting.reviews import CHUNK_CHARACTERS, ReviewCancelled, Reviews, document_batches
from reporting.runtime import Runtime
from reporting.state import Store


class LearningReviewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(SyntheticCanvas.base_url, '99', Path(self.temp.name))
        self.reviews = Reviews(self.store)

    async def test_complete_collection_revisions_provenance_and_unavailable_answers(self):
        job = self.reviews.create('42', '7')
        result = await self.reviews.collect(SyntheticCanvas(), job['id'])
        self.assertEqual(result['status'], 'awaiting_ai')
        evidence = self.reviews.evidence(job['id'])
        text = '\n'.join(e['text'] for e in evidence)
        self.assertIn('prevents all fraud', text)
        self.assertIn('collusion remains possible', text)
        self.assertIn('course module page', json.dumps(evidence))
        self.assertIn('Canvas did not provide the answer', text)
        self.assertIn('New Quizzes', text)
        self.assertNotIn('Must not be associated', text)
        self.assertNotIn('AUTOGRADED CONTENT', text)
        self.assertNotIn('AUTO ANSWER', text)
        revised = next(e for e in evidence if e['text'].startswith('Separating custody'))
        self.assertGreater(len(revised['sources']), 1)
        self.assertIn('"entry_id": "112"', json.dumps(evidence))  # Reply beyond the first ten.
        self.assertNotIn('author_name', json.dumps(evidence))
        self.assertGreater(result['last_collection_metrics']['logical_canvas_calls'], 0)
        before = len(evidence)
        await self.reviews.collect(SyntheticCanvas(), job['id'])
        self.assertEqual(len(self.reviews.evidence(job['id'])), before)

    async def test_analysis_ledger_rejects_unread_and_cross_job_citations(self):
        job = self.reviews.create('42', '7')
        await self.reviews.collect(SyntheticCanvas(), job['id'])
        first = self.reviews.evidence(job['id'])[0]
        with self.assertRaises(ValueError):
            self.reviews.record_analysis(job['id'], [first['id']], [], 'Read without retrieval')
        with self.assertRaises(ValueError):
            render_review(self.store, job['id'], overview='Premature completion')
        batch = self.reviews.next_batch(job['id'], max_characters=200000)
        ids = [e['id'] for e in batch['evidence']]
        invalid = [{'category':'strength', 'interpretation':'observation', 'text':'A claim', 'evidence_ids':['foreign']}]
        with self.assertRaises(ValueError):
            self.reviews.record_analysis(job['id'], ids, invalid, 'Invalid citations')
        finding = {'category':'submission_pattern','interpretation':'observation','text':'<script>alert(1)</script> is quoted as text.','evidence_ids':[ids[0]]}
        saved = self.reviews.record_analysis(job['id'], ids, [finding], 'Synthetic batch inspected')
        duplicate = self.reviews.record_analysis(job['id'], ids, [finding], 'Synthetic batch inspected')
        self.assertEqual(saved['analysis_id'], duplicate['analysis_id'])
        self.assertEqual(saved['coverage']['pending'], 0)
        rendered = render_review(self.store, job['id'], overview='Synthetic faculty overview')
        self.assertEqual(rendered['status'], 'completed_with_gaps')
        html = Path(rendered['report_path']).read_text()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('documented evidence gaps', html)
        self.assertEqual(len(self.store.all('analysis')), 1)

    async def test_durable_runtime_cancel_resume_delete_and_cache(self):
        service = Runtime(SyntheticCanvas, Path(self.temp.name))
        self.addAsyncCleanup(service.close)
        first = await service.report('42','7')
        cached = await service.report('42','7')
        other = await service.report('42','8')
        self.assertFalse(first['cache']['hit'])
        self.assertTrue(cached['cache']['hit'])
        self.assertEqual(cached['metrics']['logical_canvas_calls'], 0)
        self.assertEqual(other['student']['id'], '8')
        job = await service.start_review('42','7')
        await service.cancel(job['id'])
        self.assertEqual((await service.store()).get('report',job['id'])['status'],'cancelled')
        restarted = Runtime(SyntheticCanvas, Path(self.temp.name))
        self.addAsyncCleanup(restarted.close)
        await restarted.resume(job['id'])
        await asyncio.gather(*list(restarted.tasks.values()))
        self.assertTrue(Reviews(await restarted.store()).status(job['id'])['collection_complete'])
        await restarted.delete(job['id'])
        with self.assertRaises(ValueError):
            (await restarted.store()).get('report',job['id'])
        self.assertEqual((await restarted.store()).all('evidence'), [])

    async def test_explicit_partial_report_and_measured_usage_are_honest(self):
        job=self.reviews.create('42','7')
        self.reviews.add(job['id'],'submission','Synthetic readable work',{'location':'assignment 1'})
        self.store.update('report',job['id'],{'collection_complete':True})
        partial=render_review(self.store,job['id'],overview='Evidence remains unread.',allow_incomplete=True)
        self.assertEqual(partial['status'],'incomplete')
        batch=self.reviews.next_batch(job['id'])
        result=self.reviews.record_analysis(job['id'],[e['id'] for e in batch['evidence']],[],
            'Synthetic usage metadata test, not a real model usage measurement.',
            model_usage={'model':'synthetic-model','source':'test fixture','input_tokens':100,'cached_input_tokens':20,'output_tokens':40})
        self.assertEqual(result['model_usage']['input_tokens'],100)
        self.assertEqual(result['model_usage']['batches_reporting_usage'],1)
        self.assertEqual(render_review(self.store,job['id'],overview='All evidence reviewed.')['status'],'completed')

    async def test_quiz_embedded_definition_fallback_preserves_manual_answer_and_zero_score(self):
        class RestrictedDefinitions(SyntheticCanvas):
            async def page(self, endpoint, **kwargs):
                if endpoint.endswith('/quizzes/22/questions'):
                    raise ValueError('Synthetic definition permission error')
                if endpoint.endswith('/quiz_submissions/23/questions'):
                    return {'items':[{'quiz_submission_questions':[
                        {'id':'24','answer':'A synthetic essay answer','score':0,
                         'quiz_question':{'question_type':'essay_question','question_text':'Synthetic prompt','points_possible':5}},
                        {'id':'25','answer':'Auto answer excluded','quiz_question':{'question_type':'multiple_choice_question'}}]}],
                        'next_cursor':None}
                return await super().page(endpoint,**kwargs)
        job=self.reviews.create('42','7')
        await self.reviews.collect(RestrictedDefinitions(),job['id'])
        text='\n'.join(e['text'] for e in self.reviews.evidence(job['id']))
        self.assertIn('A synthetic essay answer',text)
        self.assertIn('"score": 0',text)
        self.assertIn('attempt-specific version',text)
        self.assertNotIn('Auto answer excluded',text)

    async def test_large_document_import_batches_locations_and_keeps_controls_responsive(self):
        segments = [{'location': f'sheet Synthetic, cell A{i}', 'text': str(i % 100)}
                    for i in range(1, 10001)]
        segments.append({'location': 'sheet Synthetic, cell B1', 'text': 'Formula: =SUM(A1:A10000)\nCached result: unavailable'})
        gaps = [{'location': f'sheet Synthetic, cell B{i}', 'reason': 'formula_result_unavailable_not_calculated'}
                for i in range(1, 1001)]
        extracted = {'segments': segments, 'gaps': gaps}
        job = self.reviews.create('42', '7')
        ticks = []

        async def observe():
            while True:
                ticks.append(len(self.reviews.evidence(job['id'])))
                await asyncio.sleep(0)

        monitor = asyncio.create_task(observe())
        try:
            with patch('reporting.reviews.download_attachment', new=AsyncMock(return_value=b'synthetic')), \
                 patch('reporting.reviews.extract_isolated', new=AsyncMock(return_value=extracted)):
                await self.reviews.attachment(SyntheticCanvas(), job['id'], {'id':'1','filename':'synthetic.xlsx'}, {})
                first = self.reviews.evidence(job['id'])
                await self.reviews.attachment(SyntheticCanvas(), job['id'], {'id':'1','filename':'synthetic.xlsx'}, {})
        finally:
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)
        evidence = self.reviews.evidence(job['id'])
        self.assertEqual(evidence, first)  # Resume/repeated attachment is idempotent.
        self.assertLess(len(evidence), 50)
        self.assertTrue(all(len(e['text']) <= CHUNK_CHARACTERS for e in evidence))
        text = '\n\n'.join(e['text'] for e in evidence if e['kind'] == 'file')
        for segment in segments:
            self.assertIn(f"[{segment['location']}]\n{segment['text']}", text)
        gap_text = '\n\n'.join(e['text'] for e in evidence if e['kind'] == 'gap')
        for gap in gaps:
            self.assertIn(f"[{gap['location']}]\n{gap['reason']}", gap_text)
        self.assertTrue(any(0 < n < len(evidence) for n in ticks))

    async def test_document_import_cancellation_runs_between_batches(self):
        segments = [{'location': f'row {i}', 'text': 'Synthetic row ' + str(i)} for i in range(10000)]
        job = self.reviews.create('42', '7')

        async def cancel():
            await asyncio.sleep(0)
            self.store.update('report', job['id'], {'status': 'cancelled'})

        task = asyncio.create_task(cancel())
        with patch('reporting.reviews.download_attachment', new=AsyncMock(return_value=b'synthetic')), \
             patch('reporting.reviews.extract_isolated', new=AsyncMock(return_value={'segments':segments,'gaps':[]})):
            with self.assertRaises(ReviewCancelled):
                await self.reviews.attachment(SyntheticCanvas(), job['id'], {'filename':'synthetic.csv'}, {})
        await task
        self.assertLess(len(self.reviews.evidence(job['id'])), len(list(document_batches(segments))))

    def test_long_document_segments_preserve_all_text_and_source_locations(self):
        original = 'Synthetic paragraph. ' * 2000
        result = list(document_batches([{'location':'page 1','text':original}]))
        self.assertEqual(''.join(s['text'] for s in result), original)
        self.assertTrue(all(s['location'] == 'page 1' and len(s['text']) <= CHUNK_CHARACTERS for s in result))

    def test_delete_review_keeps_other_jobs_and_discussion_records(self):
        first = self.reviews.create('42', '7')
        second = self.reviews.create('42', '8')
        self.reviews.add(first['id'], 'file', 'Synthetic first work', {'location':'page 1'})
        self.reviews.add(second['id'], 'file', 'Synthetic other work', {'location':'page 1'})
        self.store.create('analysis', {'job_id': first['id'], 'summary':'Synthetic first analysis'})
        other_analysis = self.store.create('analysis', {'job_id':second['id'], 'summary':'Synthetic other analysis'})
        watch = self.store.create('watch', {'status':'paused'})
        export = self.store.directory / f"report-{first['id']}.html"
        export.write_text('Synthetic export')
        self.store.delete_job(first['id'])
        self.assertFalse(export.exists())
        self.assertEqual([r['id'] for r in self.store.all('report')], [second['id']])
        self.assertEqual([r['job_id'] for r in self.store.all('evidence')], [second['id']])
        self.assertEqual(self.store.all('analysis'), [other_analysis])
        self.assertEqual(self.store.all('watch'), [watch])


if __name__ == '__main__': unittest.main()
