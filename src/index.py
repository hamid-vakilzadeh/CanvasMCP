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


if __name__ == "__main__":
    mcp.run()
