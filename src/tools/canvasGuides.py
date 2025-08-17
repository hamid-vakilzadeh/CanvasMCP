"""Canvas reference tools for accessing Canvas documentation and guidelines."""

from typing import Annotated
from pydantic import Field
from pathlib import Path

from .base import ToolProvider


class CanvasReferenceTools(ToolProvider):
    """Tools for accessing Canvas reference documentation and guidelines."""

    def _register_tools(self):
        """Register all Canvas reference-related tools."""
        # Wrap tools with analytics if enabled
        get_rules_tool = self._wrap_tool_with_analytics(self.get_canvas_content_creation_rules)
        search_tool = self._wrap_tool_with_analytics(self.search_canvas_reference)
        
        self.mcp.tool(
            get_rules_tool,
            tags={"canvas", "reference", "documentation"},
        )
        self.mcp.tool(
            search_tool, tags={"canvas", "reference", "search"}
        )

    async def get_canvas_content_creation_rules(self) -> str:
        """
        Get the complete Canvas HTML/CSS content creation reference guide.

        This returns the comprehensive Canvas HTML allowlist including:
        - Allowed HTML tags and attributes
        - Permitted CSS properties
        - Security restrictions and protocols
        - MathML support details

        Use this when you need to understand what HTML/CSS is allowed in Canvas
        or when creating content that needs to work within Canvas security constraints.
        """
        try:
            # Get the path to the reference file
            reference_path = "content" / "canvas_content_creation_reference.md"

            if not reference_path.exists():
                return f"❌ Canvas content creation reference file not found at: {reference_path}"

            # Read the reference content
            content = reference_path.read_text(encoding="utf-8")

            if not content.strip():
                return "❌ Canvas content creation reference file is empty"

            return f"# Canvas Content Creation Reference\n\n{content}"

        except Exception as e:
            return f"❌ Error reading Canvas content creation reference: {str(e)}"

    async def search_canvas_reference(
        self,
        search_term: Annotated[
            str,
            Field(
                description="Term to search for in the Canvas reference (e.g., 'iframe', 'CSS properties', 'table')"
            ),
        ],
    ) -> str:
        """
        Search the Canvas content creation reference for specific terms.

        This searches through the Canvas HTML allowlist and returns relevant sections
        that match your search term. Useful for quickly finding information about
        specific HTML tags, CSS properties, or Canvas restrictions.

        Args:
            search_term: The term to search for (case-insensitive)
        """
        try:
            # Get the reference content first
            current_dir = Path(__file__).parent.parent
            reference_path = (
                current_dir
                / "resources"
                / "content"
                / "canvas_content_creation_reference.md"
            )

            if not reference_path.exists():
                return f"❌ Canvas content creation reference file not found at: {reference_path}"

            content = reference_path.read_text(encoding="utf-8")

            if not content.strip():
                return "❌ Canvas content creation reference file is empty"

            # Search for the term (case-insensitive)
            lines = content.split("\n")
            matching_sections = []
            current_section = ""
            current_section_lines = []

            search_lower = search_term.lower()

            for line in lines:
                # Track current section
                if line.startswith("#"):
                    # Save previous section if it had matches
                    if current_section_lines and any(
                        search_lower in line_text.lower()
                        for line_text in current_section_lines
                    ):
                        matching_sections.append(
                            "\n".join([current_section] + current_section_lines)
                        )

                    # Start new section
                    current_section = line
                    current_section_lines = []
                else:
                    current_section_lines.append(line)

            # Check final section
            if current_section_lines and any(
                search_lower in line_text.lower() for line_text in current_section_lines
            ):
                matching_sections.append(
                    "\n".join([current_section] + current_section_lines)
                )

            if not matching_sections:
                return f"🔍 No matches found for '{search_term}' in Canvas content creation reference.\n\nTry searching for:\n- HTML tag names (e.g., 'div', 'table', 'iframe')\n- CSS properties (e.g., 'margin', 'display', 'flex')\n- General terms (e.g., 'attributes', 'protocols', 'MathML')"

            result = f"🔍 Search results for '{search_term}' in Canvas Content Creation Reference:\n\n"
            result += "\n\n---\n\n".join(matching_sections)

            return result

        except Exception as e:
            return f"❌ Error searching Canvas content creation reference: {str(e)}"
