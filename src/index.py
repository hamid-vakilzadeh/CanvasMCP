"""Canvas MCP Server - Organized with Tool Providers."""

from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider

from tools.courses import CourseTools
from tools.modules import ModuleTools
from tools.quizzes import QuizTools, QuizQuestionTools, QuizQuestionGroupTools
from tools.pages import PageTools


def create_server():
    """Initialize the Canvas MCP server with JWT authentication."""
    # Configure Bearer token authentication
    # The JWT should contain 'canvas_url' and 'access_token' claims
    auth = BearerAuthProvider(
        # You'll need to provide either public_key or jwks_uri
        # For development, you can use RSAKeyPair.generate() to create keys
        # For production, use your OAuth provider's JWKS endpoint
        # jwks_uri="https://your-auth-provider.com/.well-known/jwks.json",
        # public_key="your-public-key-here",
        issuer="canvas-mcp",
        audience="canvas-assistant"
    )
    
    mcp = FastMCP(name="Canvas Assistant", auth=auth)

    # Register all tool providers
    # Each provider automatically registers its tools with the MCP instance
    CourseTools(mcp)
    ModuleTools(mcp)
    QuizTools(mcp)
    QuizQuestionTools(mcp)
    QuizQuestionGroupTools(mcp)
    PageTools(mcp)

    return mcp


if __name__ == "__main__":
    mcp = create_server()
    mcp.run(transport="http", host="0.0.0.0", port=8000)
