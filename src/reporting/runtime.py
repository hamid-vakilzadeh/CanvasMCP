"""Per-process reporting service; durable records remain shared across local processes."""

from __future__ import annotations

import asyncio
import copy
import time
from pathlib import Path

from canvas_client import AsyncCanvasClient
from reporting.common import sid
from reporting.data import all_pages, student_report
from reporting.reviews import Reviews
from reporting.state import Store


class Runtime:
    def __init__(self, client_factory=None, state_directory: Path | None = None):
        self.client_factory = client_factory or AsyncCanvasClient.from_environment
        self.state_directory = state_directory
        self._store = None
        self._identity_lock = asyncio.Lock()
        self.tasks: dict[str, asyncio.Task] = {}
        self.cache: dict[tuple, tuple[float, dict]] = {}
        self.user_id = None
        self._last_prune = float('-inf')

    async def store(self) -> Store:
        async with self._identity_lock:
            if self._store is None:
                async with self.client_factory() as client:
                    user = await client.get('/api/v1/users/self')
                    self.user_id = sid(user['id'])
                    self._store = Store(client.base_url, self.user_id, self.state_directory)
            if time.monotonic() - self._last_prune > 3600:
                self._store.prune()
                self._last_prune = time.monotonic()
        return self._store

    async def courses(self) -> dict:
        async with self.client_factory() as client:
            result = await all_pages(client, '/api/v1/courses', {'enrollment_type': 'teacher', 'include[]': ['term']})
        result['items'] = [{k: c[k] for k in ('id', 'name', 'course_code', 'term') if k in c} for c in result['items']]
        return result

    async def students(self, course_id: str, search: str = '', cursor: str | None = None) -> dict:
        params = {'enrollment_type[]': ['student'], 'include[]': ['enrollments']}
        if search.strip():
            params['search_term'] = search.strip()
        async with self.client_factory() as client:
            result = await client.page(f'/api/v1/courses/{sid(course_id)}/users', params=params, cursor=cursor, limit=100)
        result['items'] = [{'id': str(s['id']), 'name': s.get('name', 'Student')} for s in result['items']]
        return result

    async def report(self, course_id: str, student_id: str, sections: list[str] | None = None,
                     refresh: bool = False) -> dict:
        sections = sections or ['overview', 'assignments', 'progress']
        started = time.monotonic()
        key = (sid(course_id), sid(student_id), tuple(sorted(sections)))
        if not refresh and key in self.cache and time.monotonic() - self.cache[key][0] < 60:
            result = copy.deepcopy(self.cache[key][1])
            result['cache'] = {'hit': True, 'max_age_seconds': 60}
            result['metrics']['logical_canvas_calls'] = 0
            result['metrics']['submission_page_calls'] = 0
            result['metrics']['elapsed_seconds'] = round(time.monotonic() - started, 3)
            return result
        async with self.client_factory() as client:
            result = await student_report(client, course_id, student_id, sections=sections)
        result['cache'] = {'hit': False, 'max_age_seconds': 60}
        self.cache[key] = (time.monotonic(), copy.deepcopy(result))
        if len(self.cache) > 20:
            self.cache.pop(next(iter(self.cache)))
        return result

    async def start_review(self, course_id: str, student_id: str) -> dict:
        reviews = Reviews(await self.store())
        job = reviews.create(course_id, student_id)
        return await self.resume(job['id'])

    async def resume(self, job_id: str) -> dict:
        store = await self.store()
        job = store.get('report', job_id)
        if job.get('evidence_expired'):
            raise ValueError('Evidence expired. Create a new review to collect fresh work.')
        if job['status'] == 'cancelled':
            store.update('report', job_id, {'status': 'queued'})
        if job_id not in self.tasks or self.tasks[job_id].done():
            async def collect():
                try:
                    async with self.client_factory() as client:
                        await Reviews(store).collect(client, job_id)
                except Exception:
                    # A fixed message only; no request payload in logs.
                    store.update('report', job_id, {'status': 'collection_interrupted', 'error': 'Resume collection to retry.'})
            self.tasks[job_id] = asyncio.create_task(collect())
            def finished(task):
                if self.tasks.get(job_id) is task:
                    self.tasks.pop(job_id, None)
            self.tasks[job_id].add_done_callback(finished)
        return {**Reviews(store).status(job_id), 'accepted': True,
                'next_step': 'Check status. After collection, the AI client must retrieve and analyze every evidence batch.'}

    async def cancel(self, job_id: str) -> dict:
        store = await self.store()
        store.update('report', job_id, {'status': 'cancelled'})
        task = self.tasks.get(job_id)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        return Reviews(store).status(job_id)

    async def delete(self, job_id: str) -> dict:
        store = await self.store()
        await self.cancel(job_id)
        # A collector in another local process must release its lease first.
        if store.lease_status(f'report:{job_id}')['running']:
            return {'job_id': job_id, 'status': 'deletion_pending',
                    'next_step': 'Collection was cancelled. Retry deletion after the other process stops.'}
        store.delete_job(job_id)
        self.cache.clear()
        return {'job_id': job_id, 'status': 'deleted'}

    async def close(self):
        for task in list(self.tasks.values()):
            task.cancel()
        await asyncio.gather(*list(self.tasks.values()), return_exceptions=True)
        self.cache.clear()


runtime = Runtime()
