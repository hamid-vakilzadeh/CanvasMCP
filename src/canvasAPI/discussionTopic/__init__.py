"""Discussion-related Canvas API modules

Provides APIs for managing discussions and discussion Topic-related operations.
"""

from .discussionTopics import DiscussionTopicsAPI, discussion_topics

__all__ = [
    "DiscussionTopicsAPI",
    "discussion_topics",
]
