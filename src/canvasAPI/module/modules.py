from typing import List, Dict, Union, Optional, TypedDict, Literal
from datetime import datetime
from ..base import _make_request, _get_all_pages


class CompletionRequirement(TypedDict, total=False):
    """Completion requirement for module items."""

    type: Literal[
        "must_view",
        "must_contribute",
        "must_submit",
        "min_score",
        "min_percentage",
        "must_mark_done",
    ]
    min_score: Optional[int]
    min_percentage: Optional[int]
    completed: Optional[bool]


class ModuleOverride(TypedDict, total=False):
    """Module assignment override object."""

    id: Optional[int]
    title: Optional[str]
    student_ids: Optional[List[int]]
    course_section_id: Optional[int]
    group_id: Optional[int]


def list_modules(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    include: Optional[List[Literal["items", "content_details"]]] = None,
    search_term: Optional[str] = None,
    student_id: Optional[Union[int, str]] = None,
    all_pages: bool = False,
) -> List[Dict]:
    """
    List modules in a course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        include: Additional data to include
        search_term: Partial name of modules to match
        student_id: Returns module completion information for this student
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of Module dictionaries

    Raises:
        ValueError: If invalid include values are provided
    """
    # Validate include values
    if include is not None:
        valid_includes = {"items", "content_details"}
        invalid_includes = [i for i in include if i not in valid_includes]
        if invalid_includes:
            raise ValueError(
                f"Invalid include values: {', '.join(invalid_includes)}. "
                f"Allowed values: {', '.join(sorted(valid_includes))}"
            )

        # Validate include dependencies
        if "content_details" in include and "items" not in include:
            raise ValueError("'content_details' requires 'items' to be included")

    params = {}

    if include:
        params["include[]"] = include
    if search_term:
        params["search_term"] = search_term
    if student_id is not None:
        params["student_id"] = student_id

    if all_pages:
        return _get_all_pages(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/modules",
            params=params,
        )
    else:
        response = _make_request(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/modules",
            params=params,
        )
        return response.json()


def show_module(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    include: Optional[List[Literal["items", "content_details"]]] = None,
    student_id: Optional[Union[int, str]] = None,
) -> Dict:
    """
    Get information about a single module.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        include: Additional data to include
        student_id: Returns module completion information for this student

    Returns:
        Module dictionary

    Raises:
        ValueError: If invalid include values are provided
    """
    # Validate include values
    if include is not None:
        valid_includes = {"items", "content_details"}
        invalid_includes = [i for i in include if i not in valid_includes]
        if invalid_includes:
            raise ValueError(
                f"Invalid include values: {', '.join(invalid_includes)}. "
                f"Allowed values: {', '.join(sorted(valid_includes))}"
            )

        # Validate include dependencies
        if "content_details" in include and "items" not in include:
            raise ValueError("'content_details' requires 'items' to be included")

    params = {}

    if include:
        params["include[]"] = include
    if student_id is not None:
        params["student_id"] = student_id

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/modules/{module_id}",
        params=params,
    )
    return response.json()


def create_module(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    name: str,
    unlock_at: Optional[datetime] = None,
    position: Optional[int] = None,
    require_sequential_progress: Optional[bool] = None,
    prerequisite_module_ids: Optional[List[Union[int, str]]] = None,
    publish_final_grade: Optional[bool] = None,
) -> Dict:
    """
    Create a new module.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        name: Module name
        unlock_at: Date the module will unlock
        position: Position in course (1-based)
        require_sequential_progress: Whether items must be unlocked in order
        prerequisite_module_ids: IDs of modules that must be completed first
        publish_final_grade: Whether to publish final grade upon completion

    Returns:
        Created Module dictionary

    Raises:
        ValueError: If name is empty or position is invalid
    """
    if not name or not name.strip():
        raise ValueError("Module name cannot be empty")

    if position is not None and position < 1:
        raise ValueError("Position must be 1 or greater")

    data = {"module[name]": name.strip()}

    if unlock_at is not None:
        data["module[unlock_at]"] = unlock_at.isoformat()
    if position is not None:
        data["module[position]"] = position
    if require_sequential_progress is not None:
        data["module[require_sequential_progress]"] = require_sequential_progress
    if prerequisite_module_ids:
        data["module[prerequisite_module_ids][]"] = prerequisite_module_ids
    if publish_final_grade is not None:
        data["module[publish_final_grade]"] = publish_final_grade

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/modules",
        data=data,
    )
    return response.json()


