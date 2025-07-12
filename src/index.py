from fastmcp import FastMCP
from typing import Annotated
from datetime import datetime

from pydantic import Field

from canvasAPI.module import modules
from canvasAPI.course import courses


def validate_and_convert_params(**kwargs):
    """
    Validate and convert parameter values to their expected types.

    Converts:
    - String representations of numbers to int/float
    - String representations of booleans to bool
    - String representations of lists to actual lists
    - JSON-like string representations of lists
    """
    import json
    import re

    converted = {}

    for key, value in kwargs.items():
        if value is None:
            converted[key] = value
            continue

        # Convert string numbers to int
        if isinstance(value, str) and value.isdigit():
            converted[key] = int(value)
        # Convert string floats to float
        elif isinstance(value, str) and value.replace(".", "", 1).isdigit():
            converted[key] = float(value)
        # Convert string booleans to bool
        elif isinstance(value, str) and value.lower() in ("true", "false"):
            converted[key] = value.lower() == "true"
        # Convert JSON-like string lists [1,2,3] or [3872065]
        elif (
            isinstance(value, str)
            and value.strip().startswith("[")
            and value.strip().endswith("]")
        ):
            try:
                # Try to parse as JSON
                converted[key] = json.loads(value)
            except json.JSONDecodeError:
                # Fallback: extract numbers from [3872065] format
                numbers = re.findall(r"\d+", value)
                if numbers:
                    converted[key] = [int(num) for num in numbers]
                else:
                    converted[key] = value
        # Convert string lists (basic comma-separated)
        elif isinstance(value, str) and "," in value:
            # Try to convert to list of ints if all elements are numeric
            try:
                converted[key] = [int(x.strip()) for x in value.split(",")]
            except ValueError:
                converted[key] = [x.strip() for x in value.split(",")]
        else:
            converted[key] = value

    return converted


mcp = FastMCP(name="Canvas Assistant")


@mcp.tool(tags={"course"})
async def list_courses() -> list[dict]:
    """Get a list of all the courses the user has taught as a teacher.
    Use this function to get course information such as course name, course ID and term informaiton.
    """
    result = courses.list_courses(
        enrollment_type="teacher", include=["term"], all_pages=True
    )

    courses_list = [
        {
            "course_id": item["id"],
            "course_name": item["name"],
            "term_id": item["term"]["id"],
            "term_name": item["term"]["name"],
        }
        for item in result
    ]

    return courses_list


@mcp.tool(tags={"module"})
async def create_module(
    course_id: Annotated[
        str | int, Field(description="The course ID where the module should be added")
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
            description="Whether to publish the student’s final grade for the course upon completion of this module.",
        ),
    ] = None,
) -> dict:
    """Create new Module in a course."""
    # Validate and convert parameters
    params = validate_and_convert_params(
        course_id=course_id,
        name=name,
        unlock_at=unlock_at,
        position=position,
        require_sequential_progress=require_sequential_progress,
        prerequisite_module_ids=prerequisite_module_ids,
        publish_final_grade=publish_final_grade,
    )

    return modules.create_module(**params)


@mcp.tool(tags={"module"})
async def list_modules(
    course_id: Annotated[
        str | int, Field(description="The course ID to list modules from")
    ],
    include: Annotated[
        list[str] | str | None,
        Field(description="Additional data to include: 'items', 'content_details'"),
    ] = None,
    search_term: Annotated[
        str | None, Field(description="Partial name of modules to match")
    ] = None,
    student_id: Annotated[
        str | int | None,
        Field(description="Returns module completion information for this student"),
    ] = None,
    all_pages: Annotated[
        bool | str | None,
        Field(description="If true, fetch all pages automatically"),
    ] = False,
) -> list[dict]:
    """List modules in a course."""
    params = validate_and_convert_params(
        course_id=course_id,
        include=include,
        search_term=search_term,
        student_id=student_id,
        all_pages=all_pages,
    )
    return modules.list_modules(**params)


@mcp.tool(tags={"module"})
async def show_module(
    course_id: Annotated[
        str | int, Field(description="The course ID")
    ],
    module_id: Annotated[
        str | int, Field(description="The module ID to show")
    ],
    include: Annotated[
        list[str] | str | None,
        Field(description="Additional data to include: 'items', 'content_details'"),
    ] = None,
    student_id: Annotated[
        str | int | None,
        Field(description="Returns module completion information for this student"),
    ] = None,
) -> dict:
    """Get information about a single module."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        include=include,
        student_id=student_id,
    )
    return modules.show_module(**params)


@mcp.tool(tags={"module"})
async def update_module(
    course_id: Annotated[
        str | int, Field(description="The course ID")
    ],
    module_id: Annotated[
        str | int, Field(description="The module ID to update")
    ],
    name: Annotated[
        str | None, Field(description="The name of the module")
    ] = None,
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
    params = validate_and_convert_params(
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
    return modules.update_module(**params)


@mcp.tool(tags={"module"})
async def delete_module(
    course_id: Annotated[
        str | int, Field(description="The course ID")
    ],
    module_id: Annotated[
        str | int, Field(description="The module ID to delete")
    ],
) -> dict:
    """Delete a module."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
    )
    return modules.delete_module(**params)


