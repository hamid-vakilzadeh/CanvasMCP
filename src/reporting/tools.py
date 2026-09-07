"""Discoverable reporting tools, canonical references and the MCP App bridge."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from fastmcp import Context
from fastmcp.apps import AppConfig, ResourceCSP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from discussion_watch import Watcher
from reporting.render import render_review
from reporting.reviews import Reviews
from reporting.runtime import runtime
from tools.assistant import _assistant_tool, READ_ONLY

APP_URI = 'ui://canvas/student-dashboard.html'
TEMPLATES = Path(__file__).parent / 'templates'
LOCAL_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)


class Finding(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Literal['strength', 'learning_gap', 'submission_pattern', 'participation', 'support']
    interpretation: Literal['observation', 'interpretation', 'recommendation']
    text: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class MeasuredModelUsage(BaseModel):
    """Optional usage copied from the AI client's actual response metadata, never an estimate."""
    model_config = ConfigDict(extra='forbid')
    model: str = Field(min_length=1)
    source: str = Field(min_length=1)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)


class DashboardRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['courses', 'students', 'report', 'start_review', 'review_status', 'list_reviews',
                    'cancel_review', 'delete_review', 'resume_review', 'export_review']
    course_id: str | None = None
    student_id: str | None = None
    job_id: str | None = None
    search: str = ''
    cursor: str | None = None
    sections: list[Literal['overview', 'assignments', 'progress', 'activity', 'rubrics', 'outcomes']] | None = None
    refresh: bool = False


async def dashboard_request(request: DashboardRequest, service=runtime) -> dict:
    """The two UI adapters share exactly this allowlisted operation surface."""
    action = request.action
    if action == 'courses':
        return await service.courses()
    if action in {'students', 'report', 'start_review'} and not request.course_id:
        raise ValueError('Choose a course first')
    if action in {'report', 'start_review'} and not request.student_id:
        raise ValueError('Choose a student first')
    if action == 'students':
        return await service.students(request.course_id, request.search, request.cursor)
    if action == 'report':
        return await service.report(request.course_id, request.student_id, request.sections, request.refresh)
    if action == 'start_review':
        return await service.start_review(request.course_id, request.student_id)
    store = await service.store()
    if action == 'list_reviews':
        match = {k: v for k, v in {'course_id': request.course_id, 'student_id': request.student_id}.items() if v}
        page = store.page('report', match=match, cursor=request.cursor)
        page['items'] = [Reviews(store).status(j['id']) for j in page['items']]
        return page
    if not request.job_id:
        raise ValueError('A review job ID is required')
    if action == 'review_status':
        return Reviews(store).status(request.job_id)
    if action == 'cancel_review':
        return await service.cancel(request.job_id)
    if action == 'delete_review':
        return await service.delete(request.job_id)
    if action == 'resume_review':
        return await service.resume(request.job_id)
    if action == 'export_review':
        job = store.get('report', request.job_id)
        if not job.get('report_path'):
            raise ValueError('The AI client has not rendered this report yet')
        path = store.directory / f"report-{job['id']}.html"
        return {'html': path.read_text(encoding='utf-8'), 'filename': 'canvas-learning-review.html', 'status': job['status']}
    raise ValueError('Unsupported dashboard operation')