def update_module(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    name: Optional[str] = None,
    unlock_at: Optional[datetime] = None,
    position: Optional[int] = None,
    require_sequential_progress: Optional[bool] = None,
    prerequisite_module_ids: Optional[List[Union[int, str]]] = None,
    publish_final_grade: Optional[bool] = None,
    published: Optional[bool] = None,
) -> Dict:
    """
    Update an existing module.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        name: Module name
        unlock_at: Date the module will unlock
        position: Position in course (1-based)
        require_sequential_progress: Whether items must be unlocked in order
        prerequisite_module_ids: IDs of modules that must be completed first
        publish_final_grade: Whether to publish final grade upon completion
        published: Whether module is published and visible to students

    Returns:
        Updated Module dictionary

    Raises:
        ValueError: If name is empty or position is invalid
    """
    if name is not None and (not name or not name.strip()):
        raise ValueError("Module name cannot be empty")

    if position is not None and position < 1:
        raise ValueError("Position must be 1 or greater")

    data = {}

    if name is not None:
        data["module[name]"] = name.strip()
    if unlock_at is not None:
        data["module[unlock_at]"] = unlock_at.isoformat()
    if position is not None:
        data["module[position]"] = position
    if require_sequential_progress is not None:
        data["module[require_sequential_progress]"] = require_sequential_progress
    if prerequisite_module_ids is not None:
        data["module[prerequisite_module_ids][]"] = prerequisite_module_ids
    if publish_final_grade is not None:
        data["module[publish_final_grade]"] = publish_final_grade
    if published is not None:
        data["module[published]"] = published

    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/courses/{course_id}/modules/{module_id}",
        data=data,
    )
    return response.json()


def delete_module(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
) -> Dict:
    """
    Delete a module.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID

    Returns:
        Deleted Module dictionary
    """
    response = _make_request(
        base_url,
        access_token,
        "DELETE",
        f"/api/v1/courses/{course_id}/modules/{module_id}",
    )
    return response.json()


def relock_module(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
) -> Dict:
    """
    Re-lock module progressions.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID

    Returns:
        Module dictionary

    Note:
        Resets module progressions to their default locked state and recalculates
        them based on current requirements.
    """
    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/courses/{course_id}/modules/{module_id}/relock",
    )
    return response.json()


def list_module_items(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    include: Optional[List[Literal["content_details"]]] = None,
    search_term: Optional[str] = None,
    student_id: Optional[Union[int, str]] = None,
    all_pages: bool = False,
) -> List[Dict]:
    """
    List items in a module.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        include: Additional data to include
        search_term: Partial title of items to match
        student_id: Returns module completion information for this student
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of ModuleItem dictionaries

    Raises:
        ValueError: If invalid include values are provided
    """
    # Validate include values
    if include is not None:
        valid_includes = {"content_details"}
        invalid_includes = [i for i in include if i not in valid_includes]
        if invalid_includes:
            raise ValueError(
                f"Invalid include values: {', '.join(invalid_includes)}. "
                f"Allowed values: {', '.join(sorted(valid_includes))}"
            )

    params = {}

    if include:
        params["include[]"] = include
    if search_term:
        params["search_term"] = search_term
    if student_id is not None:
        params["student_id"] = student_id

    if all_pages:
        return _get_all_pages(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/modules/{module_id}/items",
            params=params,
        )
    else:
        response = _make_request(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/modules/{module_id}/items",
            params=params,
        )
        return response.json()


