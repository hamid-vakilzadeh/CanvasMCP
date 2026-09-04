"""Exercise the real stdio process against a fake Canvas API, with external IO blocked."""

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import canvas_credentials


def clean_env():
    return {
        key: value for key, value in os.environ.items()
        if key not in {"CANVAS_URL", "CANVAS_ACCESS_TOKEN", "FASTMCP_SERVER_AUTH"}
    }


class LocalConfigTests(unittest.TestCase):
    def setUp(self):
        self.state = patch.object(canvas_credentials, "_credentials", None)
        self.state.start()
        self.addCleanup(self.state.stop)

    def test_normalizes_and_returns_canvas_credentials(self):
        canvas_credentials.configure_canvas_credentials(
            " https://school.example/ ", " test-token "
        )
        self.assertEqual(
            canvas_credentials.get_canvas_credentials(),
            ("https://school.example", "test-token"),
        )

    def test_accepts_canvas_api_url_and_stores_instance_url(self):
        canvas_credentials.configure_canvas_credentials(
            "https://school.example/api/v1/", "test-token"
        )
        self.assertEqual(
            canvas_credentials.get_canvas_credentials(),
            ("https://school.example", "test-token"),
        )

    def test_rejects_missing_credentials_and_invalid_urls(self):
        for url, token in [
            (None, "test-token"), ("https://school.example", "  "),
            ("school.example", "test-token"), ("file:///tmp/canvas", "test-token"),
            ("https://user:secret@school.example", "test-token"),
            ("https://school.example?token=secret", "test-token"),
            ("https://school.example/#fragment", "test-token"),
            ("https://school.example:bad", "test-token"),
            ("https://school.example", "test\ntoken"),
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                canvas_credentials.configure_canvas_credentials(url, token)
        self.assertIsNone(canvas_credentials._credentials)

    def test_startup_errors_are_on_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "src/local.py")],
                cwd=directory, env=clean_env(), capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("CANVAS_URL", result.stderr)


