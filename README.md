# Canvas MCP Tools Organization

This directory contains the organized tool providers for the Canvas MCP server. The tools are grouped by functionality and implemented using the recommended FastMCP patterns.

## Architecture

### Base Classes

- `base.py` - Contains the `ToolProvider` abstract base class and utility functions
- `validate_and_convert_params()` - Shared parameter validation and conversion logic

### Tool Providers

Each tool provider is a class that inherits from `ToolProvider` and automatically registers its tools with the MCP instance upon instantiation.

#### 1. CourseTools (`courses.py`)

- **Purpose**: Manages Canvas courses
- **Tools**:
  - `list_courses()` - List all courses where user is a teacher

#### 2. ModuleTools (`modules.py`)

- **Purpose**: Manages Canvas modules and module items
- **Tools**:
  - `create_module()` - Create a new module
  - `list_modules()` - List modules in a course
  - `show_module()` - Get information about a single module
  - `update_module()` - Update an existing module
  - `delete_module()` - Delete a module
  - `relock_module()` - Re-lock module progressions
  - `list_module_items()` - List items in a module
  - `show_module_item()` - Get information about a single module item
  - `create_module_item()` - Create a new module item
  - `update_module_item()` - Update an existing module item
  - `delete_module_item()` - Delete a module item

#### 3. QuizTools (`quizzes.py`)

- **Purpose**: Manages Canvas quizzes
- **Tools**:
  - `list_quizzes()` - List quizzes in a course
  - `get_quiz()` - Get a single quiz
  - `create_quiz()` - Create a new quiz
  - `update_quiz()` - Update an existing quiz
  - `delete_quiz()` - Delete a quiz
  - `validate_quiz_access_code()` - Validate quiz access code

#### 4. QuizQuestionTools (`quizzes.py`)

- **Purpose**: Manages Canvas quiz questions
- **Tools**:
  - `list_quiz_questions()` - List questions in a quiz
  - `get_quiz_question()` - Get a single quiz question
  - `create_quiz_question()` - Create a new quiz question
  - `update_quiz_question()` - Update an existing quiz question
  - `delete_quiz_question()` - Delete a quiz question

#### 5. PageTools (`pages.py`)

- **Purpose**: Manages Canvas wiki pages
- **Tools**:
  - `show_front_page()` - Retrieve the content of the front page
  - `duplicate_page()` - Duplicate a wiki page
  - `update_front_page()` - Update the title or contents of the front page
  - `list_pages()` - List wiki pages associated with a course or group
  - `create_page()` - Create a new wiki page
  - `show_page()` - Retrieve the content of a wiki page
  - `update_page()` - Update the title or contents of a wiki page
  - `delete_page()` - Delete a wiki page
  - `list_revisions()` - List revisions of a page
  - `show_revision()` - Retrieve metadata and content of a page revision
  - `revert_to_revision()` - Revert a page to a prior revision

## Usage

### Main Entry Point

```python
from fastmcp import FastMCP
from tools.courses import CourseTools
from tools.modules import ModuleTools
from tools.quizzes import QuizTools, QuizQuestionTools
from tools.pages import PageTools

# Create MCP instance
mcp = FastMCP(name="Canvas Assistant")

# Register tool providers (automatically registers all tools)
CourseTools(mcp)
ModuleTools(mcp)
QuizTools(mcp)
QuizQuestionTools(mcp)
PageTools(mcp)

# Run the server
mcp.run()
```

### Adding New Tool Providers

1. Create a new file in the `tools/` directory
2. Inherit from `ToolProvider`
3. Implement the `_register_tools()` method
4. Add tool methods as instance methods
5. Register the provider in the main entry point

Example:

```python
from .base import ToolProvider
from canvasAPI.some_module import some_api

class NewTools(ToolProvider):
    def _register_tools(self):
        self.mcp.tool(self.my_tool, tags={"new"})

    async def my_tool(self, param: str) -> dict:
        \"\"\"Description of what this tool does.\"\"\"
        params = self._validate_params(param=param)
        return some_api.do_something(**params)
```

## Benefits

1. **Better Organization**: Tools are grouped by functionality
2. **Maintainability**: Each domain has its own file
3. **Extensibility**: Easy to add new tool providers
4. **Consistency**: All providers follow the same pattern
5. **Reusability**: Common utilities are shared via base class
6. **FastMCP Compliance**: Follows recommended patterns for method registration

## Migration from Original Structure

The original `index.py` had all tools defined as individual functions. The new structure:

1. Groups related tools into classes
2. Uses instance methods that are properly registered with FastMCP
3. Shares common validation logic
4. Makes it easier to add new tools in the future

## Testing

Each tool provider can be tested independently:

```python
from fastmcp import FastMCP
from tools.courses import CourseTools

# Test individual provider
mcp = FastMCP(name="Test")
course_tools = CourseTools(mcp)
# Tools are now registered with mcp
```
