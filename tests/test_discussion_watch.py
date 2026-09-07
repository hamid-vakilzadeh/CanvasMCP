import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from action_plans import plan_store
from canvas_client import CanvasAPIError
from discussion_data import flatten_entries, read_discussion
from discussion_watch import Watcher
from reporting.state import Store


class DiscussionCanvas:
    def __init__(self):
        self.view = {'view':[{'id':'1','user_id':'7','message':'Initial question','replies':[
            {'id':str(i),'user_id':'8','message':f'Synthetic reply {i}'} for i in range(2,18)]}], 'new_entries':[]}
        self.topic = {'id':'31','title':'Synthetic discussion','published':True,'locked':False}
        self.error = None
        self.posts = []
        self.uncertain = False

    async def get(self, endpoint, params=None):
        if self.error:
            raise self.error
        return copy.deepcopy(self.view if endpoint.endswith('/view') else self.topic)

    async def post(self, endpoint, data=None):
        self.posts.append((endpoint,data))
        entry = {'id':'99','user_id':'50','parent_id':endpoint.split('/entries/')[1].split('/')[0], 'message':data['message']}
        self.view['new_entries'].append(entry)
        if self.uncertain:
            raise TimeoutError('Synthetic write accepted but response lost')
        return entry


class DiscussionWatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store=Store('https://canvas.example.invalid','50',Path(self.temp.name))
        self.client=DiscussionCanvas(); self.watcher=Watcher(self.store,'50')
        self.watch=await self.watcher.configure(self.client,'42','31')

    async def enqueue(self):
        self.client.view['new_entries']=[{'id':'18','parent_id':'1','user_id':'7','message':'A later question in an old thread'}]
        await self.watcher.poll(self.client,self.watch['id'])
        return self.store.all('activity')[0]

    async def draft(self):
        activity=await self.enqueue()
        inspected=await self.watcher.inspect(self.client,activity['id'])
        self.assertGreater(len(inspected['context']['entries']),10)
        return await self.watcher.review(self.client,activity['id'],inspected['activity']['revision'],
                                        'draft','Clarify the reasoning','<p>Which control addresses the risk?</p>')

    async def test_baseline_old_thread_replies_restart_edits_and_deletions(self):
        self.assertEqual(self.store.all('activity'),[])
        self.assertNotIn('Initial question',str(self.store.get('watch',self.watch['id'])['baseline']))
        activity=await self.enqueue()
        self.assertEqual(activity['event'],'new')
        await Watcher(self.store,'50').poll(self.client,self.watch['id'])
        self.assertEqual(len(self.store.all('activity')),1)
        self.client.view['new_entries'][0]['message']='Edited question'
        await self.watcher.poll(self.client,self.watch['id'])
        self.assertEqual(self.store.all('activity')[-1]['event'],'edited')
        self.client.view['new_entries'][0]['deleted']=True
        await self.watcher.poll(self.client,self.watch['id'])
        self.assertEqual(self.store.all('activity')[-1]['event'],'deleted')
        self.assertEqual(self.store.all('activity')[-1]['status'],'dismissed')

    async def test_overlay_preserves_parent_and_own_replies_do_not_requeue(self):
        self.client.view['new_entries']=[{'id':'17','message':'Overlay edit'}, {'id':'19','parent_id':'1','user_id':'50','message':'My reply'}]
        flat=flatten_entries(self.client.view)
        self.assertEqual(next(e for e in flat if e['id']=='17')['parent_id'],'1')
        await self.watcher.poll(self.client,self.watch['id'])
        self.assertEqual([a['entry_id'] for a in self.store.all('activity')],['17'])

    async def test_stale_draft_and_single_publication_across_plans(self):
        draft=await self.draft()
        first=await self.watcher.plan_draft(self.client,draft['id'])
        second=await self.watcher.plan_draft(self.client,draft['id'])
        applied=await self.watcher.apply_draft(self.client,await plan_store.consume(first['plan_token']))
        self.assertEqual(applied['status'],'completed')
        with self.assertRaises(ValueError):
            await self.watcher.apply_draft(self.client,await plan_store.consume(second['plan_token']))
        self.assertEqual(len(self.client.posts),1)
        with self.assertRaises(ValueError):
            await plan_store.consume(first['plan_token'])

    async def test_context_change_invalidates_plan(self):
        draft=await self.draft()
        plan=await self.watcher.plan_draft(self.client,draft['id'])
        self.client.view['view'][0]['message']='Changed context'
        with self.assertRaises(ValueError):
            await self.watcher.apply_draft(self.client,await plan_store.consume(plan['plan_token']))
        self.assertEqual(self.client.posts,[])

    async def test_uncertain_write_requires_inspection_and_reconciliation(self):
        draft=await self.draft(); self.client.uncertain=True
        plan=await self.watcher.plan_draft(self.client,draft['id'])
        result=await self.watcher.apply_draft(self.client,await plan_store.consume(plan['plan_token']))
        self.assertEqual(result['status'],'uncertain')
        with self.assertRaises(ValueError):
            await self.watcher.plan_draft(self.client,draft['id'])
        inspected=await self.watcher.inspect(self.client,draft['id'])
        self.assertEqual(inspected['possible_posted_reply_ids'],['99'])
        resolved=await self.watcher.review(self.client,draft['id'],inspected['activity']['revision'],
                                          'confirmed_posted','Faculty inspected the returned matching reply',reply_id='99')
        self.assertEqual(resolved['status'],'posted')
        self.assertEqual(len(self.client.posts),1)

    async def test_errors_backoff_permissions_pause_and_group_roots(self):
        self.client.error=CanvasAPIError(503,'canvas_request_failed','/synthetic','private failure text')
        result=await self.watcher.poll(self.client,self.watch['id'])
        self.assertEqual(result['status'],'active')
        self.assertNotIn('private failure',str(self.store.get('watch',self.watch['id'])))
        self.client.error=CanvasAPIError(401,'canvas_authentication_failed','/synthetic','private failure text')
        self.assertEqual((await self.watcher.poll(self.client,self.watch['id']))['status'],'paused')
        self.client.error=None; self.client.topic['group_topic_children']=[{'id':'88'}]
        with self.assertRaises(ValueError): await read_discussion(self.client,'42','31')

if __name__ == '__main__': unittest.main()
