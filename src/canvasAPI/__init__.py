"""Canvas LMS API Client Package

A comprehensive Python wrapper for the Canvas LMS REST API.
Provides organized modules for different Canvas API endpoints.
"""

from .base import CanvasAPIBase

# Import submodules
from . import assignment
from . import calendar  
from . import conversation
from . import course
from . import module
from . import quiz

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
from .conversation import (
    ConversationsAPI,
    conversations,
)
from .course import (
    CoursesAPI,
    courses,
)
from .module import (
    ModulesAPI,
    modules,
)
from .quiz import (
    CourseQuizExtensionsAPI,
    course_quiz_extensions,
)

__version__ = "0.1.0"

__all__ = [
    # Base class
    "CanvasAPIBase",
    
    # Submodules
    "assignment",
    "calendar", 
    "conversation",
    "course",
    "module",
    "quiz",
    
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
    
    # Conversation APIs
    "ConversationsAPI",
    "conversations",
    
    # Course APIs
    "CoursesAPI",
    "courses",
    
    # Module APIs
    "ModulesAPI",
    "modules",
    
    # Quiz APIs
    "CourseQuizExtensionsAPI",
    "course_quiz_extensions",
]