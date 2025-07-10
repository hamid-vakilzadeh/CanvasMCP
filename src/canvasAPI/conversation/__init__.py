"""Conversation-related Canvas API modules

Provides APIs for managing conversations and messages.
"""

from .conversations import ConversationsAPI, conversations

__all__ = [
    "ConversationsAPI",
    "conversations",
]