"""Base tool provider class for organizing Canvas MCP tools."""

import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Callable
from functools import wraps
from fastmcp import FastMCP
from analytics import get_analytics_client
from analytics.error_sanitizer import sanitize_error

logger = logging.getLogger(__name__)


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


def track_tool_execution(func: Callable) -> Callable:
    """
    Decorator to track tool execution analytics.

    This decorator:
    1. Captures execution time
    2. Extracts owner_id and session_id from context
    3. Tracks success/failure with sanitized errors
    4. Never blocks tool execution

    Args:
        func: The tool function to wrap

    Returns:
        Wrapped function with analytics tracking
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get analytics client
        analytics_client = get_analytics_client()

        # Extract tool name from function
        tool_name = func.__name__

        # Try to extract context information
        owner_id = None
        session_id = None

        try:
            # Try to get context from FastMCP
            from fastmcp.server.dependencies import get_context

            ctx = get_context()
            if ctx:
                owner_id = ctx.get_state("owner_id")
                session_id = ctx.get_state("session_id")
        except Exception:
            # Context not available, continue without it
            pass

        # Track execution
        start_time = time.time()
        error_info = None
        success = False

        try:
            # Execute the actual tool
            result = await func(*args, **kwargs)
            success = True
            return result

        except Exception as e:
            # Capture error for analytics
            error_info = e
            raise  # Re-raise to maintain normal error flow

        finally:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Track the execution (never let this fail)
            try:
                if error_info:
                    error_type, error_details = sanitize_error(error_info)
                else:
                    error_type, error_details = None, None

                analytics_client.track_tool_execution(
                    tool_name=tool_name,
                    owner_id=owner_id,
                    session_id=session_id,
                    duration_ms=duration_ms,
                    success=success,
                    error_type=error_type,
                    error_details=error_details,
                )

            except Exception as e:
                # Never let analytics errors affect tool execution
                logger.debug(f"Failed to track analytics for {tool_name}: {e}")

    return wrapper


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
        self._analytics_enabled = self._check_analytics_enabled()
        self._register_tools()

    def _check_analytics_enabled(self) -> bool:
        """Check if analytics is enabled."""
        import os

        return os.getenv("ANALYTICS_ENABLED", "false").lower() == "true"

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

    def _wrap_tool_with_analytics(self, tool_func: Callable) -> Callable:
        """
        Wrap a tool function with analytics tracking if enabled.

        Args:
            tool_func: The tool function to wrap

        Returns:
            Wrapped function with analytics or original function
        """
        if self._analytics_enabled:
            return track_tool_execution(tool_func)
        return tool_func
