#!/usr/bin/env python3
"""
Simple MCP test server to debug Claude Desktop connection.
"""

from fastmcp import FastMCP

def main():
    mcp = FastMCP(name="Test MCP Server")

    @mcp.tool()
    def test_tool(message: str = "Hello") -> str:
        """A simple test tool."""
        return f"Test response: {message}"

    return mcp

if __name__ == "__main__":
    mcp = main()
    mcp.run(transport="http", host="127.0.0.1", port=8002)