"""Verify diagnostic privacy with synthetic data in isolated processes."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PrivateDiagnosticsTests(unittest.TestCase):
    def run_script(self, script):
        return subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src"),
                 "CANVAS_URL": "https://school.example",
                 "CANVAS_ACCESS_TOKEN": "synthetic-secret-token",
                 "FASTMCP_LOG_ENABLED": "true",
                 "FASTMCP_LOG_LEVEL": "DEBUG",
                 "FASTMCP_TELEMETRY_MODE": "native"},
            text=True, capture_output=True, timeout=30,
        )

    def test_logs_warnings_and_exception_chains_discard_payloads(self):
        result = self.run_script('''
import logging, warnings
from private_diagnostics import configure_private_diagnostics
configure_private_diagnostics()
private = "Synthetic Student synthetic.student@example.test 987654321 synthetic-secret-token"
class Unprintable:
    def __str__(self):
        raise AssertionError("Log payload must not be formatted")
logging.getLogger("fastmcp.server").warning("Bad argument %s: %s", private, Unprintable())
try:
    raise ValueError(private)
except ValueError:
    logging.getLogger("canvasAPI.base").exception(private, stack_info=True)
warnings.warn(private)
logging.getLogger(private).error(private, extra={"student": private})
# A dependency may configure its own handler after our initial setup.
from fastmcp.utilities.logging import configure_logging
configure_logging(level="DEBUG", enable_rich_tracebacks=True)
logging.getLogger("fastmcp.server").error(private)
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("Diagnostic details suppressed for privacy.", result.stderr)
        for private in ("Synthetic Student", "example.test", "987654321",
                        "synthetic-secret-token", "AssertionError", "Traceback"):
            self.assertNotIn(private, result.stderr)

    def test_startup_masks_unhandled_errors_and_disables_telemetry(self):
        result = self.run_script('''
import sys, types
def fail():
    import fastmcp
    if fastmcp.settings.telemetry_mode != "off":
        raise SystemExit(89)
    raise RuntimeError("Synthetic Student synthetic-secret-token /private/student-file")
server = types.ModuleType("server")
server.create_server = fail
sys.modules["server"] = server
from local import main
main()
''')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("internal error", result.stderr)
        for private in ("Synthetic Student", "synthetic-secret-token", "/private/student-file", "Traceback"):
            self.assertNotIn(private, result.stderr)


if __name__ == "__main__":
    unittest.main()
