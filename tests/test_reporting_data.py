"""Synthetic reporting invariants: completeness, semantics and privacy."""

import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reporting.data import all_pages, assignment_row, collect_snapshot, compact_snapshot, grades_from, student_report
from reporting.state import Store, StateConflict


class FakeReportCanvas:
    def __init__(self, fail_second=False):
        self.calls = []
        self.fail_second = fail_second

    async def get(self, endpoint, params=None):
        self.calls.append((endpoint, params))
        if endpoint.endswith('/enrollments'):
            return [{"user": {"id": "7", "name": "Synthetic Student", "email": "private@example.invalid"},
                     "enrollment_state": "active", "grades": {"current_score": 81.25, "final_score": 67.5}}]
        if endpoint.endswith('/progress'):
            return {"requirement_count": 0, "requirement_completed_count": 0}
        if endpoint.endswith('/activity'):
            raise RuntimeError('private diagnostic payload')
        if endpoint == '/api/v1/courses/42':
            return {"id": "42", "name": "Synthetic Course"}
        raise AssertionError(endpoint)

    async def page(self, endpoint, *, params=None, cursor=None, limit=100):
        self.calls.append((endpoint, params, cursor))
        if endpoint.endswith('/enrollments'):
            return {'items': await self.get(endpoint, params), 'next_cursor': None}
        if endpoint.endswith('/modules'):
            return {"items": [], "next_cursor": None}
        if self.fail_second and cursor:
            raise RuntimeError('private diagnostic payload')
        offset = 100 if cursor else 0
        rows = [{"id": str(i + 500), "assignment_id": str(i), "score": 2,
                 "missing": i == 101, "assignment": {"name": f"Exercise {i}", "points_possible": 10}}
                for i in range(offset, min(offset + 100, 105))]
        return {"items": rows, "next_cursor": None if cursor else 'page-two'}


class ReportingDataTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_snapshot_covers_more_than_one_hundred(self):
        result = await collect_snapshot(FakeReportCanvas(), '42', '7')
        self.assertEqual(len(result['submissions']), 105)
        self.assertTrue(result['coverage']['submissions']['complete'])
        self.assertEqual(result['coverage']['submissions']['page_calls'], 2)
        self.assertIsNone(result['submissions_next_cursor'])
        self.assertNotIn('private diagnostic', str(result['warnings']))
        old = compact_snapshot(result, activity_key='activity')
        self.assertEqual(old['warnings'][0]['section'], 'activity')

    async def test_failed_page_is_partial_not_a_complete_total(self):
        result = await student_report(FakeReportCanvas(fail_second=True), '42', '7')
        self.assertEqual(len(result['assignments']), 100)
        self.assertFalse(result['counts_complete'])
        self.assertEqual(result['grades']['current_score'], 81.25)
        self.assertFalse(result['progress']['configured'])
        self.assertIsNone(result['progress']['percent'])
        self.assertNotIn('email', result['student'])

    def test_unknowns_excuses_lateness_and_student_dates(self):
        row = assignment_row({"assignment_id": 5, "score": None, "submitted_at": "2026-01-01",
                              "late": True, "assignment": {"due_at": "2025-12-01", "points_possible": 10}})
        self.assertEqual(row['status'], 'awaiting_grading')
        self.assertIn('late', row['flags'])
        self.assertIsNone(row['percent'])
        self.assertIsNone(row['student_due_at'])
        self.assertEqual(assignment_row({"excused": True, "score": 0})['status'], 'excused')
        self.assertEqual(assignment_row({"score": 0, "assignment": {"points_possible": 5}})['percent'], 0)
        self.assertEqual(assignment_row({})['status'], 'not_submitted')

    def test_grading_period_metadata_and_no_computed_average(self):
        grades = grades_from([{"grades": {"current_score": 92, "final_score": 61},
                               "current_period_computed_current_score": 80, "current_grading_period_id": 4}])
        self.assertEqual(grades['current_score'], 92)
        self.assertEqual(grades['final_score'], 61)
        self.assertEqual(grades['periods']['current_period_computed_current_score'], 80)
        self.assertIsNone(grades_from([])['current_score'])

    async def test_unavailable_outcomes_and_truncated_module_items(self):
        from report_fixtures import SyntheticCanvas
        class PartialContext(SyntheticCanvas):
            async def page(self,endpoint,**kwargs):
                if endpoint.endswith(('/outcome_results','/outcome_rollups')):
                    raise ValueError('Synthetic unavailable outcome data')
                if endpoint.endswith('/modules'):
                    return {'items':[{'id':'51','name':'Module','items_count':2,'items':[]}],'next_cursor':None}
                if endpoint.endswith('/modules/51/items'):
                    return {'items':[{'id':'61','title':'First'},{'id':'62','title':'Second'}],'next_cursor':None}
                return await super().page(endpoint,**kwargs)
        result=await student_report(PartialContext(),'42','7',sections=['overview','progress','outcomes'])
        self.assertEqual(len(result['modules'][0]['items']),2)
        self.assertFalse(result['coverage']['outcomes']['complete'])
        self.assertEqual(result['outcomes'],[])
        self.assertEqual(result['grades']['current_score'],81.25)


class PrivateStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store('https://canvas.example.invalid', '7', self.root)

    def test_account_isolation_revision_and_private_mode(self):
        record = self.store.create('report', {'status': 'queued'})
        other = Store('https://canvas.example.invalid', '8', self.root)
        with self.assertRaises(ValueError):
            other.get('report', record['id'])
        self.store.update('report', record['id'], {'status': 'collecting'}, revision=1)
        with self.assertRaises(StateConflict):
            self.store.update('report', record['id'], {'status': 'completed'}, revision=1)
        if os.name != 'nt':
            self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.store.directory.stat().st_mode & 0o777, 0o700)

    def test_process_lease_and_restart_persistence(self):
        self.assertTrue(self.store.acquire('watcher', 'process-a'))
        self.assertFalse(self.store.acquire('watcher', 'process-b'))
        self.assertTrue(self.store.lease_status('watcher')['running'])
        record = self.store.create('report', {'status': 'queued'})
        restarted = Store('https://canvas.example.invalid', '7', self.root)
        self.assertEqual(restarted.get('report', record['id'])['status'], 'queued')
        self.store.release('watcher', 'process-a')
        self.assertTrue(restarted.acquire('watcher', 'process-b'))

    def test_retention_preserves_pending_drafts_and_marks_review_evidence_expired(self):
        job=self.store.create('report',{'status':'completed_with_gaps','snapshot':{'student':'Synthetic'}})
        evidence=self.store.create('evidence',{'job_id':job['id'],'text':'Synthetic work'})
        pending=self.store.create('activity',{'status':'draft','draft_reply':'Keep pending faculty draft'})
        resolved=self.store.create('activity',{'status':'posted','message':'Resolved synthetic message','draft_reply':'Resolved draft'})
        with self.store.connect() as db:
            db.execute("UPDATE records SET created_at='2020-01-01T00:00:00+00:00',updated_at='2020-01-01T00:00:00+00:00'")
        self.store.prune()
        self.assertEqual(self.store.get('activity',pending['id'])['draft_reply'],'Keep pending faculty draft')
        self.assertIsNone(self.store.get('activity',resolved['id'])['draft_reply'])
        self.assertTrue(self.store.get('report',job['id'])['evidence_expired'])
        self.assertIsNone(self.store.get('report',job['id'])['snapshot'])
        with self.assertRaises(ValueError): self.store.get('evidence',evidence['id'])

    def test_state_rejects_git_repository_and_path_identifiers(self):
        with self.assertRaises(ValueError):
            Store('https://canvas.example.invalid','7',Path(__file__).resolve().parents[1])
        with self.assertRaises(ValueError): self.store.delete_job('../../escape')


if __name__ == '__main__':
    unittest.main()
