from fastmcp import FastMCP
from tools.courses import CourseTools
from tools.modules import ModuleTools
from tools.pages import PageTools

mcp = FastMCP("Canvas-MCP", stateless_http=True)


CourseTools(mcp)
ModuleTools(mcp)
PageTools(mcp)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=3000, path="/mcp")
