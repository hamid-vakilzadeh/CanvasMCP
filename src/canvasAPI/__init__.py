"""Canvas LMS API Client Package

A comprehensive Python wrapper for the Canvas LMS REST API.
Provides organized modules for different Canvas API endpoints.
"""

# Import submodules
from . import assignment
from . import calendar
from . import conversation
from . import course
from . import module
from . import quiz

# Import main API classes and instances
from .assignment import (
    assignment_extensions,
    assignment_groups,
    assignments,
)
from .calendar import (
    account_calendars,
)
from .conversation import (
    conversations,
)
from .course import (
    courses,
)
from .module import (
    modules,
)
from .quiz import (
    course_quiz_extensions,
)

__version__ = "0.1.0"

__all__ = [
    # Submodules
    "assignment",
    "calendar",
    "conversation",
    "course",
    "module",
    "quiz",
    # Assignment APIs
    "assignment_extensions",
    "assignment_groups",
    "assignments",
    # Calendar APIs
    "account_calendars",
    # Conversation APIs
    "conversations",
    # Course APIs
    "courses",
    # Module APIs
    "modules",
    # Quiz APIs
    "course_quiz_extensions",
]
