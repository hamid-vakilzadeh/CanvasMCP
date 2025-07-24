"""Module-related tools for Canvas MCP."""

from typing import Annotated, Literal
from datetime import datetime
from pydantic import Field

from .base import ToolProvider
from canvasAPI.module import modules
from tools.getToken import get_user_token


class ModuleTools(ToolProvider):
    """Tools for managing Canvas modules."""

    def _register_tools(self):
        """Register all module-related tools."""
        self.mcp.tool(self.create_module, tags={"module"})
        self.mcp.tool(self.list_modules, tags={"module"})
        self.mcp.tool(self.show_module, tags={"module"})
        self.mcp.tool(self.update_module, tags={"module"})
        self.mcp.tool(self.delete_module, tags={"module"})
        self.mcp.tool(self.relock_module, tags={"module"})
        self.mcp.tool(self.list_module_items, tags={"module"})
        self.mcp.tool(self.show_module_item, tags={"module"})
        self.mcp.tool(self.create_module_item, tags={"module"})
        self.mcp.tool(self.update_module_item, tags={"module"})
        self.mcp.tool(self.delete_module_item, tags={"module"})

    async def create_module(
        self,
        course_id: Annotated[
            str | int,
            Field(description="The course ID where the module should be added"),
        ],
        name: Annotated[str, Field(description="The name of the module")],
        unlock_at: Annotated[
            datetime | None, Field(description="The date the module will unlock")
        ] = None,
        position: Annotated[
            int | str | None,
            Field(
                description="The position of this module in the course (1-based) in integer format."
            ),
        ] = None,
        require_sequential_progress: Annotated[
            bool | str | None,
            Field(description="Whether module items must be unlocked in order"),
        ] = None,
        prerequisite_module_ids: Annotated[
            list[int | str] | str | None,
            Field(
                description="IDs of Modules that must be completed before this one is unlocked. Prerequisite modules must precede this module (i.e. have a lower position value), otherwise they will be ignored"
            ),
        ] = None,
        publish_final_grade: Annotated[
            bool | str | None,
            Field(
                description="Whether to publish the student's final grade for the course upon completion of this module.",
            ),
        ] = None,
    ) -> dict:
        """Create new Module in a course."""
        params = self._validate_params(
            course_id=course_id,
            name=name,
            unlock_at=unlock_at,
            position=position,
            require_sequential_progress=require_sequential_progress,
            prerequisite_module_ids=prerequisite_module_ids,
            publish_final_grade=publish_final_grade,
        )

        params["base_url"], params["access_token"] = get_user_token()

        return modules.create_module(**params)

    async def list_modules(
        self,
        course_id: Annotated[
            str | int, Field(description="The course ID to list modules from")
        ],
        include: Annotated[
            list[Literal["items", "content_details"]] | str | None,
            Field(description="Additional data to include: 'items', 'content_details'"),
        ] = None,
        search_term: Annotated[
            str | None, Field(description="Partial name of modules to match")
        ] = None,
        student_id: Annotated[
            str | int | None,
            Field(description="Returns module completion information for this student"),
        ] = None,
    ) -> list[dict]:
        """List modules in a course."""
        params = self._validate_params(
            course_id=course_id,
            include=include,
            search_term=search_term,
            student_id=student_id,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.list_modules(**params)

    async def show_module(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        module_id: Annotated[str | int, Field(description="The module ID to show")],
        include: Annotated[
            list[Literal["items", "content_details"]] | str | None,
            Field(description="Additional data to include: 'items', 'content_details'"),
        ] = None,
        student_id: Annotated[
            str | int | None,
            Field(description="Returns module completion information for this student"),
        ] = None,
    ) -> dict:
        """Get information about a single module."""
        params = self._validate_params(
            course_id=course_id,
            module_id=module_id,
            include=include,
            student_id=student_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.show_module(**params)

    async def update_module(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        module_id: Annotated[str | int, Field(description="The module ID to update")],
        name: Annotated[str | None, Field(description="The name of the module")] = None,
        unlock_at: Annotated[
            datetime | None, Field(description="The date the module will unlock")
        ] = None,
        position: Annotated[
            int | str | None,
            Field(description="The position of this module in the course (1-based)"),
        ] = None,
        require_sequential_progress: Annotated[
            bool | str | None,
            Field(description="Whether module items must be unlocked in order"),
        ] = None,
        prerequisite_module_ids: Annotated[
            list[int | str] | str | None,
            Field(description="IDs of Modules that must be completed before this one"),
        ] = None,
        publish_final_grade: Annotated[
            bool | str | None,
            Field(description="Whether to publish final grade upon completion"),
        ] = None,
        published: Annotated[
            bool | str | None,
            Field(description="Whether module is published and visible to students"),
        ] = None,
    ) -> dict:
        """Update an existing module."""
        params = self._validate_params(
            course_id=course_id,
            module_id=module_id,
            name=name,
            unlock_at=unlock_at,
            position=position,
            require_sequential_progress=require_sequential_progress,
            prerequisite_module_ids=prerequisite_module_ids,
            publish_final_grade=publish_final_grade,
            published=published,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.update_module(**params)

    async def delete_module(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        module_id: Annotated[str | int, Field(description="The module ID to delete")],
    ) -> dict:
        """Delete a module."""
        params = self._validate_params(
            course_id=course_id,
            module_id=module_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.delete_module(**params)

    async def relock_module(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        module_id: Annotated[str | int, Field(description="The module ID to relock")],
    ) -> dict:
        """Re-lock module progressions to reset them to default locked state."""
        params = self._validate_params(
            course_id=course_id,
            module_id=module_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.relock_module(**params)

    async def list_module_items(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        module_id: Annotated[
            str | int, Field(description="The module ID to list items from")
        ],
        include: Annotated[
            list[Literal["content_details"]] | str | None,
            Field(description="Additional data to include: 'content_details'"),
        ] = None,
        search_term: Annotated[
            str | None, Field(description="Partial title of items to match")
        ] = None,
        student_id: Annotated[
            str | int | None,
            Field(description="Returns module completion information for this student"),
        ] = None,
    ) -> list[dict]:
        """List items in a module."""
        params = self._validate_params(
            course_id=course_id,
            module_id=module_id,
            include=include,
            search_term=search_term,
            student_id=student_id,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.list_module_items(**params)

    async def show_module_item(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        module_id: Annotated[str | int, Field(description="The module ID")],
        item_id: Annotated[str | int, Field(description="The module item ID to show")],
        include: Annotated[
            list[Literal["content_details"]] | str | None,
            Field(description="Additional data to include: 'content_details'"),
        ] = None,
        student_id: Annotated[
            str | int | None,
            Field(description="Returns module completion information for this student"),
        ] = None,
    ) -> dict:
        """Get information about a single module item."""
        params = self._validate_params(
            course_id=course_id,
            module_id=module_id,
            item_id=item_id,
            include=include,
            student_id=student_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.show_module_item(**params)

    async def create_module_item(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        module_id: Annotated[
            str | int, Field(description="The module ID to add item to")
        ],
        item_type: Annotated[
            Literal[
                "File",
                "Page",
                "Discussion",
                "Assignment",
                "Quiz",
                "SubHeader",
                "ExternalUrl",
                "ExternalTool",
            ],
            Field(
                description="Type of content: File, Page, Discussion, Assignment, Quiz, SubHeader, ExternalUrl, ExternalTool"
            ),
        ],
        title: Annotated[
            str | None, Field(description="Name of the module item")
        ] = None,
        content_id: Annotated[
            str | int | None,
            Field(
                description="ID of content to link (required except for ExternalUrl, Page, SubHeader)"
            ),
        ] = None,
        position: Annotated[
            int | str | None,
            Field(description="Position in module (1-based)"),
        ] = None,
        indent: Annotated[
            int | str | None,
            Field(description="0-based indent level"),
        ] = None,
        page_url: Annotated[
            str | None,
            Field(description="Wiki page URL suffix (required for Page type)"),
        ] = None,
        external_url: Annotated[
            str | None,
            Field(
                description="External URL (required for ExternalUrl and ExternalTool)"
            ),
        ] = None,
        new_tab: Annotated[
            bool | str | None,
            Field(
                description="Whether external tool opens in new tab (ExternalTool only)"
            ),
        ] = None,
        completion_requirement_type: Annotated[
            Literal["must_view", "must_contribute", "must_submit", "must_mark_done"]
            | None,
            Field(
                description="Completion requirement: must_view, must_contribute, must_submit, must_mark_done"
            ),
        ] = None,
        completion_requirement_min_score: Annotated[
            int | str | None,
            Field(description="Min score for completion (min_score type only)"),
        ] = None,
        iframe_width: Annotated[
            int | str | None,
            Field(description="ExternalTool launch width"),
        ] = None,
        iframe_height: Annotated[
            int | str | None,
            Field(description="ExternalTool launch height"),
        ] = None,
    ) -> dict:
        """Create a new module item."""
        params = self._validate_params(
            course_id=course_id,
            module_id=module_id,
            item_type=item_type,
            title=title,
            content_id=content_id,
            position=position,
            indent=indent,
            page_url=page_url,
            external_url=external_url,
            new_tab=new_tab,
            completion_requirement_type=completion_requirement_type,
            completion_requirement_min_score=completion_requirement_min_score,
            iframe_width=iframe_width,
            iframe_height=iframe_height,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.create_module_item(**params)

    async def update_module_item(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        module_id: Annotated[str | int, Field(description="The module ID")],
        item_id: Annotated[
            str | int, Field(description="The module item ID to update")
        ],
        title: Annotated[
            str | None, Field(description="Name of the module item")
        ] = None,
        position: Annotated[
            int | str | None,
            Field(description="Position in module (1-based)"),
        ] = None,
        indent: Annotated[
            int | str | None,
            Field(description="0-based indent level"),
        ] = None,
        external_url: Annotated[
            str | None, Field(description="External URL (ExternalUrl type only)")
        ] = None,
        new_tab: Annotated[
            bool | str | None,
            Field(
                description="Whether external tool opens in new tab (ExternalTool only)"
            ),
        ] = None,
        completion_requirement_type: Annotated[
            Literal["must_view", "must_contribute", "must_submit", "must_mark_done"]
            | None,
            Field(
                description="Completion requirement: must_view, must_contribute, must_submit, must_mark_done"
            ),
        ] = None,
        completion_requirement_min_score: Annotated[
            int | str | None,
            Field(description="Min score for completion (min_score type only)"),
        ] = None,
        published: Annotated[
            bool | str | None,
            Field(description="Whether item is published and visible to students"),
        ] = None,
        target_module_id: Annotated[
            str | int | None,
            Field(description="Move item to another module"),
        ] = None,
    ) -> dict:
        """Update an existing module item."""
        params = self._validate_params(
            course_id=course_id,
            module_id=module_id,
            item_id=item_id,
            title=title,
            position=position,
            indent=indent,
            external_url=external_url,
            new_tab=new_tab,
            completion_requirement_type=completion_requirement_type,
            completion_requirement_min_score=completion_requirement_min_score,
            published=published,
            target_module_id=target_module_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.update_module_item(**params)

    async def delete_module_item(
        self,
        course_id: Annotated[str | int, Field(description="The course ID")],
        module_id: Annotated[str | int, Field(description="The module ID")],
        item_id: Annotated[
            str | int, Field(description="The module item ID to delete")
        ],
    ) -> dict:
        """Delete a module item."""
        params = self._validate_params(
            course_id=course_id,
            module_id=module_id,
            item_id=item_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return modules.delete_module_item(**params)
