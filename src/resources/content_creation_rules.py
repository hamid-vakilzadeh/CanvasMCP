"""MCP Resource for Canvas Content Creation Rules and Guidelines."""

from pathlib import Path
from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError


def register_content_creation_resource(mcp: FastMCP) -> None:
    """Register the Canvas content creation reference resource with the MCP server."""

    @mcp.resource(
        uri="resource://content-creation-reference",
        name="Canvas Content Creation Reference",
        description="Practical Canvas HTML/CSS guidance with a link to the current official allowlist",
        mime_type="text/markdown",
        tags={"canvas", "html", "css", "content-creation", "reference"},
        annotations={"readOnlyHint": True, "idempotentHint": True},
        meta={
            "version": "1.0",
            "category": "documentation",
            "content_type": "reference_guide",
        },
    )
    async def get_canvas_content_creation_reference() -> str:
        """
        Canvas LMS Content Creation Reference Guide

        Returns focused authoring guidance, context-specific restrictions,
        accessibility advice, and the official source for complete current rules.
        """
        try:
            # Get the path to the reference file using pathlib
            current_dir = Path(__file__).parent
            reference_path = (
                current_dir / "content" / "canvas_content_creation_reference.md"
            )

            if not reference_path.exists():
                raise ResourceError(
                    f"Canvas content creation reference file not found at: {reference_path}"
                )

            # Read the reference content asynchronously
            content = reference_path.read_text(encoding="utf-8")

            if not content.strip():
                raise ResourceError("Canvas content creation reference file is empty")

            return content

        except ResourceError:
            # Re-raise ResourceError as-is (these provide good error messages to the client)
            raise
        except Exception as e:
            # Wrap other exceptions in ResourceError for better client handling
            raise ResourceError(
                f"Failed to load Canvas content creation reference: {str(e)}"
            )
