from typing import List, Dict, Union, Optional, TypedDict, Literal
from datetime import datetime
from ..base import CanvasAPIBase


class FileAttachment(TypedDict, total=False):
    """File attachment object for discussion topics."""
    
    content_type: str
    url: str
    filename: str
    display_name: str


class DiscussionTopicPermissions(TypedDict, total=False):
    """Permissions object for discussion topics."""
    
    attach: bool


class GroupTopicChild(TypedDict, total=False):
    """Group discussion child object."""
    
    id: int
    group_id: int


class AssignmentData(TypedDict, total=False):
    """Assignment data for discussion topics."""
    
    points_possible: Optional[float]
    due_at: Optional[str]
    unlock_at: Optional[str]
    lock_at: Optional[str]
    assignment_group_id: Optional[int]
    grading_type: Optional[Literal["pass_fail", "percent", "letter_grade", "gpa_scale", "points"]]
    submission_types: Optional[List[str]]
    set_assignment: Optional[bool]


class DiscussionSummary(TypedDict, total=False):
    """Discussion summary object."""
    
    id: int
    userInput: Optional[str]
    text: str
    usage: Dict[str, int]


class DiscussionTopic(TypedDict, total=False):
    """Discussion topic object."""
    
    id: int
    title: str
    message: Optional[str]
    html_url: str
    posted_at: Optional[str]
    last_reply_at: Optional[str]
    require_initial_post: bool
    user_can_see_posts: bool
    discussion_subentry_count: int
    read_state: Literal["read", "unread"]
    unread_count: int
    subscribed: bool
    subscription_hold: Optional[Literal["initial_post_required", "not_in_group_set", "not_in_group", "topic_is_announcement"]]
    assignment_id: Optional[int]
    delayed_post_at: Optional[str]
    published: bool
    lock_at: Optional[str]
    locked: bool
    pinned: bool
    locked_for_user: bool
    lock_info: Optional[Dict]
    lock_explanation: Optional[str]
    user_name: str
    topic_children: Optional[List[int]]  # Deprecated
    group_topic_children: Optional[List[GroupTopicChild]]
    root_topic_id: Optional[int]
    podcast_url: Optional[str]
    discussion_type: Literal["side_comment", "not_threaded", "threaded"]
    group_category_id: Optional[int]
    attachments: Optional[List[FileAttachment]]
    permissions: Optional[DiscussionTopicPermissions]
    allow_rating: bool
    only_graders_can_rate: bool
    sort_by_rating: bool  # Deprecated
    sort_order: Literal["asc", "desc"]
    sort_order_locked: bool
    expand: bool
    expand_locked: bool


class DiscussionEntry(TypedDict, total=False):
    """Discussion entry object."""
    
    id: int
    user_id: int
    editor_id: Optional[int]
    user_name: str
    message: str
    read_state: Literal["read", "unread"]
    forced_read_state: bool
    created_at: str
    updated_at: Optional[str]
    attachment: Optional[FileAttachment]
    attachments: Optional[List[FileAttachment]]
    recent_replies: Optional[List[Dict]]
    has_more_replies: Optional[bool]
    deleted: Optional[bool]
    parent_id: Optional[int]
    replies: Optional[List[Dict]]


