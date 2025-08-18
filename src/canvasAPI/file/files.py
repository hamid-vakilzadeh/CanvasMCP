from typing import List, Dict, Union, Literal, Optional, TypedDict
import requests
import time
from ..base import _make_request, _get_all_pages


class File(TypedDict, total=False):
    """Canvas File Object"""
    
    id: int
    uuid: str
    folder_id: int
    display_name: str
    filename: str
    content_type: str
    url: str
    size: int
    created_at: str
    updated_at: str
    unlock_at: Optional[str]
    locked: bool
    hidden: bool
    lock_at: Optional[str]
    hidden_for_user: bool
    visibility_level: Optional[Literal["inherit", "course", "institution", "public"]]
    thumbnail_url: Optional[str]
    modified_at: str
    mime_class: str
    media_entry_id: Optional[str]
    locked_for_user: bool
    lock_info: Optional[Dict]
    lock_explanation: Optional[str]
    preview_url: Optional[str]


class Folder(TypedDict, total=False):
    """Canvas Folder Object"""
    
    context_type: str
    context_id: int
    files_count: int
    position: int
    updated_at: str
    folders_url: str
    files_url: str
    full_name: str
    lock_at: Optional[str]
    id: int
    folders_count: int
    name: str
    parent_folder_id: Optional[int]
    created_at: str
    unlock_at: Optional[str]
    hidden: bool
    hidden_for_user: bool
    locked: bool
    locked_for_user: bool
    for_submissions: bool


class UsageRights(TypedDict, total=False):
    """Canvas Usage Rights Object"""
    
    legal_copyright: Optional[str]
    use_justification: Literal["own_copyright", "public_domain", "used_by_permission", "fair_use", "creative_commons"]
    license: Optional[str]
    license_name: Optional[str]
    message: Optional[str]
    file_ids: Optional[List[int]]


class License(TypedDict):
    """Canvas License Object"""
    
    id: str
    name: str
    url: str


class QuotaInfo(TypedDict):
    """Canvas Quota Information Object"""
    
    quota: int
    quota_used: int


class UploadParams(TypedDict, total=False):
    """File Upload Parameters Object"""
    
    upload_url: str
    upload_params: Dict[str, str]
    progress: Optional[Dict[str, Union[str, int]]]


class Progress(TypedDict):
    """Canvas Progress Object"""
    
    id: int
    context_id: int
    context_type: str
    user_id: int
    tag: str
    completion: float
    workflow_state: Literal["queued", "running", "completed", "failed"]
    created_at: str
    updated_at: str
    message: Optional[str]
    url: str
    results: Optional[Dict]


def get_quota(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "groups", "users"],
    context_id: Union[int, str],
) -> QuotaInfo:
    """
    Get quota information for a course, group, or user.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (courses, groups, users)
        context_id: Context ID

    Returns:
        QuotaInfo dictionary with quota and quota_used
    """
    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/{context_type}/{context_id}/files/quota",
    )
    return response.json()


def list_files(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "users", "groups", "folders"],
    context_id: Union[int, str],
    content_types: Optional[List[str]] = None,
    exclude_content_types: Optional[List[str]] = None,
    search_term: Optional[str] = None,
    include: Optional[List[Literal["user", "usage_rights"]]] = None,
    only: Optional[List[Literal["names"]]] = None,
    sort: Literal["name", "size", "created_at", "updated_at", "content_type", "user"] = "name",
    order: Literal["asc", "desc"] = "asc",
    all_pages: bool = False,
) -> List[File]:
    """
    List files for a course, user, group, or folder.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (courses, users, groups, folders)
        context_id: Context ID
        content_types: Filter by content-type
        exclude_content_types: Exclude content-types
        search_term: Partial name to match
        include: Additional information to include
        only: Restrict to specific information
        sort: Sort field
        order: Sort order
        all_pages: If True, fetch all pages automatically

    Returns:
        List of File dictionaries
    """
    params = {}
    
    if content_types:
        params["content_types[]"] = content_types
    if exclude_content_types:
        params["exclude_content_types[]"] = exclude_content_types
    if search_term:
        params["search_term"] = search_term
    if include:
        params["include[]"] = include
    if only:
        params["only[]"] = only
    if sort != "name":
        params["sort"] = sort
    if order != "asc":
        params["order"] = order

    endpoint = f"/api/v1/{context_type}/{context_id}/files"

    if all_pages:
        return _get_all_pages(base_url, access_token, "GET", endpoint, params=params)
    else:
        response = _make_request(base_url, access_token, "GET", endpoint, params=params)
        return response.json()


