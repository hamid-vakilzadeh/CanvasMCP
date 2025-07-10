"""Assignment-related Canvas API modules

Provides APIs for managing assignments, assignment groups, and extensions.
"""

from .assignment_extensions import AssignmentExtensionsAPI, assignment_extensions
from .assignment_groups import AssignmentGroupsAPI, assignment_groups
from .assignments import AssignmentsAPI, assignments

__all__ = [
    "AssignmentExtensionsAPI",
    "assignment_extensions", 
    "AssignmentGroupsAPI",
    "assignment_groups",
    "AssignmentsAPI",
    "assignments",
]