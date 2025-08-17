"""Discussion topic-related tools for Canvas MCP."""

from typing import Annotated, Literal, Optional
from pydantic import Field
from datetime import datetime

from .base import ToolProvider
from canvasAPI.discussionTopic import discussionTopics
from tools.getToken import get_user_token


class DiscussionTools(ToolProvider):
    """Tools for managing Canvas discussion topics."""

    def _register_tools(self):
        """Register all discussion topic-related tools."""
        tools_to_register = [
            (self.list_discussion_topics, {"discussion"}),
            (self.get_discussion_topic, {"discussion"}),
            (self.create_discussion_topic, {"discussion"}),
            (self.update_discussion_topic, {"discussion"}),
            (self.delete_discussion_topic, {"discussion"}),
            (self.duplicate_discussion_topic, {"discussion"}),
            (self.reorder_pinned_topics, {"discussion"}),
        ]
        
        for tool_func, tags in tools_to_register:
            wrapped_tool = self._wrap_tool_with_analytics(tool_func)
            self.mcp.tool(wrapped_tool, tags=tags)

    async def list_discussion_topics(
        self,
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID to list discussion topics from"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID to list discussion topics from"),
        ] = None,
        include: Annotated[
            list[Literal["all_dates", "sections", "sections_user_count", "overrides"]] | None,
            Field(description="Additional data to include"),
        ] = None,
        order_by: Annotated[
            Literal["position", "recent_activity", "title"] | None,
            Field(description="Sort order for topics"),
        ] = None,
        scope: Annotated[
            list[Literal["locked", "unlocked", "pinned", "unpinned"]] | None,
            Field(description="Filter topics by state"),
        ] = None,
        only_announcements: Annotated[
            bool | None,
            Field(description="Return announcements instead of discussion topics"),
        ] = None,
        filter_by: Annotated[
            Literal["all", "unread"] | None,
            Field(description="Filter by read state"),
        ] = None,
        search_term: Annotated[
            str | None,
            Field(description="Partial title to match and return"),
        ] = None,
        exclude_context_module_locked_topics: Annotated[
            bool | None,
            Field(description="Exclude module-locked topics for students"),
        ] = None,
    ) -> list[dict]:
        """List discussion topics in a course or group."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            include=include,
            order_by=order_by,
            scope=scope,
            only_announcements=only_announcements,
            filter_by=filter_by,
            search_term=search_term,
            exclude_context_module_locked_topics=exclude_context_module_locked_topics,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.list_discussion_topics(**params)

    async def get_discussion_topic(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID to get")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
        include: Annotated[
            list[Literal["all_dates", "sections", "sections_user_count", "overrides"]] | None,
            Field(description="Additional data to include"),
        ] = None,
    ) -> dict:
        """Get a single discussion topic."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            include=include,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.get_discussion_topic(**params)

    async def create_discussion_topic(
        self,
        title: Annotated[str, Field(description="The discussion topic title")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
        message: Annotated[
            str | None,
            Field(description="The discussion topic message content"),
        ] = None,
        discussion_type: Annotated[
            Literal["side_comment", "threaded", "not_threaded"] | None,
            Field(description="The type of discussion"),
        ] = None,
        published: Annotated[
            bool | None,
            Field(description="Whether topic is published"),
        ] = None,
        delayed_post_at: Annotated[
            str | None,
            Field(description="When to publish the topic (ISO format)"),
        ] = None,
        allow_rating: Annotated[
            bool | None,
            Field(description="Whether users can rate entries"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="When to lock the topic (ISO format)"),
        ] = None,
        podcast_enabled: Annotated[
            bool | None,
            Field(description="Whether topic has podcast feed"),
        ] = None,
        podcast_has_student_posts: Annotated[
            bool | None,
            Field(description="Whether podcast includes student posts"),
        ] = None,
        require_initial_post: Annotated[
            bool | None,
            Field(description="Whether initial post is required before viewing replies"),
        ] = None,
        pinned: Annotated[
            bool | None,
            Field(description="Whether topic is pinned"),
        ] = None,
        position_after: Annotated[
            str | None,
            Field(description="ID of topic to position this after"),
        ] = None,
        group_category_id: Annotated[
            int | None,
            Field(description="Group category for group discussions"),
        ] = None,
        only_graders_can_rate: Annotated[
            bool | None,
            Field(description="Whether only graders can rate"),
        ] = None,
        sort_order: Annotated[
            Literal["asc", "desc"] | None,
            Field(description="Default sort order"),
        ] = None,
        sort_order_locked: Annotated[
            bool | None,
            Field(description="Whether users can change sort order"),
        ] = None,
        expanded: Annotated[
            bool | None,
            Field(description="Whether threads are expanded by default"),
        ] = None,
        expanded_locked: Annotated[
            bool | None,
            Field(description="Whether users can change expansion setting"),
        ] = None,
        sort_by_rating: Annotated[
            bool | None,
            Field(description="Whether to sort by rating (deprecated)"),
        ] = None,
    ) -> dict:
        """Create a new discussion topic for a course or group."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            title=title,
            message=message,
            discussion_type=discussion_type,
            published=published,
            delayed_post_at=datetime.fromisoformat(delayed_post_at) if delayed_post_at else None,
            allow_rating=allow_rating,
            lock_at=datetime.fromisoformat(lock_at) if lock_at else None,
            podcast_enabled=podcast_enabled,
            podcast_has_student_posts=podcast_has_student_posts,
            require_initial_post=require_initial_post,
            pinned=pinned,
            position_after=position_after,
            group_category_id=group_category_id,
            only_graders_can_rate=only_graders_can_rate,
            sort_order=sort_order,
            sort_order_locked=sort_order_locked,
            expanded=expanded,
            expanded_locked=expanded_locked,
            sort_by_rating=sort_by_rating,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.create_discussion_topic(**params)

    async def update_discussion_topic(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID to update")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
        title: Annotated[
            str | None,
            Field(description="The discussion topic title"),
        ] = None,
        message: Annotated[
            str | None,
            Field(description="The discussion topic message content"),
        ] = None,
        discussion_type: Annotated[
            Literal["side_comment", "threaded", "not_threaded"] | None,
            Field(description="The type of discussion"),
        ] = None,
        published: Annotated[
            bool | None,
            Field(description="Whether topic is published"),
        ] = None,
        delayed_post_at: Annotated[
            str | None,
            Field(description="When to publish the topic (ISO format)"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="When to lock the topic (ISO format)"),
        ] = None,
        podcast_enabled: Annotated[
            bool | None,
            Field(description="Whether topic has podcast feed"),
        ] = None,
        podcast_has_student_posts: Annotated[
            bool | None,
            Field(description="Whether podcast includes student posts"),
        ] = None,
        require_initial_post: Annotated[
            bool | None,
            Field(description="Whether initial post is required before viewing replies"),
        ] = None,
        pinned: Annotated[
            bool | None,
            Field(description="Whether topic is pinned"),
        ] = None,
        position_after: Annotated[
            str | None,
            Field(description="ID of topic to position this after"),
        ] = None,
        group_category_id: Annotated[
            int | None,
            Field(description="Group category for group discussions"),
        ] = None,
        allow_rating: Annotated[
            bool | None,
            Field(description="Whether users can rate entries"),
        ] = None,
        only_graders_can_rate: Annotated[
            bool | None,
            Field(description="Whether only graders can rate"),
        ] = None,
        sort_order: Annotated[
            Literal["asc", "desc"] | None,
            Field(description="Default sort order"),
        ] = None,
        sort_order_locked: Annotated[
            bool | None,
            Field(description="Whether users can change sort order"),
        ] = None,
        expanded: Annotated[
            bool | None,
            Field(description="Whether threads are expanded by default"),
        ] = None,
        expanded_locked: Annotated[
            bool | None,
            Field(description="Whether users can change expansion setting"),
        ] = None,
        sort_by_rating: Annotated[
            bool | None,
            Field(description="Whether to sort by rating (deprecated)"),
        ] = None,
    ) -> dict:
        """Update an existing discussion topic."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            title=title,
            message=message,
            discussion_type=discussion_type,
            published=published,
            delayed_post_at=datetime.fromisoformat(delayed_post_at) if delayed_post_at else None,
            lock_at=datetime.fromisoformat(lock_at) if lock_at else None,
            podcast_enabled=podcast_enabled,
            podcast_has_student_posts=podcast_has_student_posts,
            require_initial_post=require_initial_post,
            pinned=pinned,
            position_after=position_after,
            group_category_id=group_category_id,
            allow_rating=allow_rating,
            only_graders_can_rate=only_graders_can_rate,
            sort_order=sort_order,
            sort_order_locked=sort_order_locked,
            expanded=expanded,
            expanded_locked=expanded_locked,
            sort_by_rating=sort_by_rating,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.update_discussion_topic(**params)

    async def delete_discussion_topic(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID to delete")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> dict:
        """Delete a discussion topic."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.delete_discussion_topic(**params)

    async def duplicate_discussion_topic(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID to duplicate")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> dict:
        """Duplicate a discussion topic."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.duplicate_discussion_topic(**params)

    async def reorder_pinned_topics(
        self,
        order: Annotated[
            list[int],
            Field(description="List of topic IDs in desired order"),
        ],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> dict:
        """Reorder pinned discussion topics."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            order=order,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.reorder_pinned_topics(**params)


class DiscussionEntryTools(ToolProvider):
    """Tools for managing Canvas discussion entries."""

    def _register_tools(self):
        """Register all discussion entry-related tools."""
        tools_to_register = [
            (self.list_topic_entries, {"discussion", "entry"}),
            (self.post_entry, {"discussion", "entry"}),
            (self.list_entry_replies, {"discussion", "entry"}),
            (self.post_reply, {"discussion", "entry"}),
            (self.update_entry, {"discussion", "entry"}),
            (self.delete_entry, {"discussion", "entry"}),
            (self.mark_entry_read, {"discussion", "entry"}),
            (self.mark_entry_unread, {"discussion", "entry"}),
            (self.rate_entry, {"discussion", "entry"}),
        ]
        
        for tool_func, tags in tools_to_register:
            wrapped_tool = self._wrap_tool_with_analytics(tool_func)
            self.mcp.tool(wrapped_tool, tags=tags)

    async def list_topic_entries(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> list[dict]:
        """List top-level entries in a discussion topic."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.list_topic_entries(**params)

    async def post_entry(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID")],
        message: Annotated[str, Field(description="Entry message content")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> dict:
        """Post a new entry to a discussion topic."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            message=message,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.post_entry(**params)

    async def list_entry_replies(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID")],
        entry_id: Annotated[str | int, Field(description="The discussion entry ID")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> list[dict]:
        """List replies to a discussion entry."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            entry_id=entry_id,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.list_entry_replies(**params)

    async def post_reply(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID")],
        entry_id: Annotated[str | int, Field(description="The discussion entry ID")],
        message: Annotated[str, Field(description="Reply message content")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> dict:
        """Post a reply to a discussion entry."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            entry_id=entry_id,
            message=message,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.post_reply(**params)

    async def update_entry(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID")],
        entry_id: Annotated[str | int, Field(description="The discussion entry ID")],
        message: Annotated[str, Field(description="Updated message content")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> dict:
        """Update a discussion entry."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            entry_id=entry_id,
            message=message,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.update_entry(**params)

    async def delete_entry(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID")],
        entry_id: Annotated[str | int, Field(description="The discussion entry ID")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> dict:
        """Delete a discussion entry."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            entry_id=entry_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.delete_entry(**params)

    async def mark_entry_read(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID")],
        entry_id: Annotated[str | int, Field(description="The discussion entry ID")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
        forced_read_state: Annotated[
            bool | None,
            Field(description="Set the entry's forced_read_state"),
        ] = None,
    ) -> None:
        """Mark a discussion entry as read."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            entry_id=entry_id,
            forced_read_state=forced_read_state,
        )
        params["base_url"], params["access_token"] = get_user_token()

        discussionTopics.mark_entry_read(**params)

    async def mark_entry_unread(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID")],
        entry_id: Annotated[str | int, Field(description="The discussion entry ID")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
        forced_read_state: Annotated[
            bool | None,
            Field(description="Set the entry's forced_read_state"),
        ] = None,
    ) -> None:
        """Mark a discussion entry as unread."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            entry_id=entry_id,
            forced_read_state=forced_read_state,
        )
        params["base_url"], params["access_token"] = get_user_token()

        discussionTopics.mark_entry_unread(**params)

    async def rate_entry(
        self,
        topic_id: Annotated[str | int, Field(description="The discussion topic ID")],
        entry_id: Annotated[str | int, Field(description="The discussion entry ID")],
        rating: Annotated[int, Field(description="Rating value (0 or 1)")],
        course_id: Annotated[
            str | int | None,
            Field(description="The course ID"),
        ] = None,
        group_id: Annotated[
            str | int | None,
            Field(description="The group ID"),
        ] = None,
    ) -> None:
        """Rate a discussion entry."""
        params = self._validate_params(
            course_id=course_id,
            group_id=group_id,
            topic_id=topic_id,
            entry_id=entry_id,
            rating=rating,
        )
        params["base_url"], params["access_token"] = get_user_token()

        discussionTopics.rate_entry(**params)


class AnnouncementTools(ToolProvider):
    """Tools for managing Canvas announcements."""

    def _register_tools(self):
        """Register all announcement-related tools."""
        tools_to_register = [
            (self.create_announcement, {"announcement"}),
            (self.list_announcements, {"announcement"}),
        ]
        
        for tool_func, tags in tools_to_register:
            wrapped_tool = self._wrap_tool_with_analytics(tool_func)
            self.mcp.tool(wrapped_tool, tags=tags)

    async def create_announcement(
        self,
        title: Annotated[str, Field(description="The announcement title")],
        course_id: Annotated[
            str | int,
            Field(description="The course ID"),
        ],
        message: Annotated[
            str | None,
            Field(description="The announcement message content"),
        ] = None,
        published: Annotated[
            bool | None,
            Field(description="Whether announcement is published"),
        ] = True,
        delayed_post_at: Annotated[
            str | None,
            Field(description="When to publish the announcement (ISO format)"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="When to lock the announcement (ISO format)"),
        ] = None,
        pinned: Annotated[
            bool | None,
            Field(description="Whether announcement is pinned"),
        ] = None,
        specific_sections: Annotated[
            str | None,
            Field(description="Comma-separated section IDs for announcements"),
        ] = None,
        lock_comment: Annotated[
            bool | None,
            Field(description="Whether to disable commenting on announcements"),
        ] = None,
    ) -> dict:
        """Create a new announcement for a course."""
        params = self._validate_params(
            course_id=course_id,
            title=title,
            message=message,
            is_announcement=True,
            published=published,
            delayed_post_at=datetime.fromisoformat(delayed_post_at) if delayed_post_at else None,
            lock_at=datetime.fromisoformat(lock_at) if lock_at else None,
            pinned=pinned,
            specific_sections=specific_sections,
            lock_comment=lock_comment,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.create_discussion_topic(**params)

    async def list_announcements(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID to list announcements from"),
        ],
        include: Annotated[
            list[Literal["all_dates", "sections", "sections_user_count", "overrides"]] | None,
            Field(description="Additional data to include"),
        ] = None,
        order_by: Annotated[
            Literal["position", "recent_activity", "title"] | None,
            Field(description="Sort order for announcements"),
        ] = None,
        scope: Annotated[
            list[Literal["locked", "unlocked", "pinned", "unpinned"]] | None,
            Field(description="Filter announcements by state"),
        ] = None,
        filter_by: Annotated[
            Literal["all", "unread"] | None,
            Field(description="Filter by read state"),
        ] = None,
        search_term: Annotated[
            str | None,
            Field(description="Partial title to match and return"),
        ] = None,
    ) -> list[dict]:
        """List announcements in a course."""
        params = self._validate_params(
            course_id=course_id,
            include=include,
            order_by=order_by,
            scope=scope,
            only_announcements=True,
            filter_by=filter_by,
            search_term=search_term,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return discussionTopics.list_discussion_topics(**params)