def show_module_item(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    item_id: Union[int, str],
    include: Optional[List[Literal["content_details"]]] = None,
    student_id: Optional[Union[int, str]] = None,
) -> Dict:
    """
    Get information about a single module item.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        item_id: Module item ID
        include: Additional data to include
        student_id: Returns module completion information for this student

    Returns:
        ModuleItem dictionary

    Raises:
        ValueError: If invalid include values are provided
    """
    # Validate include values
    if include is not None:
        valid_includes = {"content_details"}
        invalid_includes = [i for i in include if i not in valid_includes]
        if invalid_includes:
            raise ValueError(
                f"Invalid include values: {', '.join(invalid_includes)}. "
                f"Allowed values: {', '.join(sorted(valid_includes))}"
            )

    params = {}

    if include:
        params["include[]"] = include
    if student_id is not None:
        params["student_id"] = student_id

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/modules/{module_id}/items/{item_id}",
        params=params,
    )
    return response.json()


def create_module_item(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    item_type: Literal[
        "File",
        "Page",
        "Discussion",
        "Assignment",
        "Quiz",
        "SubHeader",
        "ExternalUrl",
        "ExternalTool",
    ],
    title: Optional[str] = None,
    content_id: Optional[Union[int, str]] = None,
    position: Optional[int] = None,
    indent: Optional[int] = None,
    page_url: Optional[str] = None,
    external_url: Optional[str] = None,
    new_tab: Optional[bool] = None,
    completion_requirement_type: Optional[
        Literal["must_view", "must_contribute", "must_submit", "must_mark_done"]
    ] = None,
    completion_requirement_min_score: Optional[int] = None,
    iframe_width: Optional[int] = None,
    iframe_height: Optional[int] = None,
) -> Dict:
    """
    Create a new module item.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        item_type: Type of content linked to the item
        title: Name of the module item
        content_id: ID of content to link (required except for ExternalUrl, Page, SubHeader)
        position: Position in module (1-based)
        indent: 0-based indent level
        page_url: Wiki page URL suffix (required for Page type)
        external_url: External URL (required for ExternalUrl and ExternalTool)
        new_tab: Whether external tool opens in new tab (ExternalTool only)
        completion_requirement_type: Completion requirement type
        completion_requirement_min_score: Min score for completion (min_score type only)
        iframe_width: ExternalTool launch width
        iframe_height: ExternalTool launch height

    Returns:
        Created ModuleItem dictionary

    Raises:
        ValueError: If validation fails for item type requirements
    """
    # Validate item type
    valid_types = {
        "File",
        "Page",
        "Discussion",
        "Assignment",
        "Quiz",
        "SubHeader",
        "ExternalUrl",
        "ExternalTool",
    }
    if item_type not in valid_types:
        raise ValueError(
            f"Invalid item_type '{item_type}'. "
            f"Allowed values: {', '.join(sorted(valid_types))}"
        )

    # Validate required fields based on type
    if item_type == "Page" and not page_url:
        raise ValueError("page_url is required for Page type")

    if item_type in ["ExternalUrl", "ExternalTool"] and not external_url:
        raise ValueError(f"external_url is required for {item_type} type")

    if item_type not in ["ExternalUrl", "Page", "SubHeader"] and content_id is None:
        raise ValueError(f"content_id is required for {item_type} type")

    # Validate completion requirement
    if completion_requirement_type is not None:
        valid_completion_types = {
            "must_view",
            "must_contribute",
            "must_submit",
            "must_mark_done",
        }
        if completion_requirement_type not in valid_completion_types:
            raise ValueError(
                f"Invalid completion_requirement_type '{completion_requirement_type}'. "
                f"Allowed values: {', '.join(sorted(valid_completion_types))}"
            )

        # Validate type applicability
        type_requirements = {
            "must_contribute": {"Assignment", "Discussion", "Page"},
            "must_submit": {"Assignment", "Quiz"},
            "must_mark_done": {"Assignment", "Page"},
        }

        if completion_requirement_type in type_requirements:
            if item_type not in type_requirements[completion_requirement_type]:
                raise ValueError(
                    f"Completion requirement '{completion_requirement_type}' "
                    f"does not apply to item type '{item_type}'"
                )

    # Validate position and indent
    if position is not None and position < 1:
        raise ValueError("Position must be 1 or greater")

    if indent is not None and indent < 0:
        raise ValueError("Indent must be 0 or greater")

    data = {"module_item[type]": item_type}

    if title:
        data["module_item[title]"] = title
    if content_id is not None:
        data["module_item[content_id]"] = content_id
    if position is not None:
        data["module_item[position]"] = position
    if indent is not None:
        data["module_item[indent]"] = indent
    if page_url:
        data["module_item[page_url]"] = page_url
    if external_url:
        data["module_item[external_url]"] = external_url
    if new_tab is not None:
        data["module_item[new_tab]"] = new_tab
    if completion_requirement_type:
        data["module_item[completion_requirement][type]"] = completion_requirement_type
    if completion_requirement_min_score is not None:
        data["module_item[completion_requirement][min_score]"] = (
            completion_requirement_min_score
        )
    if iframe_width is not None:
        data["module_item[iframe][width]"] = iframe_width
    if iframe_height is not None:
        data["module_item[iframe][height]"] = iframe_height

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/modules/{module_id}/items",
        data=data,
    )
    return response.json()