def get_file(
    base_url: str,
    access_token: str,
    file_id: Union[int, str],
    context_type: Optional[Literal["courses", "groups", "users"]] = None,
    context_id: Optional[Union[int, str]] = None,
    include: Optional[List[Literal["user", "usage_rights"]]] = None,
    replacement_chain_context_type: Optional[Literal["course", "account"]] = None,
    replacement_chain_context_id: Optional[int] = None,
) -> File:
    """
    Get a single file.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        file_id: File ID
        context_type: Optional context type for scoped access
        context_id: Optional context ID for scoped access
        include: Additional information to include
        replacement_chain_context_type: Context type for replacement chain
        replacement_chain_context_id: Context ID for replacement chain

    Returns:
        File dictionary
    """
    params = {}
    
    if include:
        params["include[]"] = include
    if replacement_chain_context_type:
        params["replacement_chain_context_type"] = replacement_chain_context_type
    if replacement_chain_context_id:
        params["replacement_chain_context_id"] = replacement_chain_context_id

    if context_type and context_id:
        endpoint = f"/api/v1/{context_type}/{context_id}/files/{file_id}"
    else:
        endpoint = f"/api/v1/files/{file_id}"

    response = _make_request(base_url, access_token, "GET", endpoint, params=params)
    return response.json()


def get_public_url(
    base_url: str,
    access_token: str,
    file_id: Union[int, str],
    submission_id: Optional[int] = None,
) -> Dict[str, str]:
    """
    Get public inline preview URL for a file.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        file_id: File ID
        submission_id: Associated submission ID for access verification

    Returns:
        Dictionary with public_url
    """
    params = {}
    if submission_id:
        params["submission_id"] = submission_id

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/files/{file_id}/public_url",
        params=params,
    )
    return response.json()


def update_file(
    base_url: str,
    access_token: str,
    file_id: Union[int, str],
    name: Optional[str] = None,
    parent_folder_id: Optional[Union[int, str]] = None,
    on_duplicate: Optional[Literal["overwrite", "rename"]] = None,
    lock_at: Optional[str] = None,
    unlock_at: Optional[str] = None,
    locked: Optional[bool] = None,
    hidden: Optional[bool] = None,
    visibility_level: Optional[Literal["inherit", "course", "institution", "public"]] = None,
) -> File:
    """
    Update file settings.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        file_id: File ID
        name: New display name (max 255 characters)
        parent_folder_id: ID of folder to move file to
        on_duplicate: How to handle duplicate names
        lock_at: Lock datetime
        unlock_at: Unlock datetime
        locked: Lock flag
        hidden: Hidden flag
        visibility_level: Visibility level

    Returns:
        Updated File dictionary
    """
    data = {}
    
    if name is not None:
        if len(name) > 255:
            raise ValueError("File name cannot exceed 255 characters")
        data["name"] = name
    if parent_folder_id is not None:
        data["parent_folder_id"] = str(parent_folder_id)
    if on_duplicate is not None:
        data["on_duplicate"] = on_duplicate
    if lock_at is not None:
        data["lock_at"] = lock_at
    if unlock_at is not None:
        data["unlock_at"] = unlock_at
    if locked is not None:
        data["locked"] = locked
    if hidden is not None:
        data["hidden"] = hidden
    if visibility_level is not None:
        data["visibility_level"] = visibility_level

    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/files/{file_id}",
        data=data,
    )
    return response.json()


def delete_file(
    base_url: str,
    access_token: str,
    file_id: Union[int, str],
    replace: bool = False,
) -> File:
    """
    Delete a file.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        file_id: File ID
        replace: If True, replace content with "file has been removed" message

    Returns:
        Deleted File dictionary
    """
    params = {}
    if replace:
        params["replace"] = replace

    response = _make_request(
        base_url,
        access_token,
        "DELETE",
        f"/api/v1/files/{file_id}",
        params=params,
    )
    return response.json()


def reset_verifier(
    base_url: str,
    access_token: str,
    file_id: Union[int, str],
) -> File:
    """
    Reset the link verifier for a file.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        file_id: File ID

    Returns:
        Updated File dictionary
    """
    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/files/{file_id}/reset_verifier",
    )
    return response.json()


