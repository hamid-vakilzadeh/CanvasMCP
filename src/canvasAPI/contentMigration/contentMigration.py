from typing import List, Dict, Union, Literal, Optional, TypedDict
from ..base import _make_request, _get_all_pages


class MigrationIssue(TypedDict, total=False):
    """Migration Issue Object"""
    
    id: int
    content_migration_url: str
    description: str
    workflow_state: Literal["active", "resolved"]
    fix_issue_html_url: Optional[str]
    issue_type: Literal["todo", "warning", "error"]
    error_report_html_url: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str


class ContentMigration(TypedDict, total=False):
    """Content Migration Object"""
    
    id: int
    migration_type: str
    migration_type_title: str
    migration_issues_url: str
    attachment: Optional[Dict]
    progress_url: Optional[str]
    user_id: int
    workflow_state: Literal[
        "pre_processing", "pre_processed", "running", 
        "waiting_for_select", "completed", "failed"
    ]
    started_at: Optional[str]
    finished_at: Optional[str]
    pre_attachment: Optional[Dict]


class Migrator(TypedDict):
    """Migrator Object"""
    
    type: str
    requires_file_upload: bool
    name: str
    required_settings: List[str]


# Migration Issues API

def list_migration_issues(
    base_url: str,
    access_token: str,
    context_type: Literal["accounts", "courses", "groups", "users"],
    context_id: Union[int, str],
    content_migration_id: Union[int, str],
    all_pages: bool = False,
) -> List[MigrationIssue]:
    """
    List migration issues for a content migration.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (accounts, courses, groups, users)
        context_id: Context ID
        content_migration_id: Content migration ID
        all_pages: If True, fetch all pages automatically

    Returns:
        List of MigrationIssue dictionaries
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_migrations/{content_migration_id}/migration_issues"
    
    if all_pages:
        return _get_all_pages(base_url, access_token, "GET", endpoint)
    else:
        response = _make_request(base_url, access_token, "GET", endpoint)
        return response.json()


def get_migration_issue(
    base_url: str,
    access_token: str,
    context_type: Literal["accounts", "courses", "groups", "users"],
    context_id: Union[int, str],
    content_migration_id: Union[int, str],
    issue_id: Union[int, str],
) -> MigrationIssue:
    """
    Get a single migration issue.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (accounts, courses, groups, users)
        context_id: Context ID
        content_migration_id: Content migration ID
        issue_id: Migration issue ID

    Returns:
        MigrationIssue dictionary
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_migrations/{content_migration_id}/migration_issues/{issue_id}"
    
    response = _make_request(base_url, access_token, "GET", endpoint)
    return response.json()


def update_migration_issue(
    base_url: str,
    access_token: str,
    context_type: Literal["accounts", "courses", "groups", "users"],
    context_id: Union[int, str],
    content_migration_id: Union[int, str],
    issue_id: Union[int, str],
    workflow_state: Literal["active", "resolved"],
) -> MigrationIssue:
    """
    Update the workflow state of a migration issue.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (accounts, courses, groups, users)
        context_id: Context ID
        content_migration_id: Content migration ID
        issue_id: Migration issue ID
        workflow_state: New workflow state

    Returns:
        Updated MigrationIssue dictionary
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_migrations/{content_migration_id}/migration_issues/{issue_id}"
    
    data = {"workflow_state": workflow_state}
    
    response = _make_request(base_url, access_token, "PUT", endpoint, data=data)
    return response.json()


# Content Migrations API

def list_content_migrations(
    base_url: str,
    access_token: str,
    context_type: Literal["accounts", "courses", "groups", "users"],
    context_id: Union[int, str],
    all_pages: bool = False,
) -> List[ContentMigration]:
    """
    List content migrations for a context.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (accounts, courses, groups, users)
        context_id: Context ID
        all_pages: If True, fetch all pages automatically

    Returns:
        List of ContentMigration dictionaries
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_migrations"
    
    if all_pages:
        return _get_all_pages(base_url, access_token, "GET", endpoint)
    else:
        response = _make_request(base_url, access_token, "GET", endpoint)
        return response.json()


