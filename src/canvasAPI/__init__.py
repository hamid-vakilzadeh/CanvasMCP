from .base import CanvasAPIBase
from .course.courses import CoursesAPI, courses
from .calendar.account_calendars import AccountCalendarsAPI, account_calendars
from .assignment.assignment_extensions import (
    AssignmentExtensionsAPI,
    assignment_extensions,
)

__all__ = [
    "CanvasAPIBase",
    "CoursesAPI",
    "courses",
    "AccountCalendarsAPI",
    "account_calendars",
    "AssignmentExtensionsAPI",
    "assignment_extensions",
]