def get_icon_metadata(
    base_url: str,
    access_token: str,
    file_id: Union[int, str],
) -> Dict:
    """
    Get icon maker file attachment metadata.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        file_id: File ID

    Returns:
        Icon metadata dictionary
    """
    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/files/{file_id}/icon_metadata",
    )
    return response.json()


def list_folders(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "users", "groups", "folders"],
    context_id: Union[int, str],
    all_pages: bool = False,
) -> List[Folder]:
    """
    List folders in a context or parent folder.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (courses, users, groups, folders)
        context_id: Context ID or parent folder ID
        all_pages: If True, fetch all pages automatically

    Returns:
        List of Folder dictionaries
    """
    if context_type == "folders":
        endpoint = f"/api/v1/folders/{context_id}/folders"
    else:
        endpoint = f"/api/v1/{context_type}/{context_id}/folders"

    if all_pages:
        return _get_all_pages(base_url, access_token, "GET", endpoint)
    else:
        response = _make_request(base_url, access_token, "GET", endpoint)
        return response.json()


def resolve_path(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "users", "groups"],
    context_id: Union[int, str],
    full_path: Optional[str] = None,
) -> List[Folder]:
    """
    Resolve folder path to get hierarchy.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (courses, users, groups)
        context_id: Context ID
        full_path: Full path to folder (relative to root)

    Returns:
        List of Folder dictionaries in path hierarchy
    """
    if full_path:
        endpoint = f"/api/v1/{context_type}/{context_id}/folders/by_path/{full_path}"
    else:
        endpoint = f"/api/v1/{context_type}/{context_id}/folders/by_path"

    response = _make_request(base_url, access_token, "GET", endpoint)
    return response.json()


def get_folder(
    base_url: str,
    access_token: str,
    folder_id: Union[int, str, Literal["root"]],
    context_type: Optional[Literal["courses", "users", "groups"]] = None,
    context_id: Optional[Union[int, str]] = None,
) -> Folder:
    """
    Get a single folder.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        folder_id: Folder ID or "root" for context root folder
        context_type: Optional context type for scoped access
        context_id: Optional context ID for scoped access

    Returns:
        Folder dictionary
    """
    if context_type and context_id:
        endpoint = f"/api/v1/{context_type}/{context_id}/folders/{folder_id}"
    else:
        endpoint = f"/api/v1/folders/{folder_id}"

    response = _make_request(base_url, access_token, "GET", endpoint)
    return response.json()


def create_folder(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "users", "groups", "folders", "accounts"],
    context_id: Union[int, str],
    name: str,
    parent_folder_id: Optional[Union[int, str]] = None,
    parent_folder_path: Optional[str] = None,
    lock_at: Optional[str] = None,
    unlock_at: Optional[str] = None,
    locked: Optional[bool] = None,
    hidden: Optional[bool] = None,
    position: Optional[int] = None,
) -> Folder:
    """
    Create a folder.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (courses, users, groups, folders, accounts)
        context_id: Context ID or parent folder ID
        name: Folder name
        parent_folder_id: Parent folder ID
        parent_folder_path: Parent folder path (created if doesn't exist)
        lock_at: Lock datetime
        unlock_at: Unlock datetime
        locked: Lock flag
        hidden: Hidden flag
        position: Sort position

    Returns:
        Created Folder dictionary

    Raises:
        ValueError: If both parent_folder_id and parent_folder_path are provided
    """
    if parent_folder_id and parent_folder_path:
        raise ValueError("Cannot specify both parent_folder_id and parent_folder_path")

    data = {"name": name}
    
    if parent_folder_id is not None:
        data["parent_folder_id"] = str(parent_folder_id)
    if parent_folder_path is not None:
        data["parent_folder_path"] = parent_folder_path
    if lock_at is not None:
        data["lock_at"] = lock_at
    if unlock_at is not None:
        data["unlock_at"] = unlock_at
    if locked is not None:
        data["locked"] = locked
    if hidden is not None:
        data["hidden"] = hidden
    if position is not None:
        data["position"] = position

    if context_type == "folders":
        endpoint = f"/api/v1/folders/{context_id}/folders"
    else:
        endpoint = f"/api/v1/{context_type}/{context_id}/folders"

    response = _make_request(base_url, access_token, "POST", endpoint, data=data)
    return response.json()


