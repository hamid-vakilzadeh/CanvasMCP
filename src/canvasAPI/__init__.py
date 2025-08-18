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
from . import discussionTopic

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

from .discussionTopic import (
    discussionTopics,
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
    "assignment_extensions",
    "assignment_groups",
    "assignments",
    "account_calendars",
    "conversations",
    "courses",
    "modules",
    "course_quiz_extensions",
    "discussionTopic",
    "discussionTopics",
]