def get_content_migration(
    base_url: str,
    access_token: str,
    context_type: Literal["accounts", "courses", "groups", "users"],
    context_id: Union[int, str],
    migration_id: Union[int, str],
) -> ContentMigration:
    """
    Get a single content migration.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (accounts, courses, groups, users)
        context_id: Context ID
        migration_id: Content migration ID

    Returns:
        ContentMigration dictionary
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_migrations/{migration_id}"
    
    response = _make_request(base_url, access_token, "GET", endpoint)
    return response.json()


def create_content_migration(
    base_url: str,
    access_token: str,
    context_type: Literal["accounts", "courses", "groups", "users"],
    context_id: Union[int, str],
    migration_type: str,
    pre_attachment: Optional[Dict] = None,
    settings: Optional[Dict] = None,
    date_shift_options: Optional[Dict] = None,
    selective_import: Optional[bool] = None,
    select: Optional[Dict] = None,
) -> ContentMigration:
    """
    Create a content migration.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (accounts, courses, groups, users)
        context_id: Context ID
        migration_type: Type of migration
        pre_attachment: File attachment information
        settings: Migration settings
        date_shift_options: Date shifting options
        selective_import: Whether to perform selective import
        select: Objects to copy (for course_copy_importer)

    Returns:
        Created ContentMigration dictionary
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_migrations"
    
    data = {"migration_type": migration_type}
    
    if pre_attachment:
        for key, value in pre_attachment.items():
            data[f"pre_attachment[{key}]"] = value
    
    if settings:
        for key, value in settings.items():
            data[f"settings[{key}]"] = value
    
    if date_shift_options:
        for key, value in date_shift_options.items():
            if key == "day_substitutions" and isinstance(value, dict):
                for day, sub_day in value.items():
                    data[f"date_shift_options[day_substitutions][{day}]"] = sub_day
            else:
                data[f"date_shift_options[{key}]"] = value
    
    if selective_import is not None:
        data["selective_import"] = selective_import
    
    if select:
        for key, value in select.items():
            if isinstance(value, list):
                data[f"select[{key}][]"] = value
            else:
                data[f"select[{key}]"] = value
    
    response = _make_request(base_url, access_token, "POST", endpoint, data=data)
    return response.json()


def update_content_migration(
    base_url: str,
    access_token: str,
    context_type: Literal["accounts", "courses", "groups", "users"],
    context_id: Union[int, str],
    migration_id: Union[int, str],
    pre_attachment: Optional[Dict] = None,
    settings: Optional[Dict] = None,
    date_shift_options: Optional[Dict] = None,
    selective_import: Optional[bool] = None,
    select: Optional[Dict] = None,
) -> ContentMigration:
    """
    Update a content migration.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (accounts, courses, groups, users)
        context_id: Context ID
        migration_id: Content migration ID
        pre_attachment: File attachment information
        settings: Migration settings
        date_shift_options: Date shifting options
        selective_import: Whether to perform selective import
        select: Objects to copy for selective import

    Returns:
        Updated ContentMigration dictionary
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_migrations/{migration_id}"
    
    data = {}
    
    if pre_attachment:
        for key, value in pre_attachment.items():
            data[f"pre_attachment[{key}]"] = value
    
    if settings:
        for key, value in settings.items():
            data[f"settings[{key}]"] = value
    
    if date_shift_options:
        for key, value in date_shift_options.items():
            if key == "day_substitutions" and isinstance(value, dict):
                for day, sub_day in value.items():
                    data[f"date_shift_options[day_substitutions][{day}]"] = sub_day
            else:
                data[f"date_shift_options[{key}]"] = value
    
    if selective_import is not None:
        data["selective_import"] = selective_import
    
    if select:
        for key, value in select.items():
            if isinstance(value, list):
                data[f"select[{key}][]"] = value
            else:
                data[f"select[{key}]"] = value
    
    response = _make_request(base_url, access_token, "PUT", endpoint, data=data)
    return response.json()


def list_migration_systems(
    base_url: str,
    access_token: str,
    context_type: Literal["accounts", "courses", "groups", "users"],
    context_id: Union[int, str],
) -> List[Migrator]:
    """
    List available migration systems.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (accounts, courses, groups, users)
        context_id: Context ID

    Returns:
        List of Migrator dictionaries
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_migrations/migrators"
    
    response = _make_request(base_url, access_token, "GET", endpoint)
    return response.json()


