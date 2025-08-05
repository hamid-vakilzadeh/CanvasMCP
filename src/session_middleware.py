"""Session-based authentication middleware for Canvas MCP server."""

import logging
from typing import Optional
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mcp import McpError
from mcp.types import ErrorData

from session_manager import session_manager
from tools.getToken import verify_key, decrypt_token_with_api_key

logger = logging.getLogger(__name__)


class SessionAuthMiddleware(Middleware):
    """
    Middleware that handles session-based authentication for Canvas MCP.

    This middleware:
    1. Checks if a valid session exists for the current request
    2. If not, authenticates using API key and creates a new session
    3. If yes, extends the session timeout
    4. Stores credentials in context state for tools to access
    """

    def __init__(self):
        """Initialize the session authentication middleware."""
        super().__init__()

    async def on_request(self, context: MiddlewareContext, call_next):
        """
        Handle authentication for all MCP requests.

        Args:
            context: The middleware context containing request information
            call_next: Function to continue the middleware chain
        """
        try:
            # Get session ID from MCP context (available with stateful HTTP transport)
            session_id = None
            if context.fastmcp_context and hasattr(
                context.fastmcp_context, "session_id"
            ):
                session_id = context.fastmcp_context.session_id

            # If no session ID available, try to extract from HTTP request
            if not session_id:
                session_id = await self._extract_session_id_from_request(context)

            if not session_id:
                # Create a session ID from API key if no session context available
                api_key = await self._extract_api_key_from_request(context)
                if api_key:
                    # Use a hash of the API key as session ID for stateless scenarios
                    import hashlib

                    session_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]

            if not session_id:
                raise McpError(
                    ErrorData(
                        code=-32000, message="Unable to establish session context"
                    )
                )

            # Try to get existing session credentials
            credentials = session_manager.get_session(session_id)

            if credentials:
                # Session exists and is valid - but we still need to validate API key for rate limiting
                base_url, access_token = credentials
                print(f"🔄 [SESSION] Found existing session: {session_id[:8]}...")
                
                # Get API key for validation (required for rate limiting)
                api_key = await self._extract_api_key_from_request(context)
                if not api_key:
                    raise ValueError("API key required for rate limit validation")
                
                print(f"🔑 [RATE-LIMIT] Validating API key: {api_key[:10]}...")
                
                # Verify API key is still valid (for rate limiting)
                verification_result = verify_key(api_key)
                if not verification_result.get("valid", False):
                    # API key is invalid, remove session and force re-auth
                    session_manager.remove_session(session_id)
                    raise ValueError("API key validation failed - session invalidated")
                
                print("✅ [RATE-LIMIT] API key validated, using cached token")
                logger.debug(f"Using existing session with validated API key: {session_id}")
            else:
                # No valid session - authenticate and create new session
                print(f"🔐 [AUTH] Creating new session: {session_id[:8]}...")
                logger.debug(f"Creating new session: {session_id}")
                base_url, access_token, api_key = await self._authenticate_user(context)
                session_manager.create_session(
                    session_id, base_url, access_token, api_key
                )
                print(f"✅ [SESSION] New session created for Canvas instance: {base_url}")

            # Store credentials in FastMCP context state for tools to access
            if context.fastmcp_context:
                context.fastmcp_context.set_state("canvas_base_url", base_url)
                context.fastmcp_context.set_state("canvas_access_token", access_token)
                context.fastmcp_context.set_state("session_id", session_id)
                print("📝 [STATE] Credentials stored in FastMCP context")

            # Continue with the request
            return await call_next(context)

        except Exception as e:
            logger.error(f"Session authentication failed: {e}")
            raise McpError(
                ErrorData(code=-32001, message=f"Authentication failed: {str(e)}")
            )

    async def _extract_session_id_from_request(
        self, context: MiddlewareContext
    ) -> Optional[str]:
        """
        Extract session ID from HTTP request context.

        Args:
            context: The middleware context

        Returns:
            Session ID if available, None otherwise
        """
        try:
            from fastmcp.server.dependencies import get_http_request

            request = get_http_request()
            if not request:
                return None

            # Try to get session ID from headers
            if hasattr(request, "headers"):
                session_id = request.headers.get("x-session-id")
                if session_id:
                    return session_id

            # Try to get from query parameters
            if hasattr(request, "query_params"):
                session_id = request.query_params.get("session_id")
                if session_id:
                    return session_id

            return None

        except Exception as e:
            logger.debug(f"Could not extract session ID from request: {e}")
            return None

    async def _extract_api_key_from_request(
        self, context: MiddlewareContext
    ) -> Optional[str]:
        """
        Extract API key from HTTP request.

        Args:
            context: The middleware context

        Returns:
            API key if found, None otherwise
        """
        try:
            from fastmcp.server.dependencies import get_http_request

            request = get_http_request()
            if not request:
                return None

            # Try query parameters first
            if hasattr(request, "query_params"):
                api_key = request.query_params.get("apikey")
                if api_key:
                    return api_key

            # Try to extract from URL if available
            if hasattr(request, "url"):
                import urllib.parse

                parsed = urllib.parse.urlparse(str(request.url))
                params = urllib.parse.parse_qs(parsed.query)
                api_key = params.get("apikey", [None])[0]
                if api_key:
                    return api_key

            return None

        except Exception as e:
            logger.debug(f"Could not extract API key from request: {e}")
            return None

    async def _authenticate_user(
        self, context: MiddlewareContext
    ) -> tuple[str, str, str]:
        """
        Authenticate user using API key and return Canvas credentials.

        Args:
            context: The middleware context

        Returns:
            Tuple of (base_url, access_token, api_key)
        """
        # Extract API key from request
        api_key = await self._extract_api_key_from_request(context)
        if not api_key:
            raise ValueError("API key required in query parameters (?apikey=your_key)")

        print(f"🔑 [AUTH] Verifying API key: {api_key[:10]}...")

        # Verify API key with Unkey
        verification_result = verify_key(api_key)
        if not verification_result.get("valid", False):
            raise ValueError("Invalid API key")

        print("✅ [AUTH] API key verified successfully")

        # Extract Canvas credentials from meta object
        meta = verification_result.get("meta", {})
        base_url = meta.get("profileUrl")
        encrypted_access_token = meta.get("encryptedAccessToken")

        if not encrypted_access_token:
            raise ValueError("Encrypted access token not found in API key metadata")

        print("🔓 [AUTH] Decrypting access token...")
        
        # Decrypt access token
        access_token = decrypt_token_with_api_key(encrypted_access_token, api_key)

        if not base_url or not access_token:
            raise ValueError("Canvas credentials not found in API key metadata")

        print(f"✅ [AUTH] Token decrypted successfully for Canvas: {base_url}")
        logger.info(f"Successfully authenticated user for Canvas instance: {base_url}")
        return base_url, access_token, api_key


class SessionManagementMiddleware(Middleware):
    """
    Middleware for managing session lifecycle and cleanup.

    This middleware starts/stops the session cleanup task and provides
    monitoring capabilities for session management.
    """

    def __init__(self):
        """Initialize the session management middleware."""
        super().__init__()
        self._cleanup_started = False

    async def on_message(self, context: MiddlewareContext, call_next):
        """
        Handle session management for all messages.

        Args:
            context: The middleware context
            call_next: Function to continue the middleware chain
        """
        # Start cleanup task on first request if not already started
        if not self._cleanup_started:
            session_manager.start_cleanup_task()
            self._cleanup_started = True
            print("🧹 [SESSION] Cleanup task started (removes expired sessions every 5 minutes)")
            logger.info("Session cleanup task started")

        return await call_next(context)
