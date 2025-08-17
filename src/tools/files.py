"""File and folder management tools for Canvas MCP."""

from typing import Annotated, Literal
from pydantic import Field

from .base import ToolProvider
from canvasAPI.file import files
from tools.getToken import get_user_token


class FileTools(ToolProvider):
    """Tools for managing Canvas files."""

    def _register_tools(self):
        """Register all file-related tools."""
        self.mcp.tool(self.get_quota, tags={"file", "quota"})
        self.mcp.tool(self.list_files, tags={"file", "list"})
        self.mcp.tool(self.get_file, tags={"file"})
        self.mcp.tool(self.get_public_url, tags={"file", "url"})
        self.mcp.tool(self.update_file, tags={"file", "update"})
        self.mcp.tool(self.delete_file, tags={"file", "delete"})
        self.mcp.tool(self.reset_verifier, tags={"file", "security"})
        self.mcp.tool(self.get_icon_metadata, tags={"file", "metadata"})
        self.mcp.tool(self.upload_file_via_url, tags={"file", "upload"})
        self.mcp.tool(self.complete_upload_from_url, tags={"file", "upload", "complete"})
        self.mcp.tool(self.monitor_upload_progress, tags={"file", "upload", "progress"})
        self.mcp.tool(self.translate_file_reference, tags={"file", "migration"})
        self.mcp.tool(self.copy_file, tags={"file", "copy"})

    async def get_quota(
        self,
        context_type: Annotated[
            Literal["courses", "groups", "users"],
            Field(description="Type of context (courses, groups, users)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID")
        ],
    ) -> dict:
        """Get quota information for a course, group, or user."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.get_quota(**params)

    async def list_files(
        self,
        context_type: Annotated[
            Literal["courses", "users", "groups", "folders"],
            Field(description="Type of context (courses, users, groups, folders)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID")
        ],
        content_types: Annotated[
            list[str] | None,
            Field(description="Filter by content-type (e.g., ['image/jpeg', 'text/plain'])"),
        ] = None,
        exclude_content_types: Annotated[
            list[str] | None,
            Field(description="Exclude content-types"),
        ] = None,
        search_term: Annotated[
            str | None,
            Field(description="Partial name to match"),
        ] = None,
        include: Annotated[
            list[Literal["user", "usage_rights"]] | None,
            Field(description="Additional information to include"),
        ] = None,
        only: Annotated[
            list[Literal["names"]] | None,
            Field(description="Restrict to specific information"),
        ] = None,
        sort: Annotated[
            Literal["name", "size", "created_at", "updated_at", "content_type", "user"] | None,
            Field(description="Sort field"),
        ] = "name",
        order: Annotated[
            Literal["asc", "desc"] | None,
            Field(description="Sort order"),
        ] = "asc",
    ) -> list[dict]:
        """List files for a course, user, group, or folder."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            content_types=content_types,
            exclude_content_types=exclude_content_types,
            search_term=search_term,
            include=include,
            only=only,
            sort=sort,
            order=order,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        response: list[files.File] = files.list_files(**params)

        # Return simplified response with key file information
        decorated_response = [
            {
                "id": f.get("id"),
                "display_name": f.get("display_name"),
                "filename": f.get("filename"),
                "size": f.get("size"),
                "content_type": f.get("content_type"),
                "created_at": f.get("created_at"),
                "folder_id": f.get("folder_id"),
            }
            for f in response
        ]

        return decorated_response

    async def get_file(
        self,
        file_id: Annotated[
            str | int, Field(description="File ID")
        ],
        context_type: Annotated[
            Literal["courses", "groups", "users"] | None,
            Field(description="Optional context type for scoped access"),
        ] = None,
        context_id: Annotated[
            str | int | None,
            Field(description="Optional context ID for scoped access"),
        ] = None,
        include: Annotated[
            list[Literal["user", "usage_rights"]] | None,
            Field(description="Additional information to include"),
        ] = None,
        replacement_chain_context_type: Annotated[
            Literal["course", "account"] | None,
            Field(description="Context type for replacement chain"),
        ] = None,
        replacement_chain_context_id: Annotated[
            int | None,
            Field(description="Context ID for replacement chain"),
        ] = None,
    ) -> dict:
        """Get a single file."""
        params = self._validate_params(
            file_id=file_id,
            context_type=context_type,
            context_id=context_id,
            include=include,
            replacement_chain_context_type=replacement_chain_context_type,
            replacement_chain_context_id=replacement_chain_context_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.get_file(**params)

    async def get_public_url(
        self,
        file_id: Annotated[
            str | int, Field(description="File ID")
        ],
        submission_id: Annotated[
            int | None,
            Field(description="Associated submission ID for access verification"),
        ] = None,
    ) -> dict:
        """Get public inline preview URL for a file."""
        params = self._validate_params(
            file_id=file_id,
            submission_id=submission_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.get_public_url(**params)

    async def update_file(
        self,
        file_id: Annotated[
            str | int, Field(description="File ID")
        ],
        name: Annotated[
            str | None,
            Field(description="New display name (max 255 characters)"),
        ] = None,
        parent_folder_id: Annotated[
            str | int | None,
            Field(description="ID of folder to move file to"),
        ] = None,
        on_duplicate: Annotated[
            Literal["overwrite", "rename"] | None,
            Field(description="How to handle duplicate names"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="Lock datetime (ISO format)"),
        ] = None,
        unlock_at: Annotated[
            str | None,
            Field(description="Unlock datetime (ISO format)"),
        ] = None,
        locked: Annotated[
            bool | None,
            Field(description="Lock flag"),
        ] = None,
        hidden: Annotated[
            bool | None,
            Field(description="Hidden flag"),
        ] = None,
        visibility_level: Annotated[
            Literal["inherit", "course", "institution", "public"] | None,
            Field(description="Visibility level"),
        ] = None,
    ) -> dict:
        """Update file settings."""
        params = self._validate_params(
            file_id=file_id,
            name=name,
            parent_folder_id=parent_folder_id,
            on_duplicate=on_duplicate,
            lock_at=lock_at,
            unlock_at=unlock_at,
            locked=locked,
            hidden=hidden,
            visibility_level=visibility_level,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.update_file(**params)

    async def delete_file(
        self,
        file_id: Annotated[
            str | int, Field(description="File ID")
        ],
        replace: Annotated[
            bool | None,
            Field(description="If True, replace content with 'file has been removed' message"),
        ] = False,
    ) -> dict:
        """Delete a file."""
        params = self._validate_params(
            file_id=file_id,
            replace=replace,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.delete_file(**params)

    async def reset_verifier(
        self,
        file_id: Annotated[
            str | int, Field(description="File ID")
        ],
    ) -> dict:
        """Reset the link verifier for a file."""
        params = self._validate_params(
            file_id=file_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.reset_verifier(**params)

    async def get_icon_metadata(
        self,
        file_id: Annotated[
            str | int, Field(description="File ID")
        ],
    ) -> dict:
        """Get icon maker file attachment metadata."""
        params = self._validate_params(
            file_id=file_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.get_icon_metadata(**params)

    async def upload_file_via_url(
        self,
        context_type: Annotated[
            Literal["courses", "users", "groups", "folders"],
            Field(description="Type of context (courses, users, groups, folders)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID")
        ],
        url: Annotated[
            str, Field(description="Public HTTPS URL to the file")
        ],
        name: Annotated[
            str, Field(description="Filename")
        ],
        size: Annotated[
            int | None,
            Field(description="File size in bytes"),
        ] = None,
        content_type: Annotated[
            str | None,
            Field(description="File content type"),
        ] = None,
        parent_folder_id: Annotated[
            str | int | None,
            Field(description="Parent folder ID"),
        ] = None,
        parent_folder_path: Annotated[
            str | None,
            Field(description="Parent folder path (created if doesn't exist)"),
        ] = None,
        on_duplicate: Annotated[
            Literal["overwrite", "rename"] | None,
            Field(description="How to handle duplicates"),
        ] = "overwrite",
        success_include: Annotated[
            list[str] | None,
            Field(description="Additional info in success response"),
        ] = None,
        submit_assignment: Annotated[
            bool | None,
            Field(description="Auto-submit if associated with assignment"),
        ] = True,
    ) -> dict:
        """Upload a file via HTTPS URL (Step 1 only - initiate upload)."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            url=url,
            name=name,
            size=size,
            content_type=content_type,
            parent_folder_id=parent_folder_id,
            parent_folder_path=parent_folder_path,
            on_duplicate=on_duplicate,
            success_include=success_include,
            submit_assignment=submit_assignment,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.upload_file_via_url(**params)

    async def complete_upload_from_url(
        self,
        context_type: Annotated[
            Literal["courses", "users", "groups", "folders"],
            Field(description="Type of context (courses, users, groups, folders)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID")
        ],
        url: Annotated[
            str, Field(description="Public HTTPS URL to the file")
        ],
        name: Annotated[
            str, Field(description="Filename")
        ],
        size: Annotated[
            int | None,
            Field(description="File size in bytes"),
        ] = None,
        content_type: Annotated[
            str | None,
            Field(description="File content type"),
        ] = None,
        parent_folder_id: Annotated[
            str | int | None,
            Field(description="Parent folder ID"),
        ] = None,
        parent_folder_path: Annotated[
            str | None,
            Field(description="Parent folder path (created if doesn't exist)"),
        ] = None,
        on_duplicate: Annotated[
            Literal["overwrite", "rename"] | None,
            Field(description="How to handle duplicates"),
        ] = "overwrite",
        success_include: Annotated[
            list[str] | None,
            Field(description="Additional info in success response"),
        ] = None,
        submit_assignment: Annotated[
            bool | None,
            Field(description="Auto-submit if associated with assignment"),
        ] = True,
        wait_for_completion: Annotated[
            bool | None,
            Field(description="Whether to wait for upload completion"),
        ] = False,
        max_wait_time: Annotated[
            int | None,
            Field(description="Maximum seconds to wait for completion"),
        ] = 300,
        poll_interval: Annotated[
            int | None,
            Field(description="Seconds between progress checks"),
        ] = 5,
    ) -> dict:
        """Complete file upload via HTTPS URL - handles full 2-step workflow."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            url=url,
            name=name,
            size=size,
            content_type=content_type,
            parent_folder_id=parent_folder_id,
            parent_folder_path=parent_folder_path,
            on_duplicate=on_duplicate,
            success_include=success_include,
            submit_assignment=submit_assignment,
            wait_for_completion=wait_for_completion,
            max_wait_time=max_wait_time,
            poll_interval=poll_interval,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.complete_upload_from_url(**params)

    async def monitor_upload_progress(
        self,
        progress_url: Annotated[
            str, Field(description="Progress tracking URL from upload response")
        ],
        max_wait_time: Annotated[
            int | None,
            Field(description="Maximum seconds to wait for completion"),
        ] = 300,
        poll_interval: Annotated[
            int | None,
            Field(description="Seconds between progress checks"),
        ] = 5,
    ) -> dict | None:
        """Monitor upload progress and return final file when complete."""
        params = self._validate_params(
            progress_url=progress_url,
            max_wait_time=max_wait_time,
            poll_interval=poll_interval,
        )
        params["base_url"], params["access_token"] = get_user_token()

        result = files.monitor_upload_progress(**params)
        return result if result else None

    async def translate_file_reference(
        self,
        course_id: Annotated[
            str | int, Field(description="Course ID")
        ],
        migration_id: Annotated[
            str, Field(description="Migration ID from course copy")
        ],
    ) -> dict:
        """Get file information from a course copy file reference."""
        params = self._validate_params(
            course_id=course_id,
            migration_id=migration_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.translate_file_reference(**params)

    async def copy_file(
        self,
        dest_folder_id: Annotated[
            str | int, Field(description="Destination folder ID")
        ],
        source_file_id: Annotated[
            str | int, Field(description="Source file ID")
        ],
        on_duplicate: Annotated[
            Literal["overwrite", "rename"] | None,
            Field(description="How to handle duplicate names"),
        ] = None,
    ) -> dict:
        """Copy a file to a destination folder."""
        params = self._validate_params(
            dest_folder_id=dest_folder_id,
            source_file_id=source_file_id,
            on_duplicate=on_duplicate,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.copy_file(**params)


class FolderTools(ToolProvider):
    """Tools for managing Canvas folders."""

    def _register_tools(self):
        """Register all folder-related tools."""
        self.mcp.tool(self.list_folders, tags={"folder", "list"})
        self.mcp.tool(self.resolve_path, tags={"folder", "path"})
        self.mcp.tool(self.get_folder, tags={"folder"})
        self.mcp.tool(self.create_folder, tags={"folder", "create"})
        self.mcp.tool(self.update_folder, tags={"folder", "update"})
        self.mcp.tool(self.delete_folder, tags={"folder", "delete"})
        self.mcp.tool(self.copy_folder, tags={"folder", "copy"})
        self.mcp.tool(self.get_media_folder, tags={"folder", "media"})

    async def list_folders(
        self,
        context_type: Annotated[
            Literal["courses", "users", "groups", "folders"],
            Field(description="Type of context (courses, users, groups, folders)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID or parent folder ID")
        ],
    ) -> list[dict]:
        """List folders in a context or parent folder."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        response: list[files.Folder] = files.list_folders(**params)

        # Return simplified response with key folder information
        decorated_response = [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "full_name": f.get("full_name"),
                "parent_folder_id": f.get("parent_folder_id"),
                "files_count": f.get("files_count"),
                "folders_count": f.get("folders_count"),
                "created_at": f.get("created_at"),
                "locked": f.get("locked"),
                "hidden": f.get("hidden"),
            }
            for f in response
        ]

        return decorated_response

    async def resolve_path(
        self,
        context_type: Annotated[
            Literal["courses", "users", "groups"],
            Field(description="Type of context (courses, users, groups)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID")
        ],
        full_path: Annotated[
            str | None,
            Field(description="Full path to folder (relative to root)"),
        ] = None,
    ) -> list[dict]:
        """Resolve folder path to get hierarchy."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            full_path=full_path,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.resolve_path(**params)

    async def get_folder(
        self,
        folder_id: Annotated[
            str | int | Literal["root"],
            Field(description="Folder ID or 'root' for context root folder"),
        ],
        context_type: Annotated[
            Literal["courses", "users", "groups"] | None,
            Field(description="Optional context type for scoped access"),
        ] = None,
        context_id: Annotated[
            str | int | None,
            Field(description="Optional context ID for scoped access"),
        ] = None,
    ) -> dict:
        """Get a single folder."""
        params = self._validate_params(
            folder_id=folder_id,
            context_type=context_type,
            context_id=context_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.get_folder(**params)

    async def create_folder(
        self,
        context_type: Annotated[
            Literal["courses", "users", "groups", "folders", "accounts"],
            Field(description="Type of context (courses, users, groups, folders, accounts)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID or parent folder ID")
        ],
        name: Annotated[
            str, Field(description="Folder name")
        ],
        parent_folder_id: Annotated[
            str | int | None,
            Field(description="Parent folder ID"),
        ] = None,
        parent_folder_path: Annotated[
            str | None,
            Field(description="Parent folder path (created if doesn't exist)"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="Lock datetime (ISO format)"),
        ] = None,
        unlock_at: Annotated[
            str | None,
            Field(description="Unlock datetime (ISO format)"),
        ] = None,
        locked: Annotated[
            bool | None,
            Field(description="Lock flag"),
        ] = None,
        hidden: Annotated[
            bool | None,
            Field(description="Hidden flag"),
        ] = None,
        position: Annotated[
            int | None,
            Field(description="Sort position"),
        ] = None,
    ) -> dict:
        """Create a folder."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            name=name,
            parent_folder_id=parent_folder_id,
            parent_folder_path=parent_folder_path,
            lock_at=lock_at,
            unlock_at=unlock_at,
            locked=locked,
            hidden=hidden,
            position=position,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.create_folder(**params)

    async def update_folder(
        self,
        folder_id: Annotated[
            str | int, Field(description="Folder ID")
        ],
        name: Annotated[
            str | None,
            Field(description="New folder name"),
        ] = None,
        parent_folder_id: Annotated[
            str | int | None,
            Field(description="New parent folder ID"),
        ] = None,
        lock_at: Annotated[
            str | None,
            Field(description="Lock datetime (ISO format)"),
        ] = None,
        unlock_at: Annotated[
            str | None,
            Field(description="Unlock datetime (ISO format)"),
        ] = None,
        locked: Annotated[
            bool | None,
            Field(description="Lock flag"),
        ] = None,
        hidden: Annotated[
            bool | None,
            Field(description="Hidden flag"),
        ] = None,
        position: Annotated[
            int | None,
            Field(description="Sort position"),
        ] = None,
    ) -> dict:
        """Update a folder."""
        params = self._validate_params(
            folder_id=folder_id,
            name=name,
            parent_folder_id=parent_folder_id,
            lock_at=lock_at,
            unlock_at=unlock_at,
            locked=locked,
            hidden=hidden,
            position=position,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.update_folder(**params)

    async def delete_folder(
        self,
        folder_id: Annotated[
            str | int, Field(description="Folder ID")
        ],
        force: Annotated[
            bool | None,
            Field(description="Allow deleting non-empty folders"),
        ] = False,
    ) -> None:
        """Delete a folder."""
        params = self._validate_params(
            folder_id=folder_id,
            force=force,
        )
        params["base_url"], params["access_token"] = get_user_token()

        files.delete_folder(**params)

    async def copy_folder(
        self,
        dest_folder_id: Annotated[
            str | int, Field(description="Destination folder ID")
        ],
        source_folder_id: Annotated[
            str | int, Field(description="Source folder ID")
        ],
    ) -> dict:
        """Copy a folder to a destination folder."""
        params = self._validate_params(
            dest_folder_id=dest_folder_id,
            source_folder_id=source_folder_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.copy_folder(**params)

    async def get_media_folder(
        self,
        context_type: Annotated[
            Literal["courses", "groups"],
            Field(description="Context type (courses or groups)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID")
        ],
    ) -> dict:
        """Get uploaded media folder for user."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.get_media_folder(**params)


class UsageRightsTools(ToolProvider):
    """Tools for managing Canvas file usage rights and licensing."""

    def _register_tools(self):
        """Register all usage rights-related tools."""
        self.mcp.tool(self.set_usage_rights, tags={"file", "usage_rights", "copyright"})
        self.mcp.tool(self.remove_usage_rights, tags={"file", "usage_rights", "copyright"})
        self.mcp.tool(self.list_licenses, tags={"file", "license"})

    async def set_usage_rights(
        self,
        context_type: Annotated[
            Literal["courses", "groups", "users"],
            Field(description="Context type (courses, groups, users)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID")
        ],
        file_ids: Annotated[
            list[str | int],
            Field(description="List of file IDs"),
        ],
        use_justification: Annotated[
            Literal["own_copyright", "used_by_permission", "fair_use", "public_domain", "creative_commons"],
            Field(description="Intellectual property justification"),
        ],
        legal_copyright: Annotated[
            str | None,
            Field(description="Copyright line"),
        ] = None,
        license: Annotated[
            str | None,
            Field(description="License identifier"),
        ] = None,
        folder_ids: Annotated[
            list[str | int] | None,
            Field(description="List of folder IDs to search for files"),
        ] = None,
        publish: Annotated[
            bool | None,
            Field(description="Whether to publish files on save"),
        ] = None,
    ) -> dict:
        """Set usage rights for files."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            file_ids=file_ids,
            use_justification=use_justification,
            legal_copyright=legal_copyright,
            license=license,
            folder_ids=folder_ids,
            publish=publish,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.set_usage_rights(**params)

    async def remove_usage_rights(
        self,
        context_type: Annotated[
            Literal["courses", "groups", "users"],
            Field(description="Context type (courses, groups, users)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID")
        ],
        file_ids: Annotated[
            list[str | int],
            Field(description="List of file IDs"),
        ],
        folder_ids: Annotated[
            list[str | int] | None,
            Field(description="List of folder IDs"),
        ] = None,
    ) -> None:
        """Remove usage rights from files."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            file_ids=file_ids,
            folder_ids=folder_ids,
        )
        params["base_url"], params["access_token"] = get_user_token()

        files.remove_usage_rights(**params)

    async def list_licenses(
        self,
        context_type: Annotated[
            Literal["courses", "groups", "users"],
            Field(description="Context type (courses, groups, users)"),
        ],
        context_id: Annotated[
            str | int, Field(description="Context ID")
        ],
    ) -> list[dict]:
        """List available content licenses."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            all_pages=True,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return files.list_licenses(**params)