def update_module_item(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    item_id: Union[int, str],
    title: Optional[str] = None,
    position: Optional[int] = None,
    indent: Optional[int] = None,
    external_url: Optional[str] = None,
    new_tab: Optional[bool] = None,
    completion_requirement_type: Optional[
        Literal["must_view", "must_contribute", "must_submit", "must_mark_done"]
    ] = None,
    completion_requirement_min_score: Optional[int] = None,
    published: Optional[bool] = None,
    target_module_id: Optional[Union[int, str]] = None,
) -> Dict:
    """
    Update an existing module item.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        item_id: Module item ID
        title: Name of the module item
        position: Position in module (1-based)
        indent: 0-based indent level
        external_url: External URL (ExternalUrl type only)
        new_tab: Whether external tool opens in new tab (ExternalTool only)
        completion_requirement_type: Completion requirement type
        completion_requirement_min_score: Min score for completion (min_score type only)
        published: Whether item is published and visible to students
        target_module_id: Move item to another module

    Returns:
        Updated ModuleItem dictionary

    Raises:
        ValueError: If validation fails
    """
    # Validate completion requirement
    if completion_requirement_type is not None:
        valid_completion_types = {
            "must_view",
            "must_contribute",
            "must_submit",
            "must_mark_done",
        }
        if completion_requirement_type not in valid_completion_types:
            raise ValueError(
                f"Invalid completion_requirement_type '{completion_requirement_type}'. "
                f"Allowed values: {', '.join(sorted(valid_completion_types))}"
            )

    # Validate position and indent
    if position is not None and position < 1:
        raise ValueError("Position must be 1 or greater")

    if indent is not None and indent < 0:
        raise ValueError("Indent must be 0 or greater")

    data = {}

    if title is not None:
        data["module_item[title]"] = title
    if position is not None:
        data["module_item[position]"] = position
    if indent is not None:
        data["module_item[indent]"] = indent
    if external_url is not None:
        data["module_item[external_url]"] = external_url
    if new_tab is not None:
        data["module_item[new_tab]"] = new_tab
    if completion_requirement_type is not None:
        data["module_item[completion_requirement][type]"] = completion_requirement_type
    if completion_requirement_min_score is not None:
        data["module_item[completion_requirement][min_score]"] = (
            completion_requirement_min_score
        )
    if published is not None:
        data["module_item[published]"] = published
    if target_module_id is not None:
        data["module_item[module_id]"] = target_module_id

    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/courses/{course_id}/modules/{module_id}/items/{item_id}",
        data=data,
    )
    return response.json()


def select_mastery_path(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    item_id: Union[int, str],
    assignment_set_id: str,
    student_id: Optional[Union[int, str]] = None,
) -> Dict:
    """
    Select a mastery path for a module item.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        item_id: Module item ID
        assignment_set_id: Assignment set chosen from mastery_paths
        student_id: Student to apply selection to (defaults to current user)

    Returns:
        Compound document with assignments and related module items

    Note:
        Requires Mastery Paths feature to be enabled.
    """
    data = {"assignment_set_id": assignment_set_id}

    if student_id is not None:
        data["student_id"] = student_id

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/modules/{module_id}/items/{item_id}/select_mastery_path",
        data=data,
    )
    return response.json()