class DiscussionTopicsAPI(CanvasAPIBase):
    """Canvas LMS Discussion Topics API client for managing discussion topics and entries."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Discussion Topics API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def list_discussion_topics(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        include: Optional[List[Literal["all_dates", "sections", "sections_user_count", "overrides"]]] = None,
        order_by: Optional[Literal["position", "recent_activity", "title"]] = None,
        scope: Optional[List[Literal["locked", "unlocked", "pinned", "unpinned"]]] = None,
        only_announcements: Optional[bool] = None,
        filter_by: Optional[Literal["all", "unread"]] = None,
        search_term: Optional[str] = None,
        exclude_context_module_locked_topics: Optional[bool] = None,
        all_pages: bool = False,
    ) -> List[DiscussionTopic]:
        """
        List discussion topics for a course or group.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            include: Additional data to include
            order_by: Sort order for topics
            scope: Filter topics by state
            only_announcements: Return announcements instead of discussion topics
            filter_by: Filter by read state
            search_term: Partial title to match
            exclude_context_module_locked_topics: Exclude module-locked topics for students
            all_pages: If True, fetch all pages automatically

        Returns:
            List of DiscussionTopic dictionaries

        Raises:
            ValueError: If neither course_id nor group_id is provided, or if invalid parameters
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        # Validate include values
        if include is not None:
            valid_includes = {"all_dates", "sections", "sections_user_count", "overrides"}
            invalid_includes = [i for i in include if i not in valid_includes]
            if invalid_includes:
                raise ValueError(
                    f"Invalid include values: {', '.join(invalid_includes)}. "
                    f"Allowed values: {', '.join(sorted(valid_includes))}"
                )

        # Validate order_by
        if order_by is not None:
            valid_order_by = {"position", "recent_activity", "title"}
            if order_by not in valid_order_by:
                raise ValueError(
                    f"Invalid order_by value: {order_by}. "
                    f"Allowed values: {', '.join(sorted(valid_order_by))}"
                )

        # Validate scope
        if scope is not None:
            valid_scopes = {"locked", "unlocked", "pinned", "unpinned"}
            invalid_scopes = [s for s in scope if s not in valid_scopes]
            if invalid_scopes:
                raise ValueError(
                    f"Invalid scope values: {', '.join(invalid_scopes)}. "
                    f"Allowed values: {', '.join(sorted(valid_scopes))}"
                )

        # Validate filter_by
        if filter_by is not None:
            valid_filters = {"all", "unread"}
            if filter_by not in valid_filters:
                raise ValueError(
                    f"Invalid filter_by value: {filter_by}. "
                    f"Allowed values: {', '.join(sorted(valid_filters))}"
                )

        params = {}

        if include:
            params["include[]"] = include
        if order_by:
            params["order_by"] = order_by
        if scope:
            params["scope"] = ",".join(scope)
        if only_announcements is not None:
            params["only_announcements"] = only_announcements
        if filter_by:
            params["filter_by"] = filter_by
        if search_term:
            params["search_term"] = search_term
        if exclude_context_module_locked_topics is not None:
            params["exclude_context_module_locked_topics"] = exclude_context_module_locked_topics

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics"

        if all_pages:
            return self._get_all_pages("GET", endpoint, params=params)
        else:
            response = self._make_request("GET", endpoint, params=params)
            return response.json()

    def create_discussion_topic(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        title: str = None,
        message: str = None,
        discussion_type: Optional[Literal["side_comment", "threaded", "not_threaded"]] = None,
        published: Optional[bool] = None,
        delayed_post_at: Optional[datetime] = None,
        allow_rating: Optional[bool] = None,
        lock_at: Optional[datetime] = None,
        podcast_enabled: Optional[bool] = None,
        podcast_has_student_posts: Optional[bool] = None,
        require_initial_post: Optional[bool] = None,
        assignment: Optional[AssignmentData] = None,
        is_announcement: Optional[bool] = None,
        pinned: Optional[bool] = None,
        position_after: Optional[str] = None,
        group_category_id: Optional[int] = None,
        only_graders_can_rate: Optional[bool] = None,
        sort_order: Optional[Literal["asc", "desc"]] = None,
        sort_order_locked: Optional[bool] = None,
        expanded: Optional[bool] = None,
        expanded_locked: Optional[bool] = None,
        sort_by_rating: Optional[bool] = None,
        specific_sections: Optional[str] = None,
        lock_comment: Optional[bool] = None,
    ) -> DiscussionTopic:
        """
        Create a new discussion topic for a course or group.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            title: Discussion topic title
            message: Discussion topic message content
            discussion_type: Type of discussion
            published: Whether topic is published
            delayed_post_at: When to publish the topic
            allow_rating: Whether users can rate entries
            lock_at: When to lock the topic
            podcast_enabled: Whether topic has podcast feed
            podcast_has_student_posts: Whether podcast includes student posts
            require_initial_post: Whether initial post is required before viewing replies
            assignment: Assignment data if this is a graded discussion
            is_announcement: Whether this is an announcement
            pinned: Whether topic is pinned
            position_after: ID of topic to position this after
            group_category_id: Group category for group discussions
            only_graders_can_rate: Whether only graders can rate
            sort_order: Default sort order
            sort_order_locked: Whether users can change sort order
            expanded: Whether threads are expanded by default
            expanded_locked: Whether users can change expansion setting
            sort_by_rating: Whether to sort by rating (deprecated)
            specific_sections: Comma-separated section IDs for announcements
            lock_comment: Whether to disable commenting on announcements

        Returns:
            Created DiscussionTopic dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        # Validate discussion_type
        if discussion_type is not None:
            valid_types = {"side_comment", "threaded", "not_threaded"}
            if discussion_type not in valid_types:
                raise ValueError(
                    f"Invalid discussion_type: {discussion_type}. "
                    f"Allowed values: {', '.join(sorted(valid_types))}"
                )

        # Validate sort_order
        if sort_order is not None:
            valid_sort_orders = {"asc", "desc"}
            if sort_order not in valid_sort_orders:
                raise ValueError(
                    f"Invalid sort_order: {sort_order}. "
                    f"Allowed values: {', '.join(sorted(valid_sort_orders))}"
                )

        data = {}

        if title:
            data["title"] = title
        if message:
            data["message"] = message
        if discussion_type:
            data["discussion_type"] = discussion_type
        if published is not None:
            data["published"] = published
        if delayed_post_at is not None:
            data["delayed_post_at"] = delayed_post_at.isoformat()
        if allow_rating is not None:
            data["allow_rating"] = allow_rating
        if lock_at is not None:
            data["lock_at"] = lock_at.isoformat()
        if podcast_enabled is not None:
            data["podcast_enabled"] = podcast_enabled
        if podcast_has_student_posts is not None:
            data["podcast_has_student_posts"] = podcast_has_student_posts
        if require_initial_post is not None:
            data["require_initial_post"] = require_initial_post
        if assignment is not None:
            for key, value in assignment.items():
                data[f"assignment[{key}]"] = value
        if is_announcement is not None:
            data["is_announcement"] = is_announcement
        if pinned is not None:
            data["pinned"] = pinned
        if position_after:
            data["position_after"] = position_after
        if group_category_id is not None:
            data["group_category_id"] = group_category_id
        if only_graders_can_rate is not None:
            data["only_graders_can_rate"] = only_graders_can_rate
        if sort_order:
            data["sort_order"] = sort_order
        if sort_order_locked is not None:
            data["sort_order_locked"] = sort_order_locked
        if expanded is not None:
            data["expanded"] = expanded
        if expanded_locked is not None:
            data["expanded_locked"] = expanded_locked
        if sort_by_rating is not None:
            data["sort_by_rating"] = sort_by_rating
        if specific_sections:
            data["specific_sections"] = specific_sections
        if lock_comment is not None:
            data["lock_comment"] = lock_comment

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics"

        response = self._make_request("POST", endpoint, data=data)
        return response.json()

    def get_discussion_topic(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        include: Optional[List[Literal["all_dates", "sections", "sections_user_count", "overrides"]]] = None,
    ) -> DiscussionTopic:
        """
        Get a single discussion topic.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            include: Additional data to include

        Returns:
            DiscussionTopic dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Validate include values
        if include is not None:
            valid_includes = {"all_dates", "sections", "sections_user_count", "overrides"}
            invalid_includes = [i for i in include if i not in valid_includes]
            if invalid_includes:
                raise ValueError(
                    f"Invalid include values: {', '.join(invalid_includes)}. "
                    f"Allowed values: {', '.join(sorted(valid_includes))}"
                )

        params = {}
        if include:
            params["include[]"] = include

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}"

        response = self._make_request("GET", endpoint, params=params)
        return response.json()

    def update_discussion_topic(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        title: Optional[str] = None,
        message: Optional[str] = None,
        discussion_type: Optional[Literal["side_comment", "threaded", "not_threaded"]] = None,
        published: Optional[bool] = None,
        delayed_post_at: Optional[datetime] = None,
        lock_at: Optional[datetime] = None,
        podcast_enabled: Optional[bool] = None,
        podcast_has_student_posts: Optional[bool] = None,
        require_initial_post: Optional[bool] = None,
        assignment: Optional[AssignmentData] = None,
        is_announcement: Optional[bool] = None,
        pinned: Optional[bool] = None,
        position_after: Optional[str] = None,
        group_category_id: Optional[int] = None,
        allow_rating: Optional[bool] = None,
        only_graders_can_rate: Optional[bool] = None,
        sort_order: Optional[Literal["asc", "desc"]] = None,
        sort_order_locked: Optional[bool] = None,
        expanded: Optional[bool] = None,
        expanded_locked: Optional[bool] = None,
        sort_by_rating: Optional[bool] = None,
        specific_sections: Optional[str] = None,
        lock_comment: Optional[bool] = None,
    ) -> DiscussionTopic:
        """
        Update an existing discussion topic.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            title: Discussion topic title
            message: Discussion topic message content
            discussion_type: Type of discussion
            published: Whether topic is published
            delayed_post_at: When to publish the topic
            lock_at: When to lock the topic
            podcast_enabled: Whether topic has podcast feed
            podcast_has_student_posts: Whether podcast includes student posts
            require_initial_post: Whether initial post is required before viewing replies
            assignment: Assignment data if this is a graded discussion
            is_announcement: Whether this is an announcement
            pinned: Whether topic is pinned
            position_after: ID of topic to position this after
            group_category_id: Group category for group discussions
            allow_rating: Whether users can rate entries
            only_graders_can_rate: Whether only graders can rate
            sort_order: Default sort order
            sort_order_locked: Whether users can change sort order
            expanded: Whether threads are expanded by default
            expanded_locked: Whether users can change expansion setting
            sort_by_rating: Whether to sort by rating (deprecated)
            specific_sections: Comma-separated section IDs for announcements
            lock_comment: Whether to disable commenting on announcements

        Returns:
            Updated DiscussionTopic dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Validate discussion_type
        if discussion_type is not None:
            valid_types = {"side_comment", "threaded", "not_threaded"}
            if discussion_type not in valid_types:
                raise ValueError(
                    f"Invalid discussion_type: {discussion_type}. "
                    f"Allowed values: {', '.join(sorted(valid_types))}"
                )

        # Validate sort_order
        if sort_order is not None:
            valid_sort_orders = {"asc", "desc"}
            if sort_order not in valid_sort_orders:
                raise ValueError(
                    f"Invalid sort_order: {sort_order}. "
                    f"Allowed values: {', '.join(sorted(valid_sort_orders))}"
                )

        data = {}

        if title is not None:
            data["title"] = title
        if message is not None:
            data["message"] = message
        if discussion_type is not None:
            data["discussion_type"] = discussion_type
        if published is not None:
            data["published"] = published
        if delayed_post_at is not None:
            data["delayed_post_at"] = delayed_post_at.isoformat()
        if lock_at is not None:
            data["lock_at"] = lock_at.isoformat()
        if podcast_enabled is not None:
            data["podcast_enabled"] = podcast_enabled
        if podcast_has_student_posts is not None:
            data["podcast_has_student_posts"] = podcast_has_student_posts
        if require_initial_post is not None:
            data["require_initial_post"] = require_initial_post
        if assignment is not None:
            for key, value in assignment.items():
                data[f"assignment[{key}]"] = value
        if is_announcement is not None:
            data["is_announcement"] = is_announcement
        if pinned is not None:
            data["pinned"] = pinned
        if position_after is not None:
            data["position_after"] = position_after
        if group_category_id is not None:
            data["group_category_id"] = group_category_id
        if allow_rating is not None:
            data["allow_rating"] = allow_rating
        if only_graders_can_rate is not None:
            data["only_graders_can_rate"] = only_graders_can_rate
        if sort_order is not None:
            data["sort_order"] = sort_order
        if sort_order_locked is not None:
            data["sort_order_locked"] = sort_order_locked
        if expanded is not None:
            data["expanded"] = expanded
        if expanded_locked is not None:
            data["expanded_locked"] = expanded_locked
        if sort_by_rating is not None:
            data["sort_by_rating"] = sort_by_rating
        if specific_sections is not None:
            data["specific_sections"] = specific_sections
        if lock_comment is not None:
            data["lock_comment"] = lock_comment

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}"

        response = self._make_request("PUT", endpoint, data=data)
        return response.json()

    def delete_discussion_topic(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
    ) -> Dict:
        """
        Delete a discussion topic.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID

        Returns:
            Response dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}"

        response = self._make_request("DELETE", endpoint)
        return response.json()

    def reorder_pinned_topics(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        order: List[int] = None,
    ) -> Dict:
        """
        Reorder pinned discussion topics.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            order: List of topic IDs in desired order

        Returns:
            Response dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not order:
            raise ValueError("order is required")

        data = {"order[]": order}

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/reorder"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/reorder"

        response = self._make_request("POST", endpoint, data=data)
        return response.json()

    def duplicate_discussion_topic(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
    ) -> DiscussionTopic:
        """
        Duplicate a discussion topic.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID

        Returns:
            Duplicated DiscussionTopic dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/duplicate"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/duplicate"

        response = self._make_request("POST", endpoint)
        return response.json()

    def get_full_topic(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        include_new_entries: Optional[bool] = None,
    ) -> Dict:
        """
        Get the full topic with all entries in a threaded view.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            include_new_entries: Include new entries not yet in cached view

        Returns:
            Full topic view with participants, entries, and metadata

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        params = {}
        if include_new_entries is not None:
            params["include_new_entries"] = 1 if include_new_entries else 0

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/view"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/view"

        response = self._make_request("GET", endpoint, params=params)
        return response.json()

    def list_topic_entries(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        all_pages: bool = False,
    ) -> List[DiscussionEntry]:
        """
        List top-level entries in a discussion topic.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            all_pages: If True, fetch all pages automatically

        Returns:
            List of DiscussionEntry dictionaries

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entries"

        if all_pages:
            return self._get_all_pages("GET", endpoint)
        else:
            response = self._make_request("GET", endpoint)
            return response.json()

    def post_entry(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        message: str = None,
    ) -> DiscussionEntry:
        """
        Post a new entry to a discussion topic.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            message: Entry message content

        Returns:
            Created DiscussionEntry dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not message:
            raise ValueError("message is required")

        data = {"message": message}

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entries"

        response = self._make_request("POST", endpoint, data=data)
        return response.json()

    def list_entry_replies(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        entry_id: Union[int, str] = None,
        all_pages: bool = False,
    ) -> List[DiscussionEntry]:
        """
        List replies to a discussion entry.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            entry_id: Discussion entry ID
            all_pages: If True, fetch all pages automatically

        Returns:
            List of reply dictionaries

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not entry_id:
            raise ValueError("entry_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries/{entry_id}/replies"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entries/{entry_id}/replies"

        if all_pages:
            return self._get_all_pages("GET", endpoint)
        else:
            response = self._make_request("GET", endpoint)
            return response.json()

    def post_reply(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        entry_id: Union[int, str] = None,
        message: str = None,
    ) -> DiscussionEntry:
        """
        Post a reply to a discussion entry.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            entry_id: Discussion entry ID
            message: Reply message content

        Returns:
            Created reply dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not entry_id:
            raise ValueError("entry_id is required")

        if not message:
            raise ValueError("message is required")

        data = {"message": message}

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries/{entry_id}/replies"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entries/{entry_id}/replies"

        response = self._make_request("POST", endpoint, data=data)
        return response.json()

    def list_entries_by_ids(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        ids: List[Union[int, str]] = None,
        all_pages: bool = False,
    ) -> List[DiscussionEntry]:
        """
        List specific discussion entries by their IDs.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            ids: List of entry IDs to retrieve
            all_pages: If True, fetch all pages automatically

        Returns:
            List of DiscussionEntry dictionaries

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not ids:
            raise ValueError("ids list is required")

        params = {"ids[]": ids}

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entry_list"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entry_list"

        if all_pages:
            return self._get_all_pages("GET", endpoint, params=params)
        else:
            response = self._make_request("GET", endpoint, params=params)
            return response.json()

    def update_entry(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        entry_id: Union[int, str] = None,
        message: str = None,
    ) -> DiscussionEntry:
        """
        Update a discussion entry.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            entry_id: Discussion entry ID
            message: Updated message content

        Returns:
            Updated entry dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not entry_id:
            raise ValueError("entry_id is required")

        if not message:
            raise ValueError("message is required")

        data = {"message": message}

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries/{entry_id}"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entries/{entry_id}"

        response = self._make_request("PUT", endpoint, data=data)
        return response.json()

    def delete_entry(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        entry_id: Union[int, str] = None,
    ) -> Dict:
        """
        Delete a discussion entry.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            entry_id: Discussion entry ID

        Returns:
            Response dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not entry_id:
            raise ValueError("entry_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries/{entry_id}"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entries/{entry_id}"

        response = self._make_request("DELETE", endpoint)
        return response.json()

    def mark_topic_read(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
    ) -> None:
        """
        Mark the initial text of a discussion topic as read.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/read"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/read"

        self._make_request("PUT", endpoint)

    def mark_topic_unread(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
    ) -> None:
        """
        Mark the initial text of a discussion topic as unread.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/read"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/read"

        self._make_request("DELETE", endpoint)

    def mark_all_topics_read(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
    ) -> None:
        """
        Mark the initial text of all discussion topics as read in the context.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/read_all"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/read_all"

        self._make_request("PUT", endpoint)

    def mark_all_entries_read(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        forced_read_state: Optional[bool] = None,
    ) -> None:
        """
        Mark a discussion topic and all its entries as read.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            forced_read_state: Set forced_read_state for all entries

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        params = {}
        if forced_read_state is not None:
            params["forced_read_state"] = forced_read_state

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/read_all"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/read_all"

        self._make_request("PUT", endpoint, params=params)

    def mark_all_entries_unread(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        forced_read_state: Optional[bool] = None,
    ) -> None:
        """
        Mark a discussion topic and all its entries as unread.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            forced_read_state: Set forced_read_state for all entries

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        params = {}
        if forced_read_state is not None:
            params["forced_read_state"] = forced_read_state

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/read_all"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/read_all"

        self._make_request("DELETE", endpoint, params=params)

    def mark_entry_read(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        entry_id: Union[int, str] = None,
        forced_read_state: Optional[bool] = None,
    ) -> None:
        """
        Mark a discussion entry as read.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            entry_id: Discussion entry ID
            forced_read_state: Set the entry's forced_read_state

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not entry_id:
            raise ValueError("entry_id is required")

        params = {}
        if forced_read_state is not None:
            params["forced_read_state"] = forced_read_state

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries/{entry_id}/read"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entries/{entry_id}/read"

        self._make_request("PUT", endpoint, params=params)

    def mark_entry_unread(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        entry_id: Union[int, str] = None,
        forced_read_state: Optional[bool] = None,
    ) -> None:
        """
        Mark a discussion entry as unread.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            entry_id: Discussion entry ID
            forced_read_state: Set the entry's forced_read_state

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not entry_id:
            raise ValueError("entry_id is required")

        params = {}
        if forced_read_state is not None:
            params["forced_read_state"] = forced_read_state

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries/{entry_id}/read"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entries/{entry_id}/read"

        self._make_request("DELETE", endpoint, params=params)

    def rate_entry(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        entry_id: Union[int, str] = None,
        rating: int = None,
    ) -> None:
        """
        Rate a discussion entry.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            entry_id: Discussion entry ID
            rating: Rating value (0 or 1)

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not entry_id:
            raise ValueError("entry_id is required")

        if rating is None:
            raise ValueError("rating is required")

        if rating not in [0, 1]:
            raise ValueError("rating must be 0 or 1")

        data = {"rating": rating}

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries/{entry_id}/rating"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/entries/{entry_id}/rating"

        self._make_request("POST", endpoint, data=data)

    def subscribe_to_topic(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
    ) -> None:
        """
        Subscribe to a topic to receive notifications about new entries.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/subscribed"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/subscribed"

        self._make_request("PUT", endpoint)

    def unsubscribe_from_topic(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
    ) -> None:
        """
        Unsubscribe from a topic to stop receiving notifications about new entries.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID

        Returns:
            None (204 No Content response)

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/subscribed"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/subscribed"

        self._make_request("DELETE", endpoint)

    def find_last_summary(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
    ) -> DiscussionSummary:
        """
        Find the last summary for a discussion topic.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID

        Returns:
            DiscussionSummary dictionary with last userInput, text, and usage info

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/summaries"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/summaries"

        response = self._make_request("GET", endpoint)
        return response.json()

    def create_or_find_summary(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        userInput: str = None,
    ) -> DiscussionSummary:
        """
        Generate or find a summary for a discussion topic.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            userInput: Areas or topics for the summary to focus on

        Returns:
            DiscussionSummary dictionary with summary text and usage info

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        data = {}
        if userInput:
            data["userInput"] = userInput

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/summaries"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/summaries"

        response = self._make_request("POST", endpoint, data=data)
        return response.json()

    def disable_summary(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
    ) -> Dict:
        """
        Disable the summary for a discussion topic (deprecated).

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID

        Returns:
            Response dictionary with success status

        Raises:
            ValueError: If validation fails

        Note:
            This method is deprecated and will be removed after VICE-5047 gets merged.
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/summaries/disable"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/summaries/disable"

        response = self._make_request("PUT", endpoint)
        return response.json()

    def submit_summary_feedback(
        self,
        course_id: Union[int, str] = None,
        group_id: Union[int, str] = None,
        topic_id: Union[int, str] = None,
        summary_id: Union[int, str] = None,
        action: Literal["seen", "like", "dislike", "reset_like", "regenerate", "disable_summary"] = None,
    ) -> Dict:
        """
        Submit feedback on a discussion topic summary.

        Args:
            course_id: Course ID (required if group_id not provided)
            group_id: Group ID (required if course_id not provided)
            topic_id: Discussion topic ID
            summary_id: Summary ID
            action: Feedback action to take

        Returns:
            Feedback response dictionary

        Raises:
            ValueError: If validation fails
        """
        if not course_id and not group_id:
            raise ValueError("Either course_id or group_id must be provided")
        
        if course_id and group_id:
            raise ValueError("Cannot specify both course_id and group_id")

        if not topic_id:
            raise ValueError("topic_id is required")

        if not summary_id:
            raise ValueError("summary_id is required")

        if not action:
            raise ValueError("action is required")

        valid_actions = {"seen", "like", "dislike", "reset_like", "regenerate", "disable_summary"}
        if action not in valid_actions:
            raise ValueError(
                f"Invalid action: {action}. "
                f"Allowed values: {', '.join(sorted(valid_actions))}"
            )

        data = {"_action": action}

        # Determine endpoint based on context
        if course_id:
            endpoint = f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/summaries/{summary_id}/feedback"
        else:
            endpoint = f"/api/v1/groups/{group_id}/discussion_topics/{topic_id}/summaries/{summary_id}/feedback"

        response = self._make_request("POST", endpoint, data=data)
        return response.json()


# Lazy-loaded convenience instance
def get_discussion_topics():
    from ..base import access_token, url
    return DiscussionTopicsAPI(access_token, url)

class _LazyDiscussionTopicsAPI:
    def __getattr__(self, name):
        return getattr(get_discussion_topics(), name)

discussion_topics = _LazyDiscussionTopicsAPI()