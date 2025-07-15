"""Page-related tools for Canvas MCP."""

from typing import Annotated, Literal
from datetime import datetime
from pydantic import Field

from .base import ToolProvider
from canvasAPI.page import pages


class PageTools(ToolProvider):
    """Tools for managing Canvas wiki pages."""
    
    def _register_tools(self):
        """Register all page-related tools."""
        self.mcp.tool(self.show_front_page, tags={"page"})
        self.mcp.tool(self.duplicate_page, tags={"page"})
        self.mcp.tool(self.update_front_page, tags={"page"})
        self.mcp.tool(self.list_pages, tags={"page"})
        self.mcp.tool(self.create_page, tags={"page"})
        self.mcp.tool(self.show_page, tags={"page"})
        self.mcp.tool(self.update_page, tags={"page"})
        self.mcp.tool(self.delete_page, tags={"page"})
        self.mcp.tool(self.list_revisions, tags={"page", "revision"})
        self.mcp.tool(self.show_revision, tags={"page", "revision"})
        self.mcp.tool(self.revert_to_revision, tags={"page", "revision"})
    
    async def show_front_page(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ]
    ) -> dict:
        """Retrieve the content of the front page."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id
        )
        return pages.show_front_page(**params)
    
    async def duplicate_page(
        self,
        course_id: Annotated[
            str | int,
            Field(description="Course ID")
        ],
        url_or_id: Annotated[
            str | int,
            Field(description="Page URL or ID")
        ]
    ) -> dict:
        """Duplicate a wiki page."""
        params = self._validate_params(
            course_id=course_id,
            url_or_id=url_or_id
        )
        return pages.duplicate_page(**params)
    
    async def update_front_page(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ],
        title: Annotated[
            str | None,
            Field(description="The title for the page")
        ] = None,
        body: Annotated[
            str | None,
            Field(description="The content for the page")
        ] = None,
        editing_roles: Annotated[
            str | None,
            Field(description="Which user roles are allowed to edit this page (comma-separated): teachers, students, members, public")
        ] = None,
        notify_of_update: Annotated[
            bool | str | None,
            Field(description="Whether participants should be notified when this page changes")
        ] = None,
        published: Annotated[
            bool | str | None,
            Field(description="Whether the page is published (true) or draft state (false)")
        ] = None
    ) -> dict:
        """Update the title or contents of the front page."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            title=title,
            body=body,
            editing_roles=editing_roles,
            notify_of_update=notify_of_update,
            published=published
        )
        return pages.update_front_page(**params)
    
    async def list_pages(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ],
        sort: Annotated[
            Literal["title", "created_at", "updated_at"] | None,
            Field(description="Sort results by this field")
        ] = None,
        order: Annotated[
            Literal["asc", "desc"] | None,
            Field(description="The sorting order. Defaults to 'asc'")
        ] = None,
        search_term: Annotated[
            str | None,
            Field(description="The partial title of pages to match and return")
        ] = None,
        published: Annotated[
            bool | str | None,
            Field(description="If true, include only published pages. If false, exclude published pages")
        ] = None,
        include: Annotated[
            list[Literal["body"]] | str | None,
            Field(description="Optional list of resources to include: 'body'")
        ] = None,
        all_pages: Annotated[
            bool | str | None,
            Field(description="If True, fetch all pages automatically. If False, return only first page")
        ] = False
    ) -> list[dict]:
        """List wiki pages associated with a course or group."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            sort=sort,
            order=order,
            search_term=search_term,
            published=published,
            include=include,
            all_pages=all_pages
        )
        return pages.list_pages(**params)
    
    async def create_page(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ],
        title: Annotated[
            str,
            Field(description="The title for the new page (required)")
        ],
        body: Annotated[
            str | None,
            Field(description="The content for the new page")
        ] = None,
        editing_roles: Annotated[
            str | None,
            Field(description="Which user roles are allowed to edit this page (comma-separated): teachers, students, members, public")
        ] = None,
        notify_of_update: Annotated[
            bool | str | None,
            Field(description="Whether participants should be notified when this page changes")
        ] = None,
        published: Annotated[
            bool | str | None,
            Field(description="Whether the page is published (true) or draft state (false)")
        ] = None,
        front_page: Annotated[
            bool | str | None,
            Field(description="Set an unhidden page as the front page (if true)")
        ] = None,
        publish_at: Annotated[
            datetime | None,
            Field(description="Schedule a future date/time to publish the page")
        ] = None
    ) -> dict:
        """Create a new wiki page."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            title=title,
            body=body,
            editing_roles=editing_roles,
            notify_of_update=notify_of_update,
            published=published,
            front_page=front_page,
            publish_at=publish_at
        )
        return pages.create_page(**params)
    
    async def show_page(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ],
        url_or_id: Annotated[
            str | int,
            Field(description="Page URL or ID")
        ]
    ) -> dict:
        """Retrieve the content of a wiki page."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            url_or_id=url_or_id
        )
        return pages.show_page(**params)
    
    async def update_page(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ],
        url_or_id: Annotated[
            str | int,
            Field(description="Page URL or ID")
        ],
        title: Annotated[
            str | None,
            Field(description="The title for the page")
        ] = None,
        body: Annotated[
            str | None,
            Field(description="The content for the page")
        ] = None,
        editing_roles: Annotated[
            str | None,
            Field(description="Which user roles are allowed to edit this page (comma-separated): teachers, students, members, public")
        ] = None,
        notify_of_update: Annotated[
            bool | str | None,
            Field(description="Whether participants should be notified when this page changes")
        ] = None,
        published: Annotated[
            bool | str | None,
            Field(description="Whether the page is published (true) or draft state (false)")
        ] = None,
        publish_at: Annotated[
            datetime | None,
            Field(description="Schedule a future date/time to publish the page")
        ] = None,
        front_page: Annotated[
            bool | str | None,
            Field(description="Set an unhidden page as the front page (if true)")
        ] = None
    ) -> dict:
        """Update the title or contents of a wiki page."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            url_or_id=url_or_id,
            title=title,
            body=body,
            editing_roles=editing_roles,
            notify_of_update=notify_of_update,
            published=published,
            publish_at=publish_at,
            front_page=front_page
        )
        return pages.update_page(**params)
    
    async def delete_page(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ],
        url_or_id: Annotated[
            str | int,
            Field(description="Page URL or ID")
        ]
    ) -> dict:
        """Delete a wiki page."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            url_or_id=url_or_id
        )
        return pages.delete_page(**params)
    
    async def list_revisions(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ],
        url_or_id: Annotated[
            str | int,
            Field(description="Page URL or ID")
        ],
        all_pages: Annotated[
            bool | str | None,
            Field(description="If True, fetch all pages automatically. If False, return only first page")
        ] = False
    ) -> list[dict]:
        """List revisions of a page. Requires update rights on the page."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            url_or_id=url_or_id,
            all_pages=all_pages
        )
        return pages.list_revisions(**params)
    
    async def show_revision(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ],
        url_or_id: Annotated[
            str | int,
            Field(description="Page URL or ID")
        ],
        revision_id: Annotated[
            str | int,
            Field(description="Revision ID or 'latest'")
        ] = "latest",
        summary: Annotated[
            bool | str | None,
            Field(description="If set, exclude page content from results")
        ] = None
    ) -> dict:
        """Retrieve the metadata and optionally content of a revision of the page."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            url_or_id=url_or_id,
            revision_id=revision_id,
            summary=summary
        )
        return pages.show_revision(**params)
    
    async def revert_to_revision(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Either 'courses' or 'groups'")
        ],
        context_id: Annotated[
            str | int,
            Field(description="Course or group ID")
        ],
        url_or_id: Annotated[
            str | int,
            Field(description="Page URL or ID")
        ],
        revision_id: Annotated[
            str | int,
            Field(description="The revision to revert to")
        ]
    ) -> dict:
        """Revert a page to a prior revision."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            url_or_id=url_or_id,
            revision_id=revision_id
        )
        return pages.revert_to_revision(**params)