class ReportingTools:
    def __init__(self, mcp):
        for name in (
            'canvas_get_report_template', 'canvas_get_student_report', 'canvas_get_learning_review_batch',
            'canvas_manage_learning_review', 'canvas_start_learning_review', 'canvas_record_learning_review_analysis',
            'canvas_render_learning_review', 'canvas_manage_discussion_watch', 'canvas_list_discussion_activity',
            'canvas_get_discussion_activity', 'canvas_record_discussion_review', 'canvas_plan_discussion_draft',
        ):
            mcp.tool(_assistant_tool(getattr(self, name)), tags={'reports', 'local-workflow'},
                     annotations=READ_ONLY if name in {'canvas_get_report_template', 'canvas_get_student_report',
                                                       'canvas_list_discussion_activity'} else LOCAL_WRITE)
        mcp.tool(_assistant_tool(self.canvas_open_student_dashboard), tags={'reports'},
                 app=AppConfig(resource_uri=APP_URI), annotations=LOCAL_WRITE)
        mcp.tool(_assistant_tool(self.canvas_dashboard_data), tags={'reports', 'ui'},
                 app=AppConfig(resource_uri=APP_URI, visibility=['app']), annotations=LOCAL_WRITE)

        @mcp.resource(APP_URI, app=AppConfig(csp=ResourceCSP(connect_domains=[], resource_domains=[])),
                      name='Canvas student dashboard')
        def dashboard_html() -> str:
            from reporting.web import app_html
            return app_html('mcp')

        @mcp.resource('canvas://reports/templates', name='Canvas report templates')
        def report_catalog() -> dict:
            return {'templates': [{'name': name, 'uri': f'canvas://reports/templates/{name}'}
                                  for name in ('dashboard', 'learning-review')],
                    'fallback_tool': 'canvas_get_report_template'}

        @mcp.resource('canvas://reports/templates/{name}', name='Canvas reporting guidance')
        def report_template(name: str) -> str:
            return self.template(name)

        @mcp.resource('canvas://courses/{course_id}/students/{student_id}/report', name='Student report data')
        async def report_data(course_id: str, student_id: str) -> dict:
            return await runtime.report(course_id, student_id)

    @staticmethod
    def template(name):
        if name not in {'dashboard', 'learning-review'}:
            raise ValueError('Choose dashboard or learning-review')
        return (TEMPLATES / f'{name}.md').read_text(encoding='utf-8')

    async def canvas_get_report_template(self, name: Literal['dashboard', 'learning-review']) -> str:
        """Read canonical student report semantics, evidence workflow and presentation guidance."""
        return self.template(name)

    async def canvas_get_student_report(self, course_id: str, student_id: str,
        sections: list[Literal['overview', 'assignments', 'progress', 'activity', 'rubrics', 'outcomes']] | None = None,
        refresh: bool = False) -> dict:
        """Get complete student dashboard data; optional sections add activity, rubric feedback or outcomes."""
        return await runtime.report(course_id, student_id, sections, refresh)

    async def canvas_open_student_dashboard(self, ctx: Context, course_id: str | None = None,
                                            student_id: str | None = None,
                                            mode: Literal['auto', 'browser', 'embedded'] = 'auto') -> dict:
        """Open an interactive student dashboard. Native MCP App when supported; otherwise private localhost UI."""
        supported = ctx.client_supports_extension('io.modelcontextprotocol/ui')
        if mode == 'embedded' and not supported:
            return {'status': 'host_unsupported', 'next_step': 'Call again with mode=browser for the local browser dashboard.'}
        result = {'course_id': course_id, 'student_id': student_id,
                  'dashboard_tool': 'canvas_dashboard_data', 'host_supports_app': supported}
        if mode == 'browser' or not supported:
            from reporting.web import start_dashboard
            result.update(await start_dashboard(runtime))
            from urllib.parse import urlencode
            if course_id or student_id:
                base, fragment = result['url'].split('#', 1)
                result['url'] = base + '?' + urlencode({k: v for k, v in {'course_id': course_id, 'student_id': student_id}.items() if v}) + '#' + fragment
        else:
            result.update(status='ready', mode='embedded')
        return result

    async def canvas_dashboard_data(self, request: DashboardRequest) -> dict:
        """UI-only dashboard operations. No Canvas mutation or model invocation."""
        return await dashboard_request(request)

    async def canvas_start_learning_review(self, course_id: str, student_id: str) -> dict:
        """Queue comprehensive evidence collection; accepted is not completed. Existing AI client analyzes later."""
        return await runtime.start_review(course_id, student_id)

    async def canvas_manage_learning_review(self,
        action: Literal['status', 'list', 'resume', 'cancel', 'delete', 'analyses'],
        job_id: str | None = None, cursor: str | None = None) -> dict:
        """Inspect, resume, cancel or delete private review jobs; retrieve saved analyses before final synthesis."""
        store = await runtime.store()
        if action == 'list':
            page = store.page('report', cursor=cursor)
            page['items'] = [Reviews(store).status(j['id']) for j in page['items']]
            return page
        if not job_id:
            raise ValueError('job_id is required for this action')
        if action == 'status':
            return Reviews(store).status(job_id)
        if action == 'analyses':
            store.get('report', job_id)
            return store.page('analysis', match={'job_id': job_id}, cursor=cursor)
        return await getattr(runtime, action)(job_id)

    async def canvas_get_learning_review_batch(self, job_id: str,
        max_characters: Annotated[int, Field(ge=12000, le=200000)] = 24000) -> dict:
        """Retrieve the next unread evidence batch. Read and save analysis before requesting the next batch."""
        return Reviews(await runtime.store()).next_batch(job_id, max_characters=max_characters)

    async def canvas_record_learning_review_analysis(self, job_id: str, evidence_ids: list[str],
        findings: list[Finding], summary: str, model_usage: MeasuredModelUsage | None = None) -> dict:
        """Save the AI client's review of retrieved evidence, with evidence-linked observations and recommendations."""
        return Reviews(await runtime.store()).record_analysis(job_id, evidence_ids,
                                      [f.model_dump() for f in findings], summary,
                                      model_usage=model_usage.model_dump() if model_usage else None)

    async def canvas_render_learning_review(self, job_id: str, overview: str,
        findings: list[Finding] | None = None, follow_up_questions: list[str] | None = None,
        allow_incomplete: bool = False) -> dict:
        """Render a printable faculty HTML review; refuses completion when evidence remains unread."""
        return render_review(await runtime.store(), job_id, overview=overview,
                             findings=[f.model_dump() for f in findings] if findings is not None else None,
                             follow_up_questions=follow_up_questions, allow_incomplete=allow_incomplete)

    async def canvas_manage_discussion_watch(self, action: Literal['add', 'list', 'pause', 'resume', 'delete', 'status'],
        course_id: str | None = None, topic_id: str | None = None, watch_id: str | None = None,
        interval_seconds: Annotated[int, Field(ge=30, le=86400)] = 120) -> dict:
        """Manage local discussion polling. Run canvas-mcp watch separately; the MCP process does not poll automatically."""
        store = await runtime.store()
        if action == 'status':
            return {**store.lease_status('watcher'), 'active_watches': sum(w['status'] == 'active' for w in store.all('watch'))}
        if action == 'list':
            return {'items': [{k: v for k, v in w.items() if k != 'baseline'} for w in store.all('watch')]}
        if action == 'add':
            if not course_id or not topic_id:
                raise ValueError('course_id and topic_id are required')
            async with runtime.client_factory() as client:
                watch = await Watcher(store, runtime.user_id).configure(client, course_id, topic_id, interval_seconds=interval_seconds)
            return {k: v for k, v in watch.items() if k != 'baseline'}
        if not watch_id:
            raise ValueError('watch_id is required')
        store.get('watch', watch_id)
        if action == 'delete':
            if store.lease_status('watcher')['running']:
                raise ValueError('Stop the local watcher process before deleting a watch and its queue')
            if any(a['watch_id'] == watch_id and a['status'] in {'posting', 'uncertain'} for a in store.all('activity')):
                raise ValueError('Resolve uncertain discussion publications before deleting their records')
            store.delete('watch', watch_id)
            for item in store.all('activity'):
                if item['watch_id'] == watch_id:
                    store.delete('activity', item['id'])
            return {'status': 'deleted'}
        watch = store.update('watch', watch_id, {'status': 'active' if action == 'resume' else 'paused', 'next_poll_at': 0})
        return {k: v for k, v in watch.items() if k != 'baseline'}

    async def canvas_list_discussion_activity(self, status: str | None = 'pending', cursor: str | None = None,
                                            limit: Annotated[int, Field(ge=1, le=100)] = 25) -> dict:
        """List queued discussion changes for AI triage; use get_discussion_activity for full thread context."""
        page = (await runtime.store()).page('activity', status=status, cursor=cursor, limit=limit)
        page['items'] = [{k: v for k, v in a.items() if k not in {'message', 'draft_reply', 'reason'}} for a in page['items']]
        return page

    async def canvas_get_discussion_activity(self, activity_id: str) -> dict:
        """Inspect current discussion context before drafting or resolving an uncertain publication."""
        store = await runtime.store()
        async with runtime.client_factory() as client:
            return await Watcher(store, runtime.user_id).inspect(client, activity_id)

    async def canvas_record_discussion_review(self, activity_id: str, revision: int,
        decision: Literal['draft', 'ignore', 'confirmed_posted', 'confirmed_absent'], reason: str,
        draft_reply: str | None = None, reply_id: str | None = None) -> dict:
        """Save a draft or triage decision. Resolve uncertain writes only after faculty inspection; never sends a message."""
        store = await runtime.store()
        async with runtime.client_factory() as client:
            return await Watcher(store, runtime.user_id).review(client, activity_id, revision, decision, reason, draft_reply, reply_id)

    async def canvas_plan_discussion_draft(self, activity_id: str) -> dict:
        """Recheck a saved faculty draft and prepare a short-lived reply plan for canvas_apply_change."""
        store = await runtime.store()
        async with runtime.client_factory() as client:
            return await Watcher(store, runtime.user_id).plan_draft(client, activity_id)