@mcp.tool(tags={"module"})
async def relock_module(
    course_id: Annotated[
        str | int, Field(description="The course ID")
    ],
    module_id: Annotated[
        str | int, Field(description="The module ID to relock")
    ],
) -> dict:
    """Re-lock module progressions to reset them to default locked state."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
    )
    return modules.relock_module(**params)


@mcp.tool(tags={"module"})
async def list_module_items(
    course_id: Annotated[
        str | int, Field(description="The course ID")
    ],
    module_id: Annotated[
        str | int, Field(description="The module ID to list items from")
    ],
    include: Annotated[
        list[str] | str | None,
        Field(description="Additional data to include: 'content_details'"),
    ] = None,
    search_term: Annotated[
        str | None, Field(description="Partial title of items to match")
    ] = None,
    student_id: Annotated[
        str | int | None,
        Field(description="Returns module completion information for this student"),
    ] = None,
    all_pages: Annotated[
        bool | str | None,
        Field(description="If true, fetch all pages automatically"),
    ] = False,
) -> list[dict]:
    """List items in a module."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        include=include,
        search_term=search_term,
        student_id=student_id,
        all_pages=all_pages,
    )
    return modules.list_module_items(**params)


@mcp.tool(tags={"module"})
async def show_module_item(
    course_id: Annotated[
        str | int, Field(description="The course ID")
    ],
    module_id: Annotated[
        str | int, Field(description="The module ID")
    ],
    item_id: Annotated[
        str | int, Field(description="The module item ID to show")
    ],
    include: Annotated[
        list[str] | str | None,
        Field(description="Additional data to include: 'content_details'"),
    ] = None,
    student_id: Annotated[
        str | int | None,
        Field(description="Returns module completion information for this student"),
    ] = None,
) -> dict:
    """Get information about a single module item."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        item_id=item_id,
        include=include,
        student_id=student_id,
    )
    return modules.show_module_item(**params)


@mcp.tool(tags={"module"})
async def create_module_item(
    course_id: Annotated[
        str | int, Field(description="The course ID")
    ],
    module_id: Annotated[
        str | int, Field(description="The module ID to add item to")
    ],
    item_type: Annotated[
        str,
        Field(description="Type of content: File, Page, Discussion, Assignment, Quiz, SubHeader, ExternalUrl, ExternalTool"),
    ],
    title: Annotated[
        str | None, Field(description="Name of the module item")
    ] = None,
    content_id: Annotated[
        str | int | None,
        Field(description="ID of content to link (required except for ExternalUrl, Page, SubHeader)"),
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
        str | None, Field(description="Wiki page URL suffix (required for Page type)")
    ] = None,
    external_url: Annotated[
        str | None, Field(description="External URL (required for ExternalUrl and ExternalTool)")
    ] = None,
    new_tab: Annotated[
        bool | str | None,
        Field(description="Whether external tool opens in new tab (ExternalTool only)"),
    ] = None,
    completion_requirement_type: Annotated[
        str | None,
        Field(description="Completion requirement: must_view, must_contribute, must_submit, must_mark_done"),
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
    params = validate_and_convert_params(
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
    return modules.create_module_item(**params)


@mcp.tool(tags={"module"})
async def update_module_item(
    course_id: Annotated[
        str | int, Field(description="The course ID")
    ],
    module_id: Annotated[
        str | int, Field(description="The module ID")
    ],
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
        Field(description="Whether external tool opens in new tab (ExternalTool only)"),
    ] = None,
    completion_requirement_type: Annotated[
        str | None,
        Field(description="Completion requirement: must_view, must_contribute, must_submit, must_mark_done"),
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
    params = validate_and_convert_params(
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
    return modules.update_module_item(**params)


@mcp.tool(tags={"module"})
async def delete_module_item(
    course_id: Annotated[
        str | int, Field(description="The course ID")
    ],
    module_id: Annotated[
        str | int, Field(description="The module ID")
    ],
    item_id: Annotated[
        str | int, Field(description="The module item ID to delete")
    ],
) -> dict:
    """Delete a module item."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        item_id=item_id,
    )
    return modules.delete_module_item(**params)


if __name__ == "__main__":
    mcp.run()
