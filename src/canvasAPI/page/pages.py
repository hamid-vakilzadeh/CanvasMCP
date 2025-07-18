from typing import List, Dict, Union, Optional, Literal, TypedDict
from datetime import datetime
from ..base import CanvasAPIBase


class BlockEditorAttributes(TypedDict):
    """Block editor attributes for a page."""

    id: int
    version: str
    blocks: str  # JSON string containing block data


class PageUser(TypedDict):
    """A user associated with a page (e.g., last_edited_by)."""

    id: int
    name: str
    full_name: str
    avatar_url: Optional[str]


class PageLockInfo(TypedDict):
    """Information about page locks."""

    asset_string: str
    unlock_at: Optional[str]
    lock_at: Optional[str]
    context_module: Optional[Dict]


class Page(TypedDict):
    """A wiki page object."""

    page_id: int
    url: str
    title: str
    created_at: str
    updated_at: str
    hide_from_students: bool  # Deprecated, always reflects inverse of published
    editing_roles: Optional[str]
    last_edited_by: Optional[PageUser]
    body: Optional[str]  # Present when requesting single page or when included
    published: bool
    publish_at: Optional[str]
    front_page: bool
    locked_for_user: bool
    lock_info: Optional[PageLockInfo]
    lock_explanation: Optional[str]
    editor: Optional[Literal["rce", "block_editor"]]
    block_editor_attributes: Optional[BlockEditorAttributes]


class PageRevision(TypedDict):
    """A page revision object."""

    revision_id: int
    updated_at: str
    latest: bool
    edited_by: Optional[PageUser]
    url: Optional[str]  # Only in show action, not index
    title: Optional[str]  # Only in show action, not index
    body: Optional[str]  # Only in show action, not index


