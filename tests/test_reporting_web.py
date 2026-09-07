import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fastmcp import Client
from fastmcp.exceptions import ToolError
from httpx2 import AsyncClient, ASGITransport
from report_fixtures import SyntheticCanvas
from reporting.runtime import Runtime
from reporting.tools import ReportingTools, APP_URI
from reporting.web import create_dashboard_app
from server import create_server


class ReportingWebTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.runtime=Runtime(SyntheticCanvas,Path(self.temp.name)); self.addAsyncCleanup(self.runtime.close)
        self.app=create_dashboard_app(self.runtime,port=8765,bootstrap_secret='synthetic-bootstrap')
        self.client=AsyncClient(transport=ASGITransport(app=self.app),base_url='http://127.0.0.1:8765')
        self.addAsyncCleanup(self.client.aclose)
        self.headers={'Origin':'http://127.0.0.1:8765','X-Canvas-Dashboard':'1'}

    async def test_browser_origin_host_session_and_no_credentials(self):
        html=await self.client.get('/')
        self.assertNotIn(SyntheticCanvas.access_token,html.text)
        self.assertIn("frame-ancestors 'none'",html.headers['content-security-policy'])
        self.assertEqual(html.headers['cache-control'],'no-store')
        denied=await self.client.post('/api',headers=self.headers,json={'action':'courses'})
        self.assertEqual(denied.status_code,401)
        for headers in ({'Origin':'https://evil.example.invalid','X-Canvas-Dashboard':'1'}, {'Origin':'http://127.0.0.1:8765'}):
            self.assertEqual((await self.client.post('/session',headers=headers,json={'secret':'synthetic-bootstrap'})).status_code,403)
        self.assertEqual((await self.client.get('/',headers={'Host':'evil.example.invalid'})).status_code,403)
        connected=await self.client.post('/session',headers=self.headers,json={'secret':'synthetic-bootstrap'})
        self.assertIn('HttpOnly',connected.headers['set-cookie'])
        self.assertIn('SameSite=strict',connected.headers['set-cookie'])
        result=await self.client.post('/api',headers=self.headers,json={'action':'report','course_id':'42','student_id':'7'})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['student']['id'],'7')
        self.assertNotIn(SyntheticCanvas.access_token,result.text)
        invalid=await self.client.post('/api',headers=self.headers,json={'action':'post_reply','message':'forbidden'})
        self.assertEqual(invalid.status_code,400)

    async def test_resources_search_and_app_bridge(self):
        server=create_server()
        async with Client(server) as client:
            resources=await client.list_resources()
            self.assertIn(APP_URI,[str(r.uri) for r in resources])
            template=await client.read_resource('canvas://reports/templates/learning-review')
            self.assertEqual(template[0].text,ReportingTools.template('learning-review'))
            result=await client.call_tool('canvas_search_tools',{'query':'student report dashboard'})
            self.assertIn('canvas_get_student_report',str(result))
            hidden=await client.call_tool('canvas_search_tools',{'query':'canvas_dashboard_data UI-only dashboard'})
            self.assertNotIn('"name": "canvas_dashboard_data"',str(hidden))
            # App-only tools remain callable directly through the native host.
            from unittest.mock import patch
            with patch('reporting.tools.runtime',self.runtime):
                # dashboard_request has an explicit service default; patch the function for transport wiring only.
                from reporting.tools import dashboard_request
                async def handle(request): return await dashboard_request(request,self.runtime)
                with patch('reporting.tools.dashboard_request',handle):
                    result=await client.call_tool('canvas_dashboard_data',{'request':{'action':'report','course_id':'42','student_id':'7'}})
                    self.assertEqual(result.data['student']['id'],'7')

    async def test_dashboard_entry_detects_host_and_offers_browser_fallback(self):
        from unittest.mock import AsyncMock, patch
        provider=object.__new__(ReportingTools)
        class Context:
            def __init__(self,supported): self.supported=supported
            def client_supports_extension(self,name):
                assert name=='io.modelcontextprotocol/ui'
                return self.supported
        embedded=await provider.canvas_open_student_dashboard(Context(True),'42','7')
        self.assertEqual(embedded['mode'],'embedded')
        unsupported=await provider.canvas_open_student_dashboard(Context(False),mode='embedded')
        self.assertEqual(unsupported['status'],'host_unsupported')
        with patch('reporting.web.start_dashboard',AsyncMock(return_value={'mode':'browser','url':'http://127.0.0.1:9999/#synthetic'})):
            fallback=await provider.canvas_open_student_dashboard(Context(False),'42','7')
        self.assertEqual(fallback['mode'],'browser')
        self.assertIn('course_id=42',fallback['url'])
        self.assertIn('student_id=7',fallback['url'])

if __name__ == '__main__': unittest.main()