def update_folder(
    base_url: str,
    access_token: str,
    folder_id: Union[int, str],
    name: Optional[str] = None,
    parent_folder_id: Optional[Union[int, str]] = None,
    lock_at: Optional[str] = None,
    unlock_at: Optional[str] = None,
    locked: Optional[bool] = None,
    hidden: Optional[bool] = None,
    position: Optional[int] = None,
) -> Folder:
    """
    Update a folder.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        folder_id: Folder ID
        name: New folder name
        parent_folder_id: New parent folder ID
        lock_at: Lock datetime
        unlock_at: Unlock datetime
        locked: Lock flag
        hidden: Hidden flag
        position: Sort position

    Returns:
        Updated Folder dictionary
    """
    data = {}
    
    if name is not None:
        data["name"] = name
    if parent_folder_id is not None:
        data["parent_folder_id"] = str(parent_folder_id)
    if lock_at is not None:
        data["lock_at"] = lock_at
    if unlock_at is not None:
        data["unlock_at"] = unlock_at
    if locked is not None:
        data["locked"] = locked
    if hidden is not None:
        data["hidden"] = hidden
    if position is not None:
        data["position"] = position

    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/folders/{folder_id}",
        data=data,
    )
    return response.json()


def delete_folder(
    base_url: str,
    access_token: str,
    folder_id: Union[int, str],
    force: bool = False,
) -> None:
    """
    Delete a folder.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        folder_id: Folder ID
        force: Allow deleting non-empty folders

    Returns:
        None
    """
    params = {}
    if force:
        params["force"] = force

    _make_request(
        base_url,
        access_token,
        "DELETE",
        f"/api/v1/folders/{folder_id}",
        params=params,
    )


def copy_file(
    base_url: str,
    access_token: str,
    dest_folder_id: Union[int, str],
    source_file_id: Union[int, str],
    on_duplicate: Optional[Literal["overwrite", "rename"]] = None,
) -> File:
    """
    Copy a file to a destination folder.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        dest_folder_id: Destination folder ID
        source_file_id: Source file ID
        on_duplicate: How to handle duplicate names

    Returns:
        Copied File dictionary
    """
    data = {"source_file_id": str(source_file_id)}
    if on_duplicate:
        data["on_duplicate"] = on_duplicate

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/folders/{dest_folder_id}/copy_file",
        data=data,
    )
    return response.json()


def copy_folder(
    base_url: str,
    access_token: str,
    dest_folder_id: Union[int, str],
    source_folder_id: Union[int, str],
) -> Folder:
    """
    Copy a folder to a destination folder.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        dest_folder_id: Destination folder ID
        source_folder_id: Source folder ID

    Returns:
        Copied Folder dictionary
    """
    data = {"source_folder_id": str(source_folder_id)}

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/folders/{dest_folder_id}/copy_folder",
        data=data,
    )
    return response.json()


def get_media_folder(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "groups"],
    context_id: Union[int, str],
) -> Folder:
    """
    Get uploaded media folder for user.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Context type (courses or groups)
        context_id: Context ID

    Returns:
        Media Folder dictionary
    """
    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/{context_type}/{context_id}/folders/media",
    )
    return response.json()


def set_usage_rights(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "groups", "users"],
    context_id: Union[int, str],
    file_ids: List[Union[int, str]],
    use_justification: Literal["own_copyright", "used_by_permission", "fair_use", "public_domain", "creative_commons"],
    legal_copyright: Optional[str] = None,
    license: Optional[str] = None,
    folder_ids: Optional[List[Union[int, str]]] = None,
    publish: Optional[bool] = None,
) -> UsageRights:
    """
    Set usage rights for files.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Context type (courses, groups, users)
        context_id: Context ID
        file_ids: List of file IDs
        use_justification: Intellectual property justification
        legal_copyright: Copyright line
        license: License identifier
        folder_ids: List of folder IDs to search for files
        publish: Whether to publish files on save

    Returns:
        UsageRights dictionary
    """
    data = {
        "file_ids[]": [str(fid) for fid in file_ids],
        "usage_rights[use_justification]": use_justification,
    }
    
    if legal_copyright:
        data["usage_rights[legal_copyright]"] = legal_copyright
    if license:
        data["usage_rights[license]"] = license
    if folder_ids:
        data["folder_ids[]"] = [str(fid) for fid in folder_ids]
    if publish is not None:
        data["publish"] = publish

    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/{context_type}/{context_id}/usage_rights",
        data=data,
    )
    return response.json()


