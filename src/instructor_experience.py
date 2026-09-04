"""Registration entry point for Canvas resources and instructor prompts."""

from fastmcp import FastMCP

from prompts.instructor_workflows import register_instructor_prompts
from resources.instructor_support import register_instructor_resources


def register_instructor_experience(mcp: FastMCP) -> None:
    """Add compact Canvas resource templates and reusable workflow prompts."""
    register_instructor_resources(mcp)
    register_instructor_prompts(mcp)