class LocalProtocolTests(unittest.TestCase):
    def test_stdio_tools_resources_and_direct_canvas_request(self):
        calls = []

        class CanvasHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                calls.append((self.path, self.headers.get("Authorization")))
                if self.path.startswith("/api/v1/courses"):
                    payload = [{"id": 42, "name": "Local test course", "term": {"id": 1, "name": "Fall"}}]
                    self.send_response(200)
                else:
                    payload = {"error": "Unexpected test endpoint"}
                    self.send_response(404)
                body = json.dumps(payload).encode()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        canvas = ThreadingHTTPServer(("127.0.0.1", 0), CanvasHandler)
        threading.Thread(target=canvas.serve_forever, daemon=True).start()
        self.addCleanup(canvas.server_close)
        self.addCleanup(canvas.shutdown)

        with tempfile.TemporaryDirectory() as directory:
            workdir = Path(directory)
            # Fail the subprocess on outgoing non-Canvas requests or any attempt
            # to open a listener. The server must connect only to Canvas.
            (workdir / "sitecustomize.py").write_text(
                "import socket\n"
                "original_connect = socket.socket.connect\n"
                "def connect(sock, address):\n"
                f"    if address != ('127.0.0.1', {canvas.server_port}):\n"
                "        raise RuntimeError('Non-Canvas connection attempted')\n"
                "    return original_connect(sock, address)\n"
                "socket.socket.connect = connect\n"
                "def bind(*args):\n"
                "    raise RuntimeError('Network listener attempted')\n"
                "socket.socket.bind = bind\n"
            )
            env = {
                **clean_env(), "PYTHONPATH": str(workdir),
                "CANVAS_URL": f"http://127.0.0.1:{canvas.server_port}/",
                "CANVAS_ACCESS_TOKEN": "local-test-token",
                "FASTMCP_SERVER_AUTH": "invalid-test-provider",
                "NO_PROXY": "127.0.0.1",
            }
            # Override to verify an installed npm package with this same protocol test.
            command = json.loads(os.environ["TEST_MCP_COMMAND_JSON"]) if "TEST_MCP_COMMAND_JSON" in os.environ else [
                sys.executable, str(ROOT / "src/local.py")
            ]
            with tempfile.TemporaryFile(mode="w+") as stderr:
                process = subprocess.Popen(
                    command, cwd=directory,
                    env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr, text=True,
                )
                lines = queue.Queue()

                def read_stdout():
                    for line in process.stdout:
                        lines.put(line)
                    lines.put(None)

                reader = threading.Thread(target=read_stdout, daemon=True)
                reader.start()

                def send(message):
                    process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
                    process.stdin.flush()

                def request(request_id, method, params):
                    send({"id": request_id, "method": method, "params": params})
                    while True:
                        line = lines.get(timeout=30)
                        if line is None:
                            stderr.seek(0)
                            self.fail("MCP process exited early: " + stderr.read())
                        response = json.loads(line)  # Any stdout logging fails this test.
                        if response.get("id") == request_id:
                            self.assertNotIn("error", response, response)
                            return response["result"]

                try:
                    initialized = request(1, "initialize", {
                        "protocolVersion": "2025-03-26", "capabilities": {},
                        "clientInfo": {"name": "local-install-test", "version": "1.0"},
                    })
                    self.assertEqual(initialized["serverInfo"]["name"], "Canvas-MCP")
                    send({"method": "notifications/initialized"})
                    tools = request(2, "tools/list", {})["tools"]
                    names = {tool["name"] for tool in tools}
                    self.assertEqual(
                        names,
                        {
                            "canvas_capabilities",
                            "canvas_list_courses",
                            "canvas_get_course_structure",
                            "canvas_list_course_people",
                            "canvas_get_student_snapshot",
                            "canvas_analyze_student_engagement",
                            "canvas_list_grading_queue",
                            "canvas_get_submission_review",
                            "canvas_list_inbox",
                            "canvas_get_conversation",
                            "canvas_plan_communication",
                            "canvas_plan_announcement_change",
                            "canvas_plan_page_change",
                            "canvas_plan_assignment_change",
                            "canvas_plan_discussion_change",
                            "canvas_plan_module_change",
                            "canvas_plan_quiz_change",
                            "canvas_plan_file_upload",
                            "canvas_plan_course_copy",
                            "canvas_plan_grade_change",
                            "canvas_apply_change",
                            "canvas_search_tools",
                            "canvas_call_tool",
                        },
                    )
                    self.assertNotIn("create_page", names)
                    result = request(3, "tools/call", {"name": "canvas_list_courses", "arguments": {}})
                    self.assertFalse(result.get("isError"), result)
                    self.assertIn("Local test course", result["content"][0]["text"])
                    self.assertEqual(len(calls), 1)
                    self.assertTrue(calls[0][0].startswith("/api/v1/courses?"))
                    self.assertEqual(calls[0][1], "Bearer local-test-token")
                    reference = request(4, "tools/call", {
                        "name": "canvas_call_tool",
                        "arguments": {"name": "get_canvas_content_creation_rules", "arguments": {}},
                    })
                    self.assertIn("Canvas Content Creation Reference", reference["content"][0]["text"])
                    self.assertNotIn("Error reading", reference["content"][0]["text"])
                    resources = request(5, "resources/list", {})
                    self.assertIn("resource://content-creation-reference", [r["uri"] for r in resources["resources"]])
                    content = request(6, "resources/read", {"uri": "resource://content-creation-reference"})
                    self.assertIn("html", content["contents"][0]["text"].lower())
                    prompts = request(7, "prompts/list", {})
                    self.assertIn("build_canvas_course", [p["name"] for p in prompts["prompts"]])
                    process.stdin.close()
                    self.assertEqual(process.wait(timeout=10), 0)
                    reader.join(timeout=5)
                    while not lines.empty():
                        line = lines.get_nowait()
                        if line is not None:
                            json.loads(line)
                    stderr.seek(0)
                    diagnostics = stderr.read()
                    self.assertNotIn("local-test-token", diagnostics)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)
                    if not process.stdin.closed:
                        process.stdin.close()
                    process.stdout.close()


if __name__ == "__main__":
    unittest.main()