def remove_usage_rights(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "groups", "users"],
    context_id: Union[int, str],
    file_ids: List[Union[int, str]],
    folder_ids: Optional[List[Union[int, str]]] = None,
) -> None:
    """
    Remove usage rights from files.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Context type (courses, groups, users)
        context_id: Context ID
        file_ids: List of file IDs
        folder_ids: List of folder IDs

    Returns:
        None
    """
    data = {"file_ids[]": [str(fid) for fid in file_ids]}
    
    if folder_ids:
        data["folder_ids[]"] = [str(fid) for fid in folder_ids]

    _make_request(
        base_url,
        access_token,
        "DELETE",
        f"/api/v1/{context_type}/{context_id}/usage_rights",
        data=data,
    )


def upload_file_via_url(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "users", "groups", "folders"],
    context_id: Union[int, str],
    url: str,
    name: str,
    size: Optional[int] = None,
    content_type: Optional[str] = None,
    parent_folder_id: Optional[Union[int, str]] = None,
    parent_folder_path: Optional[str] = None,
    on_duplicate: Optional[Literal["overwrite", "rename"]] = "overwrite",
    success_include: Optional[List[str]] = None,
    submit_assignment: bool = True,
) -> UploadParams:
    """
    Upload a file via URL - Step 1 only (initiate upload).

    This function only initiates the upload process. For the complete workflow,
    use complete_upload_from_url() which handles both steps.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (courses, users, groups, folders)
        context_id: Context ID
        url: Public URL to the file
        name: Filename
        size: File size in bytes
        content_type: File content type
        parent_folder_id: Parent folder ID
        parent_folder_path: Parent folder path
        on_duplicate: How to handle duplicates
        success_include: Additional info in success response
        submit_assignment: Auto-submit if associated with assignment

    Returns:
        UploadParams with upload_url, upload_params, and optional progress

    Raises:
        ValueError: If both parent_folder_id and parent_folder_path are provided
    """
    if parent_folder_id and parent_folder_path:
        raise ValueError("Cannot specify both parent_folder_id and parent_folder_path")

    data = {
        "url": url,
        "name": name,
        "submit_assignment": submit_assignment,
    }
    
    if size is not None:
        data["size"] = size
    if content_type:
        data["content_type"] = content_type
    if parent_folder_id is not None:
        data["parent_folder_id"] = str(parent_folder_id)
    if parent_folder_path is not None:
        data["parent_folder_path"] = parent_folder_path
    if on_duplicate != "overwrite":
        data["on_duplicate"] = on_duplicate
    if success_include:
        data["success_include[]"] = success_include

    if context_type == "folders":
        endpoint = f"/api/v1/folders/{context_id}/files"
    else:
        endpoint = f"/api/v1/{context_type}/{context_id}/files"

    response = _make_request(base_url, access_token, "POST", endpoint, data=data)
    return response.json()


