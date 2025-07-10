"""Course-related Canvas API modules

Provides APIs for managing courses and course-related operations.
"""

from .courses import CoursesAPI, courses

__all__ = [
    "CoursesAPI",
    "courses",
]