def list_items_for_selective_import(
    base_url: str,
    access_token: str,
    context_type: Literal["accounts", "courses", "groups", "users"],
    context_id: Union[int, str],
    migration_id: Union[int, str],
    type: Optional[Literal[
        "context_modules", "assignments", "quizzes", "assessment_question_banks",
        "discussion_topics", "wiki_pages", "context_external_tools", "tool_profiles",
        "announcements", "calendar_events", "rubrics", "groups", 
        "learning_outcomes", "attachments"
    ]] = None,
) -> List[Dict]:
    """
    List items available for selective import in a tree structure.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (accounts, courses, groups, users)
        context_id: Context ID
        migration_id: Content migration ID
        type: Type of content to enumerate

    Returns:
        List of content items available for selective import
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_migrations/{migration_id}/selective_data"
    
    params = {}
    if type:
        params["type"] = type
    
    response = _make_request(base_url, access_token, "GET", endpoint, params=params)
    return response.json()


def get_asset_id_mapping(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    migration_id: Union[int, str],
) -> Dict[str, Dict[str, str]]:
    """
    Get asset ID mapping for a course content migration.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        migration_id: Content migration ID

    Returns:
        Dictionary mapping asset types to ID mappings

    Note:
        Only available for courses, not other contexts
    """
    endpoint = f"/api/v1/courses/{course_id}/content_migrations/{migration_id}/asset_id_mapping"
    
    response = _make_request(base_url, access_token, "GET", endpoint)
    return response.json()


# Specialized Course Copy Functions

def copy_course_content(
    base_url: str,
    access_token: str,
    source_course_id: Union[int, str],
    destination_course_id: Union[int, str],
    shift_dates: bool = False,
    old_start_date: Optional[str] = None,
    new_start_date: Optional[str] = None,
    old_end_date: Optional[str] = None,
    new_end_date: Optional[str] = None,
    day_substitutions: Optional[Dict[int, int]] = None,
    remove_dates: bool = False,
    selective_items: Optional[Dict[str, List[Union[int, str]]]] = None,
    import_blueprint_settings: bool = False,
    move_to_assignment_group_id: Optional[int] = None,
    insert_into_module_id: Optional[int] = None,
    insert_into_module_type: Optional[Literal["assignment", "discussion_topic", "file", "page", "quiz"]] = None,
    insert_into_module_position: Optional[int] = None,
) -> ContentMigration:
    """
    Copy content from one course to another using course_copy_importer.
    
    This is a specialized wrapper around create_content_migration specifically 
    for copying content between courses.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        source_course_id: ID of the source course to copy from
        destination_course_id: ID of the destination course to copy to
        shift_dates: Whether to shift dates in the copied content
        old_start_date: Original start date (YYYY-MM-DD format)
        new_start_date: New start date (YYYY-MM-DD format)
        old_end_date: Original end date (YYYY-MM-DD format)  
        new_end_date: New end date (YYYY-MM-DD format)
        day_substitutions: Map of day numbers (0=Sunday, 1=Monday, etc.) to substitute
        remove_dates: Whether to remove all dates instead of shifting
        selective_items: Dictionary of content types and their IDs to copy selectively
        import_blueprint_settings: Whether to import blueprint course settings
        move_to_assignment_group_id: Assignment group to move all assignments to
        insert_into_module_id: Module to add imported items to
        insert_into_module_type: Type of items to add to module (if specified)
        insert_into_module_position: Position in module to insert items

    Returns:
        ContentMigration object representing the copy operation

    Example:
        # Simple course copy
        migration = copy_course_content(
            base_url, token, source_course_id=123, destination_course_id=456
        )
        
        # Course copy with date shifting
        migration = copy_course_content(
            base_url, token, 
            source_course_id=123, 
            destination_course_id=456,
            shift_dates=True,
            old_start_date="2023-01-01",
            new_start_date="2024-01-01"
        )
        
        # Selective course copy (assignments and quizzes only)
        migration = copy_course_content(
            base_url, token,
            source_course_id=123,
            destination_course_id=456,
            selective_items={
                "assignments": [1, 2, 3],
                "quizzes": [4, 5]
            }
        )
    """
    settings = {"source_course_id": str(source_course_id)}
    
    # Add optional settings
    if import_blueprint_settings:
        settings["import_blueprint_settings"] = True
    
    if move_to_assignment_group_id:
        settings["move_to_assignment_group_id"] = move_to_assignment_group_id
    
    if insert_into_module_id:
        settings["insert_into_module_id"] = insert_into_module_id
        
        if insert_into_module_type:
            settings["insert_into_module_type"] = insert_into_module_type
            
        if insert_into_module_position:
            settings["insert_into_module_position"] = insert_into_module_position
    
    # Handle date shifting options
    date_shift_options = None
    if shift_dates or remove_dates:
        date_shift_options = {}
        
        if shift_dates:
            date_shift_options["shift_dates"] = True
            if old_start_date:
                date_shift_options["old_start_date"] = old_start_date
            if new_start_date:
                date_shift_options["new_start_date"] = new_start_date
            if old_end_date:
                date_shift_options["old_end_date"] = old_end_date
            if new_end_date:
                date_shift_options["new_end_date"] = new_end_date
            if day_substitutions:
                date_shift_options["day_substitutions"] = day_substitutions
        
        if remove_dates:
            date_shift_options["remove_dates"] = True
    
    return create_content_migration(
        base_url=base_url,
        access_token=access_token,
        context_type="courses",
        context_id=destination_course_id,
        migration_type="course_copy_importer",
        settings=settings,
        date_shift_options=date_shift_options,
        select=selective_items
    )


def selective_course_copy(
    base_url: str,
    access_token: str,
    source_course_id: Union[int, str],
    destination_course_id: Union[int, str],
    content_types: Optional[List[Literal[
        "assignments", "quizzes", "pages", "modules", "files", 
        "discussion_topics", "announcements", "calendar_events", 
        "rubrics", "assessment_question_banks"
    ]]] = None,
    interactive_selection: bool = True,
    poll_interval: int = 2,
    max_wait_time: int = 300,
) -> Dict:
    """
    Copy specific content from one course to another with interactive selection.
    
    This function handles the complete workflow for selective content migration:
    1. Initiates selective import migration
    2. Waits for content analysis
    3. Retrieves available content for selection
    4. Allows filtering by content types
    5. Executes the migration with selected items
    
    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        source_course_id: ID of the source course to copy from
        destination_course_id: ID of the destination course to copy to
        content_types: List of content types to include (None for all types)
        interactive_selection: If True, return selection data for user interaction
        poll_interval: Seconds between status checks
        max_wait_time: Maximum seconds to wait for content analysis
        
    Returns:
        Dictionary containing:
        - migration_id: The migration ID
        - status: Current migration status
        - available_content: Available items for selection (if interactive_selection=True)
        - selected_items: Items selected for migration (if selection was made)
        
    Example:
        # Get available content for user selection
        result = selective_course_copy(
            base_url, token, 
            source_course_id=123,
            destination_course_id=456,
            content_types=["assignments", "quizzes"]
        )
        
        # Process the available content and make selections
        migration_id = result["migration_id"]
        available_content = result["available_content"]
        
        # Then execute selection (separate call)
        execute_selective_migration(base_url, token, destination_course_id, 
                                  migration_id, selected_properties)
    """
    import time
    
    # Step 1: Create selective import migration
    migration = create_content_migration(
        base_url=base_url,
        access_token=access_token,
        context_type="courses",
        context_id=destination_course_id,
        migration_type="course_copy_importer",
        settings={"source_course_id": str(source_course_id)},
        selective_import=True
    )
    
    migration_id = migration["id"]
    
    # Step 2: Wait for migration to reach waiting_for_select state
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        current_status = get_content_migration(
            base_url, access_token, "courses", destination_course_id, migration_id
        )
        
        workflow_state = current_status["workflow_state"]
        
        if workflow_state == "waiting_for_select":
            break
        elif workflow_state in ["failed", "completed"]:
            return {
                "migration_id": migration_id,
                "status": workflow_state,
                "error": "Migration completed unexpectedly or failed",
                "migration_details": current_status
            }
        
        time.sleep(poll_interval)
    else:
        return {
            "migration_id": migration_id,
            "status": "timeout",
            "error": f"Migration did not reach waiting_for_select state within {max_wait_time} seconds"
        }
    
    # Step 3: Get available content
    available_content = {}
    
    # Get top-level content structure (for reference if needed)
    # top_level = list_items_for_selective_import(
    #     base_url, access_token, "courses", destination_course_id, migration_id
    # )
    
    # Filter by content types if specified
    content_type_mapping = {
        "assignments": "assignments",
        "quizzes": "quizzes", 
        "pages": "wiki_pages",
        "modules": "context_modules",
        "files": "attachments",
        "discussion_topics": "discussion_topics",
        "announcements": "announcements", 
        "calendar_events": "calendar_events",
        "rubrics": "rubrics",
        "assessment_question_banks": "assessment_question_banks"
    }
    
    target_types = content_types if content_types else list(content_type_mapping.keys())
    
    for content_type in target_types:
        api_type = content_type_mapping.get(content_type, content_type)
        
        try:
            content_items = list_items_for_selective_import(
                base_url, access_token, "courses", destination_course_id,
                migration_id, type=api_type
            )
            available_content[content_type] = content_items
        except Exception as e:
            available_content[content_type] = {"error": str(e)}
    
    result = {
        "migration_id": migration_id,
        "status": "waiting_for_select",
        "available_content": available_content,
        "source_course_id": source_course_id,
        "destination_course_id": destination_course_id
    }
    
    if not interactive_selection:
        # Auto-select all available items
        selected_properties = _extract_all_properties(available_content)
        
        # Execute the migration
        update_content_migration(
            base_url, access_token, "courses", destination_course_id,
            migration_id, select=selected_properties
        )
        
        result["status"] = "migration_started"
        result["selected_items"] = selected_properties
    
    return result


def execute_selective_migration(
    base_url: str,
    access_token: str,
    destination_course_id: Union[int, str],
    migration_id: Union[int, str],
    selected_properties: Dict[str, int],
) -> ContentMigration:
    """
    Execute a selective migration with user-selected items.
    
    This function is used after selective_course_copy() to actually perform
    the migration with specific selected items.
    
    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        destination_course_id: Destination course ID
        migration_id: Migration ID from selective_course_copy()
        selected_properties: Dictionary of property keys to 1 (selected items)
        
    Returns:
        Updated ContentMigration object
        
    Example:
        # Properties extracted from available_content
        selected_properties = {
            "copy[assignments][id_i123abc]": 1,
            "copy[quizzes][id_i456def]": 1
        }
        
        migration = execute_selective_migration(
            base_url, token, course_id, migration_id, selected_properties
        )
    """
    return update_content_migration(
        base_url, access_token, "courses", destination_course_id,
        migration_id, select=selected_properties
    )


def _extract_all_properties(available_content: Dict) -> Dict[str, int]:
    """
    Helper function to extract all property keys from available content.
    Used for auto-selecting all items when interactive_selection=False.
    """
    properties = {}
    
    for _, items in available_content.items():
        if isinstance(items, dict) and "error" in items:
            continue
            
        for item in items:
            if "property" in item:
                properties[item["property"]] = 1
            
            # Handle sub_items
            if "sub_items" in item:
                for sub_item in item["sub_items"]:
                    if "property" in sub_item:
                        properties[sub_item["property"]] = 1
    
    return properties


def get_migration_progress(
    base_url: str,
    access_token: str,
    destination_course_id: Union[int, str],
    migration_id: Union[int, str],
) -> Dict:
    """
    Get the current status and progress of a content migration.
    
    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        destination_course_id: Destination course ID
        migration_id: Migration ID
        
    Returns:
        Dictionary with migration status and progress information
    """
    migration = get_content_migration(
        base_url, access_token, "courses", destination_course_id, migration_id
    )
    
    result = {
        "migration_id": migration_id,
        "workflow_state": migration["workflow_state"],
        "started_at": migration.get("started_at"),
        "finished_at": migration.get("finished_at"),
        "progress_url": migration.get("progress_url")
    }
    
    # Get progress details if available
    if migration.get("progress_url"):
        try:
            # Note: This would require a separate progress API call
            # For now, just include the URL
            result["progress_available"] = True
        except Exception:
            result["progress_available"] = False
    
    return result