class PagesAPI(CanvasAPIBase):
    """Canvas LMS Pages API client for managing wiki pages."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Pages API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def show_front_page(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
    ) -> Page:
        """
        Retrieve the content of the front page.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID

        Returns:
            Page object
        """
        response = self._make_request(
            "GET", f"/api/v1/{context_type}/{context_id}/front_page"
        )
        return response.json()

    def duplicate_page(
        self,
        course_id: Union[int, str],
        url_or_id: Union[str, int],
    ) -> Page:
        """
        Duplicate a wiki page.

        Args:
            course_id: Course ID
            url_or_id: Page URL or ID

        Returns:
            Duplicated Page object
        """
        response = self._make_request(
            "POST", f"/api/v1/courses/{course_id}/pages/{url_or_id}/duplicate"
        )
        return response.json()

    def update_front_page(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
        title: Optional[str] = None,
        body: Optional[str] = None,
        editing_roles: Optional[str] = None,
        notify_of_update: Optional[bool] = None,
        published: Optional[bool] = None,
    ) -> Page:
        """
        Update the title or contents of the front page.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID
            title: The title for the new page
            body: The content for the new page
            editing_roles: Which user roles are allowed to edit this page (comma-separated)
            notify_of_update: Whether participants should be notified when this page changes
            published: Whether the page is published (true) or draft state (false)

        Returns:
            Updated Page object

        Raises:
            ValueError: If editing_roles contains invalid values
        """
        if editing_roles is not None:
            valid_roles = {"teachers", "students", "members", "public"}
            roles = [role.strip() for role in editing_roles.split(",")]
            invalid_roles = [role for role in roles if role not in valid_roles]
            if invalid_roles:
                raise ValueError(
                    f"Invalid editing roles: {', '.join(invalid_roles)}. "
                    f"Allowed values: {', '.join(sorted(valid_roles))}"
                )

        data = {}

        if title is not None:
            data["wiki_page[title]"] = title
        if body is not None:
            data["wiki_page[body]"] = body
        if editing_roles is not None:
            data["wiki_page[editing_roles]"] = editing_roles
        if notify_of_update is not None:
            data["wiki_page[notify_of_update]"] = notify_of_update
        if published is not None:
            data["wiki_page[published]"] = published

        response = self._make_request(
            "PUT", f"/api/v1/{context_type}/{context_id}/front_page", data=data
        )
        return response.json()

    def list_pages(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
        sort: Optional[Literal["title", "created_at", "updated_at"]] = None,
        order: Optional[Literal["asc", "desc"]] = None,
        search_term: Optional[str] = None,
        published: Optional[bool] = None,
        include: Optional[List[Literal["body"]]] = None,
        all_pages: bool = False,
    ) -> List[Page]:
        """
        List wiki pages associated with a course or group.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID
            sort: Sort results by this field
            order: The sorting order. Defaults to 'asc'
            search_term: The partial title of pages to match and return
            published: If true, include only published pages. If false, exclude published pages
            include: Optional list of resources to include ("body")
            all_pages: If True, fetch all pages automatically. If False, return only first page.

        Returns:
            List of Page objects

        Raises:
            ValueError: If sort, order, or include values are invalid
        """
        # Validate sort
        if sort is not None:
            valid_sorts = {"title", "created_at", "updated_at"}
            if sort not in valid_sorts:
                raise ValueError(
                    f"Invalid sort value: '{sort}'. "
                    f"Allowed values: {', '.join(sorted(valid_sorts))}"
                )

        # Validate order
        if order is not None:
            valid_orders = {"asc", "desc"}
            if order not in valid_orders:
                raise ValueError(
                    f"Invalid order value: '{order}'. "
                    f"Allowed values: {', '.join(sorted(valid_orders))}"
                )

        # Validate include
        if include is not None:
            valid_includes = {"body"}
            invalid_includes = [i for i in include if i not in valid_includes]
            if invalid_includes:
                raise ValueError(
                    f"Invalid include values: {', '.join(invalid_includes)}. "
                    f"Allowed values: {', '.join(sorted(valid_includes))}"
                )

        params = {}

        if sort is not None:
            params["sort"] = sort
        if order is not None:
            params["order"] = order
        if search_term is not None:
            params["search_term"] = search_term
        if published is not None:
            params["published"] = published
        if include:
            params["include[]"] = include

        if all_pages:
            return self._get_all_pages(
                "GET", f"/api/v1/{context_type}/{context_id}/pages", params=params
            )
        else:
            response = self._make_request(
                "GET", f"/api/v1/{context_type}/{context_id}/pages", params=params
            )
            return response.json()

    def create_page(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
        title: str,
        body: Optional[str] = None,
        editing_roles: Optional[str] = None,
        notify_of_update: Optional[bool] = None,
        published: Optional[bool] = None,
        front_page: Optional[bool] = None,
        publish_at: Optional[datetime] = None,
    ) -> Page:
        """
        Create a new wiki page.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID
            title: The title for the new page (required)
            body: The content for the new page
            editing_roles: Which user roles are allowed to edit this page (comma-separated)
            notify_of_update: Whether participants should be notified when this page changes
            published: Whether the page is published (true) or draft state (false)
            front_page: Set an unhidden page as the front page (if true)
            publish_at: Schedule a future date/time to publish the page

        Returns:
            Created Page object

        Raises:
            ValueError: If title is empty or editing_roles contains invalid values
        """
        if not title or not title.strip():
            raise ValueError("Page title cannot be empty")

        if editing_roles is not None:
            valid_roles = {"teachers", "students", "members", "public"}
            roles = [role.strip() for role in editing_roles.split(",")]
            invalid_roles = [role for role in roles if role not in valid_roles]
            if invalid_roles:
                raise ValueError(
                    f"Invalid editing roles: {', '.join(invalid_roles)}. "
                    f"Allowed values: {', '.join(sorted(valid_roles))}"
                )

        data = {"wiki_page[title]": title.strip()}

        if body is not None:
            data["wiki_page[body]"] = body
        if editing_roles is not None:
            data["wiki_page[editing_roles]"] = editing_roles
        if notify_of_update is not None:
            data["wiki_page[notify_of_update]"] = notify_of_update
        if published is not None:
            data["wiki_page[published]"] = published
        if front_page is not None:
            data["wiki_page[front_page]"] = front_page
        if publish_at is not None:
            data["wiki_page[publish_at]"] = publish_at.isoformat()

        response = self._make_request(
            "POST", f"/api/v1/{context_type}/{context_id}/pages", data=data
        )
        return response.json()

    def show_page(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
        url_or_id: Union[str, int],
    ) -> Page:
        """
        Retrieve the content of a wiki page.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID
            url_or_id: Page URL or ID

        Returns:
            Page object
        """
        response = self._make_request(
            "GET", f"/api/v1/{context_type}/{context_id}/pages/{url_or_id}"
        )
        return response.json()

    def update_page(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
        url_or_id: Union[str, int],
        title: Optional[str] = None,
        body: Optional[str] = None,
        editing_roles: Optional[str] = None,
        notify_of_update: Optional[bool] = None,
        published: Optional[bool] = None,
        publish_at: Optional[datetime] = None,
        front_page: Optional[bool] = None,
    ) -> Page:
        """
        Update the title or contents of a wiki page.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID
            url_or_id: Page URL or ID
            title: The title for the new page
            body: The content for the new page
            editing_roles: Which user roles are allowed to edit this page (comma-separated)
            notify_of_update: Whether participants should be notified when this page changes
            published: Whether the page is published (true) or draft state (false)
            publish_at: Schedule a future date/time to publish the page
            front_page: Set an unhidden page as the front page (if true)

        Returns:
            Updated Page object

        Raises:
            ValueError: If title is empty or editing_roles contains invalid values
        """
        if title is not None and (not title or not title.strip()):
            raise ValueError("Page title cannot be empty")

        if editing_roles is not None:
            valid_roles = {"teachers", "students", "members", "public"}
            roles = [role.strip() for role in editing_roles.split(",")]
            invalid_roles = [role for role in roles if role not in valid_roles]
            if invalid_roles:
                raise ValueError(
                    f"Invalid editing roles: {', '.join(invalid_roles)}. "
                    f"Allowed values: {', '.join(sorted(valid_roles))}"
                )

        data = {}

        if title is not None:
            data["wiki_page[title]"] = title.strip()
        if body is not None:
            data["wiki_page[body]"] = body
        if editing_roles is not None:
            data["wiki_page[editing_roles]"] = editing_roles
        if notify_of_update is not None:
            data["wiki_page[notify_of_update]"] = notify_of_update
        if published is not None:
            data["wiki_page[published]"] = published
        if publish_at is not None:
            data["wiki_page[publish_at]"] = publish_at.isoformat()
        if front_page is not None:
            data["wiki_page[front_page]"] = front_page

        response = self._make_request(
            "PUT", f"/api/v1/{context_type}/{context_id}/pages/{url_or_id}", data=data
        )
        return response.json()

    def delete_page(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
        url_or_id: Union[str, int],
    ) -> Page:
        """
        Delete a wiki page.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID
            url_or_id: Page URL or ID

        Returns:
            Deleted Page object
        """
        response = self._make_request(
            "DELETE", f"/api/v1/{context_type}/{context_id}/pages/{url_or_id}"
        )
        return response.json()

    def list_revisions(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
        url_or_id: Union[str, int],
        all_pages: bool = False,
    ) -> List[PageRevision]:
        """
        List revisions of a page. Requires update rights on the page.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID
            url_or_id: Page URL or ID
            all_pages: If True, fetch all pages automatically. If False, return only first page.

        Returns:
            List of PageRevision objects
        """
        if all_pages:
            return self._get_all_pages(
                "GET",
                f"/api/v1/{context_type}/{context_id}/pages/{url_or_id}/revisions",
            )
        else:
            response = self._make_request(
                "GET",
                f"/api/v1/{context_type}/{context_id}/pages/{url_or_id}/revisions",
            )
            return response.json()

    def show_revision(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
        url_or_id: Union[str, int],
        revision_id: Union[str, int] = "latest",
        summary: Optional[bool] = None,
    ) -> PageRevision:
        """
        Retrieve the metadata and optionally content of a revision of the page.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID
            url_or_id: Page URL or ID
            revision_id: Revision ID or "latest"
            summary: If set, exclude page content from results

        Returns:
            PageRevision object
        """
        params = {}

        if summary is not None:
            params["summary"] = summary

        response = self._make_request(
            "GET",
            f"/api/v1/{context_type}/{context_id}/pages/{url_or_id}/revisions/{revision_id}",
            params=params,
        )
        return response.json()

    def revert_to_revision(
        self,
        context_type: Literal["courses", "groups"],
        context_id: Union[int, str],
        url_or_id: Union[str, int],
        revision_id: Union[int, str],
    ) -> PageRevision:
        """
        Revert a page to a prior revision.

        Args:
            context_type: Either "courses" or "groups"
            context_id: Course or group ID
            url_or_id: Page URL or ID
            revision_id: The revision to revert to

        Returns:
            PageRevision object
        """
        response = self._make_request(
            "POST",
            f"/api/v1/{context_type}/{context_id}/pages/{url_or_id}/revisions/{revision_id}",
        )
        return response.json()


# Lazy-loaded convenience instance
def get_pages():
    from ..base import access_token, url
    return PagesAPI(access_token, url)

class _LazyPagesAPI:
    def __getattr__(self, name):
        return getattr(get_pages(), name)

pages = _LazyPagesAPI()
