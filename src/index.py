"""Canvas MCP Server - Organized with Tool Providers."""

import argparse
from fastmcp import FastMCP

from tools.courses import CourseTools
from tools.modules import ModuleTools
from tools.quizzes import QuizTools, QuizQuestionTools, QuizQuestionGroupTools
from tools.pages import PageTools


def main():
    """Initialize the Canvas MCP server with organized tool providers."""
    parser = argparse.ArgumentParser(description="Canvas MCP Server")
    parser.add_argument("--canvas-url", required=True, help="Canvas base URL")
    parser.add_argument("--access-token", required=True, help="Canvas API access token")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")

    args = parser.parse_args()

    mcp = FastMCP(name="Canvas Assistant")

    # Store credentials globally for API classes to access
    import canvasAPI.base

    canvasAPI.base.access_token = args.access_token
    canvasAPI.base.url = args.canvas_url

    # Register all tool providers
    # Each provider automatically registers its tools with the MCP instance
    CourseTools(mcp)
    ModuleTools(mcp)
    QuizTools(mcp)
    QuizQuestionTools(mcp)
    QuizQuestionGroupTools(mcp)
    PageTools(mcp)

    return mcp, args


if __name__ == "__main__":
    mcp, args = main()
    mcp.run(transport="http", host=args.host, port=args.port)
