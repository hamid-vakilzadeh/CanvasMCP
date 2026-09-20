"""Explicit student-record opt-in for existing synthetic integration suites."""

import os
import unittest
from unittest.mock import patch


def enable_synthetic_student_records():
    environment = patch.dict(os.environ, {'FERPA': 'true'})
    environment.start()
    unittest.addModuleCleanup(environment.stop)
