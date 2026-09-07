"""Synthetic-only browser fixture. Never imports or configures user credentials."""
import atexit
import asyncio
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route
import uvicorn
from report_fixtures import SyntheticCanvas
from reporting.runtime import Runtime
from reporting.web import app_html, create_dashboard_app
from reporting.reviews import Reviews
from reporting.render import render_review

temporary=tempfile.TemporaryDirectory(prefix='canvas-synthetic-ui-')
atexit.register(temporary.cleanup)
runtime=Runtime(SyntheticCanvas,Path(temporary.name))
app=create_dashboard_app(runtime,port=8765,bootstrap_secret='synthetic-ui-session')

async def host(request):
    return HTMLResponse('<!doctype html><html lang="en"><head><title>Synthetic MCP App host</title></head><body style="margin:0"><iframe id="app" title="Canvas dashboard" sandbox="allow-scripts allow-same-origin" style="width:100%;height:1800px;border:0"></iframe><script type="module" src="/test-host.js"></script></body></html>')

async def host_script(request):
    return Response(Path('/private/tmp/canvas-test-host.js').read_text(),media_type='application/javascript')

async def native(request):
    return HTMLResponse(app_html('mcp'))

async def complete(request):
    store=await runtime.store()
    for job in store.all('report'):
        if not job.get('collection_complete'):
            continue
        batch=Reviews(store).next_batch(job['id'],max_characters=200000)
        if batch['evidence']:
            Reviews(store).record_analysis(job['id'],[e['id'] for e in batch['evidence']],[],
                                           'Synthetic UI fixture; this is not an AI evaluation.')
        render_review(store,job['id'],overview='Synthetic printable report for browser verification.')
    return JSONResponse({'status':'rendered'})

app.router.routes.extend([Route('/test-host',host),Route('/test-host.js',host_script),Route('/test-native',native),Route('/test-complete',complete)])
if __name__=='__main__': uvicorn.run(app,host='127.0.0.1',port=8765,access_log=False,log_level='critical')
