from typing import List, Dict, Union, Literal, Optional
from ..base import CanvasAPIBase


class ConversationsAPI(CanvasAPIBase):
    """Canvas LMS Conversations API client for managing conversations and messages."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Conversations API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def list_conversations(
        self,
        scope: Optional[Literal["unread", "starred", "archived", "sent"]] = None,
        filter: Optional[List[str]] = None,
        filter_mode: Literal["and", "or"] = "or",
        interleave_submissions: Optional[bool] = None,
        include_all_conversation_ids: bool = False,
        include: Optional[List[Literal["participant_avatars"]]] = None,
        all_pages: bool = False,
    ) -> Union[List[Dict], Dict]:
        """
        List conversations for the current user.

        Args:
            scope: Filter by conversation type
            filter: Filter by courses, groups, or users (e.g., ["user_123", "course_456"])
            filter_mode: How to combine multiple filters
            interleave_submissions: (Obsolete) Ignored parameter
            include_all_conversation_ids: Return object with conversation_ids array
            include: Additional data to include
            all_pages: If True, fetch all pages automatically. If False, return only first page.

        Returns:
            List of Conversation dictionaries or object with conversations and conversation_ids

        Raises:
            ValueError: If invalid scope, filter_mode, or include values are provided
        """
        # Validate scope
        if scope is not None:
            valid_scopes = {"unread", "starred", "archived", "sent"}
            if scope not in valid_scopes:
                raise ValueError(
                    f"Invalid scope '{scope}'. "
                    f"Allowed values: {', '.join(sorted(valid_scopes))}"
                )

        # Validate filter_mode
        valid_filter_modes = {"and", "or"}
        if filter_mode not in valid_filter_modes:
            raise ValueError(
                f"Invalid filter_mode '{filter_mode}'. "
                f"Allowed values: {', '.join(sorted(valid_filter_modes))}"
            )

        # Validate include
        if include is not None:
            valid_includes = {"participant_avatars"}
            invalid_includes = [i for i in include if i not in valid_includes]
            if invalid_includes:
                raise ValueError(
                    f"Invalid include values: {', '.join(invalid_includes)}. "
                    f"Allowed values: {', '.join(sorted(valid_includes))}"
                )

        params = {}

        if scope:
            params["scope"] = scope
        if filter:
            params["filter[]"] = filter
        if filter_mode != "or":  # Default is "or"
            params["filter_mode"] = filter_mode
        if interleave_submissions is not None:
            params["interleave_submissions"] = interleave_submissions
        if include_all_conversation_ids:
            params["include_all_conversation_ids"] = include_all_conversation_ids
        if include:
            params["include[]"] = include

        if all_pages:
            return self._get_all_pages("GET", "/api/v1/conversations", params=params)
        else:
            response = self._make_request("GET", "/api/v1/conversations", params=params)
            return response.json()

    def create_conversation(
        self,
        recipients: List[str],
        body: str,
        subject: Optional[str] = None,
        force_new: bool = False,
        group_conversation: bool = False,
        attachment_ids: Optional[List[str]] = None,
        media_comment_id: Optional[str] = None,
        media_comment_type: Optional[Literal["audio", "video"]] = None,
        mode: Literal["sync", "async"] = "sync",
        scope: Optional[Literal["unread", "starred", "archived"]] = None,
        filter: Optional[List[str]] = None,
        filter_mode: Literal["and", "or"] = "or",
        context_code: Optional[str] = None,
    ) -> Union[List[Dict], Dict]:
        """
        Create a new conversation with one or more recipients.

        Args:
            recipients: Array of recipient IDs (user_123, course_456, group_789)
            body: Message content
            subject: Conversation subject (max 255 characters, ignored when reusing)
            force_new: Force new conversation even if private one exists
            group_conversation: Create group conversation (required for >100 recipients)
            attachment_ids: Array of attachment IDs from conversation attachments folder
            media_comment_id: Media comment ID for audio/video
            media_comment_type: Type of media comment
            mode: Synchronous or asynchronous creation
            scope: Used for generating "visible" in response
            filter: Used for generating "visible" in response
            filter_mode: How to combine filters for "visible" calculation
            context_code: Course or group context for conversation

        Returns:
            Created conversation(s) or empty array for async mode

        Raises:
            ValueError: If validation fails for parameters

        Note:
            If course/group has >100 enrollments, bulk_message and group_conversation must be true.
        """
        if not recipients:
            raise ValueError("Recipients cannot be empty")

        if not body or not body.strip():
            raise ValueError("Body cannot be empty")

        if subject and len(subject) > 255:
            raise ValueError("Subject cannot exceed 255 characters")

        # Validate media_comment_type
        if media_comment_type is not None:
            valid_media_types = {"audio", "video"}
            if media_comment_type not in valid_media_types:
                raise ValueError(
                    f"Invalid media_comment_type '{media_comment_type}'. "
                    f"Allowed values: {', '.join(sorted(valid_media_types))}"
                )

        # Validate mode
        valid_modes = {"sync", "async"}
        if mode not in valid_modes:
            raise ValueError(
                f"Invalid mode '{mode}'. "
                f"Allowed values: {', '.join(sorted(valid_modes))}"
            )

        # Validate scope
        if scope is not None:
            valid_scopes = {"unread", "starred", "archived"}
            if scope not in valid_scopes:
                raise ValueError(
                    f"Invalid scope '{scope}'. "
                    f"Allowed values: {', '.join(sorted(valid_scopes))}"
                )

        # Validate filter_mode
        valid_filter_modes = {"and", "or"}
        if filter_mode not in valid_filter_modes:
            raise ValueError(
                f"Invalid filter_mode '{filter_mode}'. "
                f"Allowed values: {', '.join(sorted(valid_filter_modes))}"
            )

        data = {
            "recipients[]": recipients,
            "body": body.strip(),
        }

        if subject:
            data["subject"] = subject.strip()
        if force_new:
            data["force_new"] = force_new
        if group_conversation:
            data["group_conversation"] = group_conversation
        if attachment_ids:
            data["attachment_ids[]"] = attachment_ids
        if media_comment_id:
            data["media_comment_id"] = media_comment_id
        if media_comment_type:
            data["media_comment_type"] = media_comment_type
        if mode != "sync":
            data["mode"] = mode
        if scope:
            data["scope"] = scope
        if filter:
            data["filter[]"] = filter
        if filter_mode != "or":
            data["filter_mode"] = filter_mode
        if context_code:
            data["context_code"] = context_code

        response = self._make_request("POST", "/api/v1/conversations", data=data)
        return response.json()

    def get_running_batches(self) -> List[Dict]:
        """
        Get any currently running conversation batches for the current user.

        Returns:
            List of batch dictionaries with id, subject, workflow_state, completion, etc.

        Note:
            Conversation batches are created when bulk private messages are sent asynchronously.
        """
        response = self._make_request("GET", "/api/v1/conversations/batches")
        return response.json()

    def get_conversation(
        self,
        conversation_id: Union[int, str],
        interleave_submissions: Optional[bool] = None,
        scope: Optional[Literal["unread", "starred", "archived"]] = None,
        filter: Optional[List[str]] = None,
        filter_mode: Literal["and", "or"] = "or",
        auto_mark_as_read: bool = True,
    ) -> Dict:
        """
        Get information for a single conversation.

        Args:
            conversation_id: Conversation ID
            interleave_submissions: (Obsolete) Ignored parameter
            scope: Used for generating "visible" in response
            filter: Used for generating "visible" in response
            filter_mode: How to combine filters
            auto_mark_as_read: Automatically mark unread conversations as read

        Returns:
            Conversation dictionary with messages and extended participant info

        Raises:
            ValueError: If invalid scope or filter_mode values are provided
        """
        # Validate scope
        if scope is not None:
            valid_scopes = {"unread", "starred", "archived"}
            if scope not in valid_scopes:
                raise ValueError(
                    f"Invalid scope '{scope}'. "
                    f"Allowed values: {', '.join(sorted(valid_scopes))}"
                )

        # Validate filter_mode
        valid_filter_modes = {"and", "or"}
        if filter_mode not in valid_filter_modes:
            raise ValueError(
                f"Invalid filter_mode '{filter_mode}'. "
                f"Allowed values: {', '.join(sorted(valid_filter_modes))}"
            )

        params = {}

        if interleave_submissions is not None:
            params["interleave_submissions"] = interleave_submissions
        if scope:
            params["scope"] = scope
        if filter:
            params["filter[]"] = filter
        if filter_mode != "or":
            params["filter_mode"] = filter_mode
        if auto_mark_as_read is not True:
            params["auto_mark_as_read"] = auto_mark_as_read

        response = self._make_request(
            "GET", f"/api/v1/conversations/{conversation_id}", params=params
        )
        return response.json()

    def update_conversation(
        self,
        conversation_id: Union[int, str],
        workflow_state: Optional[Literal["read", "unread", "archived"]] = None,
        subscribed: Optional[bool] = None,
        starred: Optional[bool] = None,
        scope: Optional[Literal["unread", "starred", "archived"]] = None,
        filter: Optional[List[str]] = None,
        filter_mode: Literal["and", "or"] = "or",
    ) -> Dict:
        """
        Update attributes for a single conversation.

        Args:
            conversation_id: Conversation ID
            workflow_state: Change conversation state
            subscribed: Toggle subscription (only valid for group conversations)
            starred: Toggle starred state
            scope: Used for generating "visible" in response
            filter: Used for generating "visible" in response
            filter_mode: How to combine filters

        Returns:
            Updated Conversation dictionary

        Raises:
            ValueError: If invalid workflow_state, scope, or filter_mode values are provided
        """
        # Validate workflow_state
        if workflow_state is not None:
            valid_states = {"read", "unread", "archived"}
            if workflow_state not in valid_states:
                raise ValueError(
                    f"Invalid workflow_state '{workflow_state}'. "
                    f"Allowed values: {', '.join(sorted(valid_states))}"
                )

        # Validate scope
        if scope is not None:
            valid_scopes = {"unread", "starred", "archived"}
            if scope not in valid_scopes:
                raise ValueError(
                    f"Invalid scope '{scope}'. "
                    f"Allowed values: {', '.join(sorted(valid_scopes))}"
                )

        # Validate filter_mode
        valid_filter_modes = {"and", "or"}
        if filter_mode not in valid_filter_modes:
            raise ValueError(
                f"Invalid filter_mode '{filter_mode}'. "
                f"Allowed values: {', '.join(sorted(valid_filter_modes))}"
            )

        data = {}

        if workflow_state is not None:
            data["conversation[workflow_state]"] = workflow_state
        if subscribed is not None:
            data["conversation[subscribed]"] = subscribed
        if starred is not None:
            data["conversation[starred]"] = starred
        if scope:
            data["scope"] = scope
        if filter:
            data["filter[]"] = filter
        if filter_mode != "or":
            data["filter_mode"] = filter_mode

        response = self._make_request(
            "PUT", f"/api/v1/conversations/{conversation_id}", data=data
        )
        return response.json()

    def mark_all_as_read(self) -> Dict:
        """
        Mark all conversations as read.

        Returns:
            Response dictionary
        """
        response = self._make_request("POST", "/api/v1/conversations/mark_all_as_read")
        return response.json()

    def delete_conversation(self, conversation_id: Union[int, str]) -> Dict:
        """
        Delete a conversation and its messages.

        Args:
            conversation_id: Conversation ID

        Returns:
            Deleted conversation dictionary

        Note:
            This only deletes the current user's view of the conversation.
        """
        response = self._make_request(
            "DELETE", f"/api/v1/conversations/{conversation_id}"
        )
        return response.json()

    def add_recipients(
        self,
        conversation_id: Union[int, str],
        recipients: List[str],
    ) -> Dict:
        """
        Add recipients to an existing group conversation.

        Args:
            conversation_id: Conversation ID
            recipients: Array of recipient IDs (user_123, course_456, group_789)

        Returns:
            Updated conversation dictionary with latest message

        Raises:
            ValueError: If recipients is empty
        """
        if not recipients:
            raise ValueError("Recipients cannot be empty")

        data = {"recipients[]": recipients}

        response = self._make_request(
            "POST", f"/api/v1/conversations/{conversation_id}/add_recipients", data=data
        )
        return response.json()

    def add_message(
        self,
        conversation_id: Union[int, str],
        body: str,
        attachment_ids: Optional[List[str]] = None,
        media_comment_id: Optional[str] = None,
        media_comment_type: Optional[Literal["audio", "video"]] = None,
        recipients: Optional[List[str]] = None,
        included_messages: Optional[List[str]] = None,
    ) -> Dict:
        """
        Add a message to an existing conversation.

        Args:
            conversation_id: Conversation ID
            body: Message content
            attachment_ids: Array of attachment IDs from conversation attachments folder
            media_comment_id: Media comment ID for audio/video
            media_comment_type: Type of media comment
            recipients: User IDs to send to (defaults to all conversation recipients)
            included_messages: Message IDs from this conversation to forward

        Returns:
            Updated conversation dictionary with latest message

        Raises:
            ValueError: If body is empty or media_comment_type is invalid

        Note:
            To send to no other recipients, recipients array should contain only logged-in user ID.
        """
        if not body or not body.strip():
            raise ValueError("Body cannot be empty")

        # Validate media_comment_type
        if media_comment_type is not None:
            valid_media_types = {"audio", "video"}
            if media_comment_type not in valid_media_types:
                raise ValueError(
                    f"Invalid media_comment_type '{media_comment_type}'. "
                    f"Allowed values: {', '.join(sorted(valid_media_types))}"
                )

        data = {"body": body.strip()}

        if attachment_ids:
            data["attachment_ids[]"] = attachment_ids
        if media_comment_id:
            data["media_comment_id"] = media_comment_id
        if media_comment_type:
            data["media_comment_type"] = media_comment_type
        if recipients:
            data["recipients[]"] = recipients
        if included_messages:
            data["included_messages[]"] = included_messages

        response = self._make_request(
            "POST", f"/api/v1/conversations/{conversation_id}/add_message", data=data
        )
        return response.json()

    def remove_messages(
        self,
        conversation_id: Union[int, str],
        remove: List[str],
    ) -> Dict:
        """
        Delete messages from a conversation.

        Args:
            conversation_id: Conversation ID
            remove: Array of message IDs to delete

        Returns:
            Updated conversation dictionary

        Raises:
            ValueError: If remove list is empty

        Note:
            This only affects the current user's view of the conversation.
            If all messages are deleted, the conversation will be deleted too.
        """
        if not remove:
            raise ValueError("Remove list cannot be empty")

        data = {"remove[]": remove}

        response = self._make_request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/remove_messages",
            data=data,
        )
        return response.json()

    def batch_update_conversations(
        self,
        conversation_ids: List[Union[int, str]],
        event: Literal[
            "mark_as_read", "mark_as_unread", "star", "unstar", "archive", "destroy"
        ],
    ) -> Dict:
        """
        Perform a change on a set of conversations.

        Args:
            conversation_ids: List of conversation IDs (max 500)
            event: Action to take on each conversation

        Returns:
            Progress object for tracking the operation

        Raises:
            ValueError: If conversation_ids is empty, too large, or event is invalid

        Note:
            Operates asynchronously; use Progress API to check status.
        """
        if not conversation_ids:
            raise ValueError("Conversation IDs cannot be empty")

        if len(conversation_ids) > 500:
            raise ValueError("Cannot update more than 500 conversations at once")

        # Validate event
        valid_events = {
            "mark_as_read",
            "mark_as_unread",
            "star",
            "unstar",
            "archive",
            "destroy",
        }
        if event not in valid_events:
            raise ValueError(
                f"Invalid event '{event}'. "
                f"Allowed values: {', '.join(sorted(valid_events))}"
            )

        data = {
            "conversation_ids[]": conversation_ids,
            "event": event,
        }

        response = self._make_request("PUT", "/api/v1/conversations", data=data)
        return response.json()

    def find_recipients(self, **kwargs) -> Dict:
        """
        Find recipients (DEPRECATED).

        Args:
            **kwargs: Search parameters

        Returns:
            Search results

        Note:
            This endpoint is deprecated. Use the Find recipients endpoint in the Search API instead.
        """
        response = self._make_request(
            "GET", "/api/v1/conversations/find_recipients", params=kwargs
        )
        return response.json()

    def unread_count(self) -> Dict:
        """
        Get the number of unread conversations for the current user.

        Returns:
            Dictionary with unread_count key
        """
        response = self._make_request("GET", "/api/v1/conversations/unread_count")
        return response.json()


# Convenience instance using environment variables
conversations = ConversationsAPI()