def complete_upload_from_url(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "users", "groups", "folders"],
    context_id: Union[int, str],
    url: str,
    name: str,
    size: Optional[int] = None,
    content_type: Optional[str] = None,
    parent_folder_id: Optional[Union[int, str]] = None,
    parent_folder_path: Optional[str] = None,
    on_duplicate: Optional[Literal["overwrite", "rename"]] = "overwrite",
    success_include: Optional[List[str]] = None,
    submit_assignment: bool = True,
    wait_for_completion: bool = False,
    max_wait_time: int = 300,
    poll_interval: int = 5,
) -> Dict[str, Union[UploadParams, Progress, File]]:
    """
    Complete file upload via URL - handles full 2-step workflow.

    This function handles the complete Canvas URL upload workflow:
    1. Initiate upload with Canvas
    2. If new behavior, POST to upload service
    3. Optionally wait for completion and return final file

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Type of context (courses, users, groups, folders)
        context_id: Context ID
        url: Public URL to the file
        name: Filename
        size: File size in bytes
        content_type: File content type
        parent_folder_id: Parent folder ID
        parent_folder_path: Parent folder path
        on_duplicate: How to handle duplicates
        success_include: Additional info in success response
        submit_assignment: Auto-submit if associated with assignment
        wait_for_completion: Whether to wait for upload completion
        max_wait_time: Maximum seconds to wait for completion
        poll_interval: Seconds between progress checks

    Returns:
        Dictionary with upload_params, progress, and optionally final_file

    Raises:
        ValueError: If both parent_folder_id and parent_folder_path are provided
        TimeoutError: If upload doesn't complete within max_wait_time
        requests.RequestException: If upload service request fails
    """
    # Step 1: Initiate upload
    upload_params = upload_file_via_url(
        base_url, access_token, context_type, context_id, url, name,
        size, content_type, parent_folder_id, parent_folder_path,
        on_duplicate, success_include, submit_assignment
    )
    
    result = {"upload_params": upload_params}
    
    # Step 2: Handle new behavior if upload_url is present
    if "upload_url" in upload_params and "upload_params" in upload_params:
        upload_url = upload_params["upload_url"]
        params = upload_params["upload_params"].copy()
        
        # Add the target URL (original URL) to parameters
        params["target_url"] = url
        
        # POST to upload service (no authentication required)
        try:
            upload_response = requests.post(
                upload_url,
                data=params,
                timeout=60
            )
            upload_response.raise_for_status()
            result["upload_service_response"] = {
                "status_code": upload_response.status_code,
                "success": upload_response.status_code in [200, 201]
            }
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to POST to upload service: {str(e)}")
    
    # Step 3: Wait for completion if requested
    if wait_for_completion and "progress" in upload_params:
        progress_info = upload_params["progress"]
        if "url" in progress_info:
            final_file = monitor_upload_progress(
                base_url, access_token, progress_info["url"],
                max_wait_time, poll_interval
            )
            if final_file:
                result["final_file"] = final_file
    
    return result


def monitor_upload_progress(
    base_url: str,
    access_token: str,
    progress_url: str,
    max_wait_time: int = 300,
    poll_interval: int = 5,
) -> Optional[File]:
    """
    Monitor upload progress and return final file when complete.

    Args:
        base_url: Canvas instance base URL  
        access_token: Canvas API access token
        progress_url: Progress tracking URL from upload response
        max_wait_time: Maximum seconds to wait
        poll_interval: Seconds between checks

    Returns:
        File object when complete, None if timeout or failure

    Raises:
        TimeoutError: If upload doesn't complete within max_wait_time
    """
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        # Progress URL is usually relative to Canvas base URL
        if progress_url.startswith('/'):
            full_url = base_url.rstrip('/') + progress_url
        else:
            full_url = progress_url
            
        try:
            response = _make_request("", access_token, "GET", full_url)
            progress = response.json()
            
            workflow_state = progress.get("workflow_state", "")
            
            if workflow_state == "completed":
                # Check if results contain file ID
                results = progress.get("results", {})
                if "id" in results:
                    # Get the final file
                    file_id = results["id"]
                    try:
                        file_response = _make_request(
                            base_url, access_token, "GET", f"/api/v1/files/{file_id}"
                        )
                        return file_response.json()
                    except Exception:
                        # File might not be immediately available
                        pass
                return None
                
            elif workflow_state == "failed":
                return None
                
            # Still in progress, wait and check again
            time.sleep(poll_interval)
            
        except Exception:
            # Error checking progress, wait and try again
            time.sleep(poll_interval)
    
    raise TimeoutError(f"Upload did not complete within {max_wait_time} seconds")


def translate_file_reference(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    migration_id: str,
) -> File:
    """
    Get file information from a course copy file reference.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        migration_id: Migration ID from course copy

    Returns:
        File dictionary
    """
    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/files/file_ref/{migration_id}",
    )
    return response.json()


def list_licenses(
    base_url: str,
    access_token: str,
    context_type: Literal["courses", "groups", "users"],
    context_id: Union[int, str],
    all_pages: bool = False,
) -> List[License]:
    """
    List available content licenses.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        context_type: Context type (courses, groups, users)
        context_id: Context ID
        all_pages: If True, fetch all pages automatically

    Returns:
        List of License dictionaries
    """
    endpoint = f"/api/v1/{context_type}/{context_id}/content_licenses"

    if all_pages:
        return _get_all_pages(base_url, access_token, "GET", endpoint)
    else:
        response = _make_request(base_url, access_token, "GET", endpoint)
        return response.json()