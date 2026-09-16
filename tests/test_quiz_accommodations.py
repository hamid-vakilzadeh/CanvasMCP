"""Synthetic-only accommodation plans, wire payloads and completion reporting."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from action_plans import PlanStore
from canvas_client import AsyncCanvasClient, CanvasAPIError, encode_cursor
from fastmcp import Client
from server import create_server
from tools.assistant import AssistantTools
import tools.quiz_accommodations as accommodations
from test_assistant_plans import FakeMCP, FakeProgress


class Canvas:
    def __init__(self):
        self.calls = []
        self.quizzes = {
            '11': {'id':'11', 'title':'Synthetic quiz A', 'time_limit':30, 'published':True,
                   'unlock_at':'2026-10-01T10:00:00Z', 'lock_at':'2026-10-01T11:00:00Z'},
            '12': {'id':'12', 'title':'Synthetic quiz B', 'time_limit':45, 'published':False},
        }
        self.inventory = [['11'], ['12']]
        self.submissions = {q: [[{'id': '91'+q, 'user_id':'7', 'quiz_id':q, 'extra_time':5,
            'workflow_state':'untaken', 'end_at':None}]] for q in self.quizzes}
        self.students = ['7','8']
        self.responses = []
        self.page_error = None

    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass

    def payload(self, endpoint, params=None):
        parsed = urlsplit(endpoint)
        query = parse_qs(parsed.query)
        number = int(query.get('page', [(params or {}).get('page', 1)])[0])-1
        path = parsed.path
        if path.endswith('/enrollments'):
            student = str(params['user_id'])
            return ([{'user_id':student, 'type':'StudentEnrollment', 'enrollment_state':'active',
                      'user':{'name':f'Synthetic Student {student}'}}] if student in self.students else []), False
        if path.endswith('/submissions'):
            rows = self.submissions[path.split('/')[-2]]
            return {'quiz_submissions': copy.deepcopy(rows[number])}, number+1 < len(rows)
        if path.endswith('/quizzes'):
            return [copy.deepcopy(self.quizzes[q]) for q in self.inventory[number]], number+1 < len(self.inventory)
        return copy.deepcopy(self.quizzes[path.split('/')[-1]]), False

    async def get(self, endpoint, params=None):
        self.calls.append(('GET', endpoint, params))
        return self.payload(endpoint, params)[0]

    async def page(self, endpoint, *, params=None, cursor=None, limit=100):
        self.calls.append(('PAGE', endpoint, cursor))
        if self.page_error and endpoint.endswith('/quizzes') and cursor:
            raise self.page_error
        url = accommodations.decode_cursor(cursor) if cursor else endpoint
        payload, more = self.payload(url, params)
        page = int(parse_qs(urlsplit(url).query).get('page', ['1'])[0])
        next_cursor = encode_cursor(f'https://canvas.example.invalid{urlsplit(endpoint).path}?page={page+1}&per_page=100') if more else None
        return {'items':payload if isinstance(payload,list) else [payload], 'next_cursor':next_cursor}

    async def post(self, endpoint, *, data=None, json_data=None):
        self.calls.append(('POST', endpoint, data, json_data))
        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, Exception): raise response
            return response
        if endpoint.endswith('/extensions'):
            return {'quiz_extensions':[{'quiz_id':endpoint.split('/')[-2], **r} for r in json_data['quiz_extensions']]}
        return {'successful':[{'user_id':r['user_id']} for r in json_data], 'failed':[]}


class AccommodationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = PlanStore()
        self.canvas = Canvas()
        for target, replacement in [('tools.quiz_accommodations.plan_store',self.store),
                                    ('tools.assistant.plan_store',self.store)]:
            p = patch(target,replacement); p.start(); self.addCleanup(p.stop)
        p = patch.object(AsyncCanvasClient, 'from_environment', return_value=self.canvas)
        p.start(); self.addCleanup(p.stop)
        self.tools = accommodations.QuizAccommodationTools(FakeMCP())
        self.apply = AssistantTools(FakeMCP())

    async def plan(self, **kwargs):
        return await self.tools.canvas_plan_quiz_accommodations(course_id='42', student_ids=['7'], **kwargs)

    async def test_classic_multiplier_is_per_quiz_and_only_changes_student_time(self):
        result = await self.plan(quiz_ids=['11','12'], time_multiplier=1.5)
        pending = self.store._plans[result['plan_token']]
        self.assertFalse(any(c[0] == 'POST' for c in self.canvas.calls))
        self.assertEqual([m.json_data for m in pending.mutations], [
            {'quiz_extensions':[{'user_id':7,'extra_time':15}]},
            {'quiz_extensions':[{'user_id':7,'extra_time':23}]}])
        self.assertEqual([q['students'][0]['total_time_minutes'] for q in result['preview']['quizzes']], [45,68])
        self.assertTrue(any('cut off' in w for w in result['warnings']))
        self.assertEqual(result['preview']['quizzes'][0]['students'][0]['previous_extra_time_minutes'],5)
        applied = await self.apply.canvas_apply_change(result['plan_token'],True,FakeProgress())
        self.assertEqual(applied['status'],'completed')
        self.assertEqual(applied['student_changes'], {'applied':2,'failed':0,'uncertain':0})
        with self.assertRaises(ValueError):
            await self.apply.canvas_apply_change(result['plan_token'],True,FakeProgress())

    async def test_all_timed_follows_pages_skips_untimed_and_includes_unpublished(self):
        self.canvas.quizzes['13'] = {'id':'13','time_limit':None}
        self.canvas.inventory[1].append('13')
        result = await self.plan(scope='all_timed',time_multiplier=1.1)
        self.assertEqual(result['mutation_count'],2)
        self.assertEqual(result['preview']['quizzes'][0]['students'][0]['extra_time_minutes'],3)
        self.assertFalse(result['preview']['quizzes'][1]['published'])
        self.assertEqual(result['preview']['skipped'],[{'quiz_id':'13','reason':'No time limit'}])
        self.assertTrue(any('created later' in w for w in result['warnings']))

    async def test_existing_extensions_follow_submission_pagination_and_hide_other_students(self):
        self.canvas.submissions['11'].insert(0,[{'user_id':'99','extra_time':50,'name':'Unrelated person'}])
        self.canvas.submissions['11'][1][0].update(extra_time=60,workflow_state='untaken',end_at='2026-10-01T11:00:00Z')
        result = await self.plan(quiz_ids=['11'],extra_time_minutes=0)
        self.assertEqual(result['preview']['quizzes'][0]['students'][0]['previous_extra_time_minutes'],60)
        self.assertTrue(any('reduces' in w for w in result['warnings']))
        self.assertNotIn('Unrelated person',json.dumps(result))
        self.assertEqual((await self.apply.canvas_apply_change(result['plan_token'],True,FakeProgress()))['status'],'completed')

    async def test_stale_quiz_or_extension_prevents_every_write(self):
        for change in ('quiz','extension','inventory'):
            with self.subTest(change=change):
                result = await self.plan(scope='all_timed',time_multiplier=1.5)
                if change == 'quiz': self.canvas.quizzes['12']['time_limit'] += 1
                elif change == 'extension': self.canvas.submissions['11'][0][0]['extra_time'] += 1
                else: self.canvas.inventory[1].append('11')
                with self.assertRaisesRegex(ValueError,'stale'):
                    await self.apply.canvas_apply_change(result['plan_token'],True,FakeProgress())
        self.assertFalse(any(c[0] == 'POST' for c in self.canvas.calls))

    async def test_incomplete_inventory_never_creates_a_plan(self):
        self.canvas.page_error = CanvasAPIError(403,'canvas_permission_denied','/synthetic','Synthetic denied')
        with self.assertRaises(CanvasAPIError):
            await self.plan(scope='all_timed',time_multiplier=1.5)
        self.assertEqual(self.store._plans,{})

    async def test_invalid_requests_and_wrong_student_or_engine_are_rejected(self):
        cases = [dict(quiz_ids=['11']), dict(quiz_ids=['11'],extra_time_minutes=3,time_multiplier=1.5),
                 dict(quiz_ids=['11'],extra_time_minutes=True), dict(quiz_ids=['11'],extra_time_minutes=-1),
                 dict(quiz_ids=['11'],extra_time_minutes=10081), dict(quiz_ids=['11'],time_multiplier=float('nan')),
                 dict(quiz_ids=['11'],time_multiplier=.5), dict(quiz_ids=['11','11'],extra_time_minutes=5),
                 dict(scope='all_timed',quiz_ids=['11'],extra_time_minutes=5),
                 dict(scope='course',extra_time_minutes=5), dict(engine='new',scope='course',time_multiplier=1.5),
                 dict(quiz_ids=['11'],extra_time_minutes=5,apply_to_in_progress_quiz_sessions=True)]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError): await self.plan(**values)
        self.canvas.students=[]
        with self.assertRaisesRegex(ValueError,'not enrolled'): await self.plan(quiz_ids=['11'],extra_time_minutes=5)
        self.canvas.students=['7']; self.canvas.quizzes['11']['is_new_quiz']=True
        with self.assertRaisesRegex(ValueError,'New Quiz'): await self.plan(quiz_ids=['11'],extra_time_minutes=5)
        self.assertEqual(self.store._plans,{})

    async def test_new_quiz_uses_assignment_id_seconds_and_top_level_array(self):
        self.canvas.quizzes['11']['quiz_settings']={'has_time_limit':True,'session_time_limit_in_seconds':1800}
        result=await self.plan(engine='new',quiz_ids=['11'],time_multiplier=1.5)
        pending=self.store._plans[result['plan_token']]
        self.assertEqual(pending.mutations[0].endpoint,'/api/quiz/v1/courses/42/quizzes/11/accommodations')
        self.assertEqual(pending.mutations[0].json_data,[{'user_id':7,'extra_time':15}])
        self.assertEqual(result['preview']['quizzes'][0]['identifier_type'],'assignment_id')
        self.assertFalse(result['preview']['quizzes'][0]['students'][0]['previous_setting_available'])

    async def test_new_course_http_200_partial_failure_is_not_completed(self):
        result=await self.tools.canvas_plan_quiz_accommodations(course_id='42',student_ids=['7','8'],engine='new',scope='course',extra_time_minutes=30)
        mutation=self.store._plans[result['plan_token']].mutations[0]
        self.assertEqual(mutation.endpoint,'/api/quiz/v1/courses/42/accommodations')
        self.assertEqual(mutation.json_data,[{'user_id':7,'extra_time':30,'apply_to_in_progress_quiz_sessions':False},
                                             {'user_id':8,'extra_time':30,'apply_to_in_progress_quiz_sessions':False}])
        self.canvas.responses=[{'successful':[{'user_id':7}], 'failed':[{'user_id':8,'error':'Synthetic failure'}]}]
        result=await self.apply.canvas_apply_change(result['plan_token'],True,FakeProgress())
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['student_changes'],{'applied':1,'failed':1,'uncertain':0})

    async def test_partial_permissions_and_lost_responses_do_not_retry(self):
        for error,status in [(CanvasAPIError(403,'denied','/synthetic','Synthetic permission failure'),'failed'),
                             (CanvasAPIError(0,'canvas_connection_failed','/synthetic','Timeout'),'uncertain')]:
            result=await self.plan(quiz_ids=['11','12'],extra_time_minutes=10)
            self.canvas.responses=[{'quiz_extensions':[{'quiz_id':11,'user_id':7,'extra_time':10}]},error]
            applied=await self.apply.canvas_apply_change(result['plan_token'],True,FakeProgress())
            self.assertEqual(applied['status'],'partial')
            self.assertEqual(applied['student_changes'][status],1)
        self.assertEqual(sum(c[0]=='POST' for c in self.canvas.calls),4)
        result=await self.plan(engine='new',scope='course',extra_time_minutes=10)
        self.canvas.responses=[{'successful':[],'failed':[]}]
        self.assertEqual((await self.apply.canvas_apply_change(result['plan_token'],True,FakeProgress()))['status'],'uncertain')

    async def test_discovery_and_schema_reject_boolean_minutes(self):
        async with Client(create_server()) as client:
            result=await client.call_tool('canvas_search_tools',{'query':'student quiz extra time 1.5x accommodations'})
            self.assertIn('canvas_plan_quiz_accommodations',{r['name'] for r in result.data})
            invalid=await client.call_tool('canvas_call_tool',{'name':'canvas_plan_quiz_accommodations',
                'arguments':{'course_id':'42','student_ids':['7'],'quiz_ids':['11'],'extra_time_minutes':True}},raise_on_error=False)
            self.assertTrue(invalid.is_error)
            valid = await client.call_tool('canvas_call_tool', {'name':'canvas_plan_quiz_accommodations',
                'arguments':{'course_id':42,'student_ids':[7],'scope':'all_timed','time_multiplier':1.5}})
            self.assertEqual(valid.data['mutation_count'],2)
            applied = await client.call_tool('canvas_apply_change', {'plan_token':valid.data['plan_token'],'confirm':True})
            self.assertEqual(applied.data['status'],'completed')

    async def test_real_http_client_preserves_json_array_and_classic_nested_payload(self):
        import httpx2
        received=[]
        def handler(request):
            received.append((request.headers['content-type'],json.loads(request.content)))
            return httpx2.Response(200,json={'successful':[{'user_id':7}],'failed':[]})
        client=AsyncCanvasClient('https://canvas.example.invalid','synthetic-token')
        await client._client.aclose()
        client._client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
        async with client:
            for payload in ([{'user_id':7,'extra_time':15}],{'quiz_extensions':[{'user_id':7,'extra_time':15}]}):
                await client.post('/synthetic',json_data=payload)
                self.assertEqual(received[-1],('application/json',payload))


if __name__ == '__main__': unittest.main()
