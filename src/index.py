from fastmcp import FastMCP
from typing import Annotated
from datetime import datetime

from pydantic import Field

from canvasAPI.module import modules
from canvasAPI.course import courses

mcp = FastMCP(name="Canvas Assistant")


@mcp.tool(tags={"module"})
async def create_new_module(
    course_id: Annotated[
        int, Field(description="The course ID where the module should be added")
    ],
    name: Annotated[str, Field(description="The name of the module")],
    unlock_at: Annotated[
        datetime | None, Field(description="The date the module will unlock")
    ] = None,
    position: Annotated[
        int | None,
        Field(description="The position of this module in the course (1-based)"),
    ] = None,
    require_sequential_progress: Annotated[
        bool | None, Field(description="Whether module items must be unlocked in order")
    ] = None,
    prerequisite_module_ids: Annotated[
        list[str] | None,
        Field(
            description="IDs of Modules that must be completed before this one is unlocked. Prerequisite modules must precede this module (i.e. have a lower position value), otherwise they will be ignored"
        ),
    ] = None,
    publish_final_grade: Annotated[
        bool | None,
        Field(
            description="Whether to publish the student’s final grade for the course upon completion of this module.",
        ),
    ] = None,
) -> list[int]:
    """Create new Module in a course"""
    return await modules.create_module(
        course_id=course_id,
        name=name,
        unlock_at=unlock_at,
        position=position,
        require_sequential_progress=require_sequential_progress,
        prerequisite_module_ids=prerequisite_module_ids,
        publish_final_grade=publish_final_grade,
    )


@mcp.tool(tags={"course"})
async def list_courses():
    return await courses.list_courses()


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
