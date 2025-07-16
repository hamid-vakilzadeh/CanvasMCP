"""Canvas MCP Server - Organized with Tool Providers."""

from fastmcp import FastMCP

from tools.courses import CourseTools
from tools.modules import ModuleTools
from tools.quizzes import QuizTools, QuizQuestionTools, QuizQuestionGroupTools
from tools.pages import PageTools


def main():
    """Initialize the Canvas MCP server with organized tool providers."""
    mcp = FastMCP(name="Canvas Assistant")

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
    mcp = main()
    mcp.run()
