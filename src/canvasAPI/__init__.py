"""Canvas LMS API Client Package

A comprehensive Python wrapper for the Canvas LMS REST API.
Provides organized modules for different Canvas API endpoints.
"""

from .base import CanvasAPIBase

# Import submodules
from . import assignment
from . import calendar  
from . import course

# Import main API classes and instances
from .assignment import (
    AssignmentExtensionsAPI,
    assignment_extensions,
    AssignmentGroupsAPI,
    assignment_groups,
    AssignmentsAPI,
    assignments,
)
from .calendar import (
    AccountCalendarsAPI,
    account_calendars,
)
from .course import (
    CoursesAPI,
    courses,
)

__version__ = "0.1.0"

__all__ = [
    # Base class
    "CanvasAPIBase",
    
    # Submodules
    "assignment",
    "calendar", 
    "course",
    
    # Assignment APIs
    "AssignmentExtensionsAPI",
    "assignment_extensions",
    "AssignmentGroupsAPI", 
    "assignment_groups",
    "AssignmentsAPI",
    "assignments",
    
    # Calendar APIs
    "AccountCalendarsAPI",
    "account_calendars",
    
    # Course APIs
    "CoursesAPI",
    "courses",
]