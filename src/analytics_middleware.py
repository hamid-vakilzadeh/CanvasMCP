"""Analytics middleware for tracking tool usage in Canvas MCP."""

import logging
import time
from fastmcp.server.middleware import Middleware, MiddlewareContext
from analytics import get_analytics_client
from analytics.error_sanitizer import sanitize_error

logger = logging.getLogger(__name__)


class AnalyticsMiddleware(Middleware):
    """
    Middleware that tracks tool execution analytics.

    This middleware:
    1. Captures tool execution start and end times
    2. Extracts owner_id from context (set by session middleware)
    3. Tracks success/failure with sanitized error details
    4. Never blocks tool execution due to analytics failures
    """

    def __init__(self):
        """Initialize the analytics middleware."""
        super().__init__()
        self.analytics_client = get_analytics_client()
        logger.info("Analytics middleware initialized")

    async def on_tool_call(self, context: MiddlewareContext, call_next):
        """
        Track tool execution analytics.

        Args:
            context: The middleware context containing tool information
            call_next: Function to continue the middleware chain
        """
        # Extract tool name from context
        tool_name = None
        if hasattr(context, "tool_name"):
            tool_name = context.tool_name
        elif context.message and hasattr(context.message, "params"):
            # Try to extract from message params
            if hasattr(context.message.params, "name"):
                tool_name = context.message.params.name

        # Skip if we can't determine the tool name
        if not tool_name:
            return await call_next(context)

        # Extract owner_id and session_id from context (set by session middleware)
        owner_id = None
        session_id = None

        try:
            if context.fastmcp_context:
                owner_id = context.fastmcp_context.get_state("owner_id")
                session_id = context.fastmcp_context.get_state("session_id")
        except Exception as e:
            logger.debug(f"Could not extract context data: {e}")

        # Track execution time
        start_time = time.time()
        error_info = None
        success = False

        try:
            # Execute the tool
            result = await call_next(context)
            success = True
            return result

        except Exception as e:
            # Capture and sanitize error information
            error_info = e
            raise  # Re-raise the error to maintain normal error handling

        finally:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Track the execution (never let this fail)
            try:
                if error_info:
                    error_type, error_details = sanitize_error(error_info)
                else:
                    error_type, error_details = None, None

                self.analytics_client.track_tool_execution(
                    tool_name=tool_name,
                    owner_id=owner_id,
                    session_id=session_id,
                    duration_ms=duration_ms,
                    success=success,
                    error_type=error_type,
                    error_details=error_details,
                )

            except Exception as analytics_error:
                # Never let analytics errors affect tool execution
                logger.debug(
                    f"Failed to track analytics for {tool_name}: {analytics_error}"
                )

    async def on_request(self, context: MiddlewareContext, call_next):
        """
        Handle analytics for all requests.

        This method can be used to track request-level analytics if needed.

        Args:
            context: The middleware context
            call_next: Function to continue the middleware chain
        """
        # For now, just pass through - tool-level tracking happens in on_tool_call
        return await call_next(context)

    async def on_message(self, context: MiddlewareContext, call_next):
        """
        Handle analytics for all messages.

        Args:
            context: The middleware context
            call_next: Function to continue the middleware chain
        """
        # Check if this is a tool call message
        if context.message and hasattr(context.message, "method"):
            if context.message.method == "tools/call":
                # This is a tool call, track it
                return await self.on_tool_call(context, call_next)

        # Not a tool call, just pass through
        return await call_next(context)
