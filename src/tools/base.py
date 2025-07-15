"""Base tool provider class for organizing Canvas MCP tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from fastmcp import FastMCP


def validate_and_convert_params(**kwargs) -> Dict[str, Any]:
    """
    Validate and convert parameter values to their expected types using eval().

    Args:
        **kwargs: Parameters to validate and convert

    Returns:
        Dict with converted parameter values
    """
    converted = {}

    for key, value in kwargs.items():
        if value is None:
            converted[key] = value
            continue

        # Keep non-strings as-is
        if not isinstance(value, str):
            converted[key] = value
            continue

        # Try to eval the string to convert it to proper type
        try:
            converted[key] = eval(value)
        except (SyntaxError, NameError, ValueError, TypeError):
            # If eval fails, keep as string
            converted[key] = value

    return converted


class ToolProvider(ABC):
    """
    Base class for tool providers that organize related Canvas API tools.

    This class follows the FastMCP pattern for registering instance methods
    as tools after creating the instance.
    """

    def __init__(self, mcp_instance: FastMCP):
        """
        Initialize the tool provider and register its tools.

        Args:
            mcp_instance: The FastMCP instance to register tools with
        """
        self.mcp = mcp_instance
        self._register_tools()

    @abstractmethod
    def _register_tools(self):
        """Register all tools provided by this class with the MCP instance."""
        pass

    def _validate_params(self, **kwargs) -> Dict[str, Any]:
        """
        Convenience method to validate and convert parameters.

        Args:
            **kwargs: Parameters to validate and convert

        Returns:
            Dict with converted parameter values
        """
        return validate_and_convert_params(**kwargs)
