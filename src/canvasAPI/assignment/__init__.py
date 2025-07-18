"""Assignment-related Canvas API modules

Provides APIs for managing assignments, assignment groups, and extensions.
"""

from . import assignment_extensions
from . import assignment_groups
from . import assignments

__all__ = [
    "assignment_extensions",
    "assignment_groups",
    "assignments",
]
