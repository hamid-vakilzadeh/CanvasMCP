"""Synthetic anonymous survey statistics and identity-free MCP responses."""

import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fastmcp import Client
from canvas_client import AsyncCanvasClient
from ferpa import check_request
from server import create_server
from tools.quiz_statistics import QuizStatisticsTools, scale_value
from test_assistant_plans import FakeMCP
from ferpa_test_support import enable_synthetic_student_records

setUpModule = enable_synthetic_student_records


class SurveyCanvas:
    base_url = 'https://canvas.example.invalid'

    def __init__(self):
        self.calls = []
        self.quiz = {'id': 21, 'title': 'Synthetic survey', 'quiz_type': 'survey',
                     'anonymous_submissions': True, 'question_count': 2}
        labels = ['Strongly disagree', 'Disagree', 'Neither agree nor disagree',
                  'Agree', 'Strongly agree', 'Not applicable / synthetic option']
        self.questions = [{'id': qid, 'question_type': 'multiple_choice_question',
            'question_text': f'<p>Synthetic question {position}</p>',
            'answers': [{'id': i, 'text': text, 'weight': 100} for i, text in enumerate(labels, 1)]}
            for position, qid in enumerate((71, 72), 1)]
        self.record = {'quiz_id': '21', 'includes_all_versions': False,
            'generated_at': '2026-01-01T00:00:00Z', 'multiple_attempts_exist': True,
            'submission_statistics': {'unique_count': 10, 'score_average': 100,
                                      'user_ids': ['SYNTHETIC_IDENTITY_SENTINEL']},
            'question_statistics': []}
        for definition, counts in zip(self.questions, ([1, 1, 2, 2, 1, 2], [0, 0, 0, 0, 5, 4])):
            row = copy.deepcopy(definition)
            row.update(responses=sum(counts), user_names=['SYNTHETIC_IDENTITY_SENTINEL'],
                       response_values=['SYNTHETIC_FREE_RESPONSE'])
            for a, n in zip(row['answers'], counts):
                a.update(responses=n, user_ids=['SYNTHETIC_IDENTITY_SENTINEL'])
            row['answers'].append({'id': 'none', 'text': 'No Answer', 'responses': 1})
            self.record['question_statistics'].append(row)
        self.payload = {'quiz_statistics': [self.record]}

    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass

    async def get(self, endpoint, params=None):
        self.calls.append(('GET', endpoint, params))
        if endpoint == '/api/v1/courses/42/quizzes/21': return copy.deepcopy(self.quiz)
        if endpoint == '/api/v1/courses/42/quizzes/21/statistics':
            assert params == {'all_versions': 'false'}
            return copy.deepcopy(self.payload)
        raise AssertionError('Unexpected endpoint: no student lookup is permitted')

    async def page(self, endpoint, *, params=None, cursor=None, limit=None):
        self.calls.append(('PAGE', endpoint, params, cursor))
        assert endpoint == '/api/v1/courses/42/quizzes/21/questions'
        index = 0 if cursor is None else 1
        return {'items': copy.deepcopy(self.questions[index:index+1]),
                'next_cursor': 'synthetic-next' if index == 0 else None}


class SurveyStatisticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.canvas = SurveyCanvas()
        p = patch.object(AsyncCanvasClient, 'from_environment', return_value=self.canvas)
        p.start(); self.addCleanup(p.stop)
        self.tools = QuizStatisticsTools(FakeMCP())

    async def read(self, **args):
        return await self.tools.canvas_get_quiz_statistics(42, 21, **args)

    async def test_real_mcp_discovery_counts_averages_and_identity_allowlist(self):
        async with Client(create_server()) as client:
            found = await client.call_tool('canvas_search_tools', {'query': 'anonymous survey statistics response counts averages'})
            self.assertIn('canvas_get_quiz_statistics', {x['name'] for x in found.data})
            result = await client.call_tool('canvas_call_tool', {'name': 'canvas_get_quiz_statistics',
                'arguments': {'course_id': 42, 'quiz_id': 21}})
        data = result.data
        self.assertEqual(data['status'], 'available')
        self.assertEqual(data['completed_submission_count'], 10)
        self.assertEqual(data['generated_at'], self.canvas.record['generated_at'])
        first, second = data['questions']
        self.assertEqual(first['response_count'], 9)
        self.assertEqual(first['not_applicable_count'], 2)
        self.assertEqual(first['unanswered_count'], 1)
        self.assertEqual(first['rated_response_count'], 7)
        self.assertAlmostEqual(first['average_1_to_5'], 22 / 7)
        self.assertEqual(second['average_1_to_5'], 5)
        self.assertAlmostEqual(data['overall_average_1_to_5'], 47 / 12)
        self.assertEqual(data['overall_rated_response_count'], 12)
        encoded = json.dumps(data)
        for private in ('SYNTHETIC_IDENTITY_SENTINEL', 'SYNTHETIC_FREE_RESPONSE', 'user_ids', 'user_names', 'score_average'):
            self.assertNotIn(private, encoded)
        self.assertEqual(len(self.canvas.calls), 4)  # Definition + two question pages + statistics.

    async def test_all_na_or_unanswered_has_no_average(self):
        for row in self.canvas.record['question_statistics']:
            for a in row['answers']: a['responses'] = 0
            row['answers'][-2]['responses'] = 8
            row['answers'][-1]['responses'] = 2
            row['responses'] = 8
        data = await self.read()
        self.assertEqual(data['status'], 'available')
        self.assertIsNone(data['overall_average_1_to_5'])
        self.assertEqual(data['overall_rated_response_count'], 0)
        self.assertTrue(all(q['average_status'] == 'no_rated_responses' for q in data['questions']))

    async def test_custom_scale_requires_explicit_mapping_not_order_or_correctness(self):
        self.canvas.questions[0]['answers'][0]['text'] = 'Synthetic custom scale label'
        self.canvas.record['question_statistics'][0]['answers'][0]['text'] = 'Synthetic custom scale label'
        data = await self.read()
        self.assertEqual(data['questions'][0]['average_status'], 'mapping_required')
        self.assertIsNone(data['overall_average_1_to_5'])
        mapped = await self.read(answer_values={'71': {'1': 1}})
        self.assertAlmostEqual(mapped['questions'][0]['average_1_to_5'], 22 / 7)
        for values in ({'71': {'6': 1}}, {'999': {'1': 1}}, {'71': {'99': 1}}, {'71': {'1': True}}, {'71': {'1': 6}}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                await self.read(answer_values=values)

    async def test_schema_rejects_boolean_rating_before_conversion(self):
        async with Client(create_server()) as client:
            result = await client.call_tool('canvas_call_tool', {'name':'canvas_get_quiz_statistics',
                'arguments': {'course_id':42, 'quiz_id':21, 'answer_values':{'71':{'1':True}}}}, raise_on_error=False)
        self.assertTrue(result.is_error)
        self.assertEqual(self.canvas.calls, [])

    async def test_missing_reports_and_204_are_not_zero_counts(self):
        for payload in (None, {}, {'quiz_statistics': []}):
            self.canvas.payload = payload
            data = await self.read()
            self.assertEqual(data['status'], 'unavailable')
            self.assertIsNone(data['completed_submission_count'])
            self.assertIsNone(data['overall_average_1_to_5'])

    async def test_json_api_quiz_links_are_verified_without_being_returned_or_followed(self):
        self.canvas.record.pop('quiz_id')
        self.canvas.record['links'] = {'quiz': self.canvas.base_url + '/api/v1/courses/42/quizzes/21'}
        data = await self.read()
        self.assertEqual(data['status'], 'available')
        self.assertNotIn('links', data)
        for link in ('https://outside.invalid/api/v1/courses/42/quizzes/21',
                     self.canvas.base_url + '/api/v1/courses/99/quizzes/21',
                     self.canvas.base_url + '/api/v1/courses/42/quizzes/22'):
            self.canvas.record['links']['quiz'] = link
            with self.assertRaisesRegex(ValueError, 'different quiz'):
                await self.read()

    async def test_confirmed_zero_completions_produces_zero_choices_without_averages(self):
        self.canvas.record['submission_statistics']['unique_count'] = 0
        self.canvas.record['question_statistics'] = []
        data = await self.read()
        self.assertEqual(data['completed_submission_count'], 0)
        self.assertEqual(len(data['questions']), 2)
        self.assertTrue(all(a['response_count'] == 0 for q in data['questions'] for a in q['answers']))
        self.assertIsNone(data['overall_average_1_to_5'])

    async def test_missing_counts_changed_definitions_and_inconsistent_totals_withhold_average(self):
        original = copy.deepcopy(self.canvas.record)
        for mutate in (
            lambda: self.canvas.record['question_statistics'][0]['answers'][0].pop('responses'),
            lambda: self.canvas.record['question_statistics'][0]['answers'][0].update(responses=True),
            lambda: self.canvas.record['question_statistics'][0]['answers'][0].update(responses=-1),
            lambda: self.canvas.record['question_statistics'][0]['answers'][0].update(text='Changed synthetic label'),
            lambda: self.canvas.record['question_statistics'][0].update(responses=8),
            lambda: self.canvas.record['submission_statistics'].update(unique_count=1),
        ):
            self.canvas.record.clear(); self.canvas.record.update(copy.deepcopy(original))
            mutate()
            data = await self.read()
            self.assertEqual(data['status'], 'partial')
            self.assertIsNone(data['overall_average_1_to_5'])
            self.assertIsNone(data['questions'][0]['average_1_to_5'])

    async def test_no_all_attempts_or_mismatched_statistics_are_silently_used(self):
        self.canvas.record['includes_all_versions'] = True
        data = await self.read()
        self.assertIsNone(data['completed_submission_count'])
        self.canvas.record['includes_all_versions'] = False
        self.canvas.record['quiz_id'] = 22
        with self.assertRaisesRegex(ValueError, 'different quiz'): await self.read()
        self.canvas.record['quiz_id'] = 21
        self.canvas.payload['quiz_statistics'].append(copy.deepcopy(self.canvas.record))
        with self.assertRaisesRegex(ValueError, 'ambiguous'): await self.read()

    async def test_nonanonymous_and_essay_statistics_never_return_student_answers(self):
        self.canvas.quiz['anonymous_submissions'] = False
        self.canvas.questions[1]['question_type'] = 'essay_question'
        self.canvas.record['question_statistics'][1]['answers'] = [{'text':'SYNTHETIC_FREE_RESPONSE','responses':10}]
        data = await self.read()
        self.assertFalse(data['anonymous_survey'])
        self.assertEqual(data['questions'][1]['answers'], [])
        self.assertIsNone(data['questions'][1]['average_1_to_5'])
        self.assertNotIn('SYNTHETIC_FREE_RESPONSE', json.dumps(data))
        self.assertNotIn('SYNTHETIC_IDENTITY_SENTINEL', json.dumps(data))

    async def test_new_quizzes_rejected_and_ferpa_off_blocks_search_call_and_transport(self):
        self.canvas.quiz['is_new_quiz'] = True
        with self.assertRaisesRegex(ValueError, 'Classic Quiz'): await self.read()
        self.canvas.calls.clear()
        with patch.dict(os.environ, {'FERPA':'false'}):
            async with Client(create_server()) as client:
                found = await client.call_tool('canvas_search_tools', {'query':'anonymous survey statistics'})
                self.assertNotIn('canvas_get_quiz_statistics', {x['name'] for x in found.data})
                result = await client.call_tool('canvas_call_tool', {'name':'canvas_get_quiz_statistics',
                    'arguments':{'course_id':42,'quiz_id':21}}, raise_on_error=False)
                self.assertTrue(result.is_error)
            with self.assertRaisesRegex(ValueError, 'FERPA=true'):
                check_request('https://canvas.example.invalid/api/v1/courses/42/quizzes/21/statistics')
        self.assertEqual(self.canvas.calls, [])

    def test_scale_labels_are_explicit_and_na_is_never_six(self):
        for text, value in [('1',1),('5 — Synthetic highest',5),('Agree',4),('Neither agree nor disagree',3)]:
            self.assertEqual(scale_value(text)[0], value)
        for text in ('N/A', 'Not applicable', 'Not applicable / synthetic option'):
            self.assertEqual(scale_value(text), (None, 'not_applicable'))
        for text in ('6', '1–5', '10', '5.5', 'Sometimes'):
            self.assertEqual(scale_value(text), (None, 'unmapped'))


if __name__ == '__main__': unittest.main()
