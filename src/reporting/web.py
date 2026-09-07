"""Optional loopback-only dashboard. Canvas credentials never enter the browser."""

from __future__ import annotations

import asyncio
import json
import secrets
import socket
from contextlib import contextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route
from starlette.middleware.base import BaseHTTPMiddleware

UI = Path(__file__).parent / 'ui'


def app_html(mode: str, *, nonce: str = '') -> str:
    template = (UI / 'index.html').read_text(encoding='utf-8')
    script = (UI / 'dashboard.js').read_text(encoding='utf-8').replace('</script', '<\\/script')
    style = (UI / 'dashboard.css').read_text(encoding='utf-8')
    config = json.dumps({'mode': mode})
    return template.replace('{{STYLE}}', style).replace('{{SCRIPT}}', script).replace('{{CONFIG}}', config).replace('{{NONCE}}', nonce)


def create_dashboard_app(service, *, port: int, bootstrap_secret: str):
    origin = f'http://127.0.0.1:{port}'
    cookie = secrets.token_urlsafe(32)

    async def index(request):
        nonce = secrets.token_urlsafe(18)
        response = HTMLResponse(app_html('browser', nonce=nonce))
        response.headers['Content-Security-Policy'] = (
            f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
            "connect-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'none'")
        return response

    async def session(request):
        data = await request.json()
        if not isinstance(data, dict) or not secrets.compare_digest(str(data.get('secret', '')), bootstrap_secret):
            return JSONResponse({'error': 'Invalid dashboard session'}, status_code=401)
        response = JSONResponse({'status': 'connected'})
        response.set_cookie('canvas_dashboard', cookie, httponly=True, samesite='strict', path='/')
        return response

    async def api(request):
        from reporting.tools import DashboardRequest, dashboard_request
        try:
            payload = DashboardRequest.model_validate(await request.json())
            return JSONResponse(await dashboard_request(payload, service))
        except ValueError as exc:
            # Pydantic errors may include input values; only our own ValueErrors are safe text.
            message = str(exc) if type(exc) is ValueError else 'Invalid dashboard request'
            return JSONResponse({'error': message}, status_code=400)
        except Exception:
            return JSONResponse({'error': 'Canvas data could not be retrieved. Check connection and permissions.'}, status_code=502)

    app = Starlette(routes=[Route('/', index), Route('/session', session, methods=['POST']), Route('/api', api, methods=['POST'])])

    async def protect(request: Request, call_next):
        if request.headers.get('host') != f'127.0.0.1:{port}':
            return Response('Invalid host', status_code=403)
        if request.method != 'GET':
            if request.headers.get('origin') != origin or request.headers.get('x-canvas-dashboard') != '1':
                return Response('Invalid origin', status_code=403)
            try:
                if int(request.headers.get('content-length', '0')) > 2_000_000:
                    return Response('Request too large', status_code=413)
            except ValueError:
                return Response('Invalid request', status_code=400)
        if request.url.path == '/api' and not secrets.compare_digest(request.cookies.get('canvas_dashboard', ''), cookie):
            return JSONResponse({'error': 'Open the dashboard link from your MCP client again.'}, status_code=401)
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse({'error': 'Dashboard request could not be completed'}, status_code=400)
        response.headers.update({'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
                                 'X-Content-Type-Options': 'nosniff', 'Cross-Origin-Resource-Policy': 'same-origin'})
        return response

    app.add_middleware(BaseHTTPMiddleware, dispatch=protect)
    return app


_servers: list[tuple] = []


async def start_dashboard(service) -> dict:
    """Start within the requesting local process, avoiding a second credential handoff."""
    import uvicorn
    class EmbeddedServer(uvicorn.Server):
        @contextmanager
        def capture_signals(self):
            # The MCP client / asyncio runner owns process shutdown.
            yield
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    secret = secrets.token_urlsafe(32)
    app = create_dashboard_app(service, port=port, bootstrap_secret=secret)
    server = EmbeddedServer(uvicorn.Config(app, host='127.0.0.1', port=port, log_config=None,
                                           access_log=False, log_level='critical', lifespan='off'))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    for _ in range(100):
        if server.started:
            break
        if task.done():
            sock.close()
            raise ValueError('The local dashboard could not start')
        await asyncio.sleep(.01)
    if not server.started:
        server.should_exit = True
        raise ValueError('The local dashboard did not start in time')
    _servers.append((server, task, sock))
    return {'status': 'ready', 'mode': 'browser', 'url': f'http://127.0.0.1:{port}/#{secret}',
            'lifetime': 'Available while this local Canvas MCP process remains running.'}


async def close_dashboards():
    for server, _, _ in _servers:
        server.should_exit = True
    await asyncio.gather(*(task for _, task, _ in _servers), return_exceptions=True)
    for _, _, sock in _servers:
        sock.close()
    _servers.clear()