def delete_module_item(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    item_id: Union[int, str],
) -> Dict:
    """
    Delete a module item.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        item_id: Module item ID

    Returns:
        Deleted ModuleItem dictionary
    """
    response = _make_request(
        base_url,
        access_token,
        "DELETE",
        f"/api/v1/courses/{course_id}/modules/{module_id}/items/{item_id}",
    )
    return response.json()


def mark_module_item_done(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    item_id: Union[int, str],
    done: bool = True,
) -> Dict:
    """
    Mark a module item as done/not done.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        item_id: Module item ID
        done: Whether to mark as done (True) or not done (False)

    Returns:
        Response dictionary
    """
    method = "PUT" if done else "DELETE"
    response = _make_request(
        base_url,
        access_token,
        method,
        f"/api/v1/courses/{course_id}/modules/{module_id}/items/{item_id}/done",
    )
    return response.json()


def get_module_item_sequence(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    asset_type: Literal[
        "ModuleItem",
        "File",
        "Page",
        "Discussion",
        "Assignment",
        "Quiz",
        "ExternalTool",
    ],
    asset_id: Union[int, str],
) -> Dict:
    """
    Get module item sequence information.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        asset_type: Type of asset to find sequence for
        asset_id: ID of the asset (or URL for Page type)

    Returns:
        ModuleItemSequence dictionary with previous, current, and next items

    Raises:
        ValueError: If invalid asset_type is provided
    """
    # Validate asset_type
    valid_asset_types = {
        "ModuleItem",
        "File",
        "Page",
        "Discussion",
        "Assignment",
        "Quiz",
        "ExternalTool",
    }
    if asset_type not in valid_asset_types:
        raise ValueError(
            f"Invalid asset_type '{asset_type}'. "
            f"Allowed values: {', '.join(sorted(valid_asset_types))}"
        )

    params = {
        "asset_type": asset_type,
        "asset_id": asset_id,
    }

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/module_item_sequence",
        params=params,
    )
    return response.json()


def mark_module_item_read(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    item_id: Union[int, str],
) -> Dict:
    """
    Mark a module item as read to fulfill "must view" requirement.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        item_id: Module item ID

    Returns:
        Response dictionary

    Note:
        Generally not necessary to call explicitly, but provided for applications
        that need to access external content directly.
    """
    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/modules/{module_id}/items/{item_id}/mark_read",
    )
    return response.json()


def list_module_overrides(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    all_pages: bool = False,
) -> List[Dict]:
    """
    List assignment overrides that apply to a module.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of ModuleAssignmentOverride dictionaries
    """
    if all_pages:
        return _get_all_pages(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/modules/{module_id}/assignment_overrides",
        )

    else:
        response = _make_request(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/modules/{module_id}/assignment_overrides",
        )
        return response.json()


def update_module_overrides(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    module_id: Union[int, str],
    overrides: List[ModuleOverride],
) -> None:
    """
    Update assignment overrides for a module.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        module_id: Module ID
        overrides: List of override objects to apply

    Returns:
        None (204 No Content response)

    Raises:
        ValueError: If overrides list format is invalid

    Note:
        - Existing overrides with IDs will be updated
        - New overrides without IDs will be created
        - Overrides not in the list will be deleted
        - Empty list deletes all overrides
    """
    # Validate each override object
    for i, override in enumerate(overrides):
        if not isinstance(override, dict):
            raise ValueError(f"Override at index {i} must be a dictionary")

        # Check for at least one target specification
        targets = ["student_ids", "course_section_id", "group_id"]
        if not any(target in override for target in targets):
            # Allow overrides with just ID for updates/deletes
            if "id" not in override:
                raise ValueError(
                    f"Override at index {i} must include 'id' or one of: {', '.join(targets)}"
                )

    json_data = {"overrides": overrides}

    _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/courses/{course_id}/modules/{module_id}/assignment_overrides",
        json_data=json_data,
    )
    # 204 No Content response, so no JSON to return
    return None
