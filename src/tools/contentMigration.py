"""Content Migration tools for Canvas MCP."""

import asyncio
from typing import Annotated, Literal
from pydantic import Field

from .base import ToolProvider
from fastmcp import Context
from canvasAPI.contentMigration.contentMigration import (
    list_content_migrations,
    get_content_migration,
    create_content_migration,
    list_migration_systems,
    copy_course_content,
    execute_selective_migration as _execute_selective_migration,
    get_migration_progress as _get_migration_progress,
    list_migration_issues,
    get_migration_issue,
    update_migration_issue,
)
from tools.getToken import get_user_token


class ContentMigrationTools(ToolProvider):
    """Tools for managing Canvas content migrations."""

    def _register_tools(self):
        """Register all content migration-related tools."""
        tools_to_register = [
            (self.list_content_migrations, {"migration"}),
            (self.get_content_migration, {"migration"}),
            (self.create_content_migration, {"migration"}),
            (self.list_migration_systems, {"migration"}),
            (self.copy_course_content, {"migration", "course"}),
            (self.selective_course_copy, {"migration", "course"}),
            (self.execute_selective_migration, {"migration", "course"}),
            (self.get_migration_progress, {"migration"}),
        ]
        
        for tool_func, tags in tools_to_register:
            wrapped_tool = self._wrap_tool_with_analytics(tool_func)
            self.mcp.tool(wrapped_tool, tags=tags)

    async def list_content_migrations(
        self,
        context_type: Annotated[
            Literal["accounts", "courses", "groups", "users"],
            Field(description="Type of context (accounts, courses, groups, users)"),
        ],
        context_id: Annotated[str | int, Field(description="Context ID")],
        all_pages: Annotated[
            bool, Field(description="Whether to fetch all pages")
        ] = False,
        ctx: Context = None,
    ) -> list[dict]:
        """List content migrations for a context."""
        if ctx:
            await ctx.info(
                f"Listing content migrations for {context_type} {context_id}"
            )
            await ctx.debug("Preparing API request parameters")

        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            all_pages=all_pages,
        )
        params["base_url"], params["access_token"] = get_user_token()

        if ctx:
            await ctx.debug("Executing API request to Canvas")

        migrations = list_content_migrations(**params)

        if ctx:
            await ctx.info(f"Retrieved {len(migrations)} migrations")

        return migrations

    async def get_content_migration(
        self,
        context_type: Annotated[
            Literal["accounts", "courses", "groups", "users"],
            Field(description="Type of context (accounts, courses, groups, users)"),
        ],
        context_id: Annotated[str | int, Field(description="Context ID")],
        migration_id: Annotated[str | int, Field(description="Migration ID")],
    ) -> dict:
        """Get details of a specific content migration."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            migration_id=migration_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return get_content_migration(**params)

    async def create_content_migration(
        self,
        context_type: Annotated[
            Literal["accounts", "courses", "groups", "users"],
            Field(description="Type of context (accounts, courses, groups, users)"),
        ],
        context_id: Annotated[str | int, Field(description="Context ID")],
        migration_type: Annotated[
            str, Field(description="Type of migration (e.g., course_copy_importer)")
        ],
        settings: Annotated[
            dict | None,
            Field(description="Migration settings (e.g., source_course_id)"),
        ] = None,
        date_shift_options: Annotated[
            dict | None, Field(description="Options for shifting dates")
        ] = None,
        selective_import: Annotated[
            bool | None, Field(description="Whether to perform selective import")
        ] = None,
        select: Annotated[
            dict | None, Field(description="Objects to copy for selective import")
        ] = None,
    ) -> dict:
        """Create a new content migration."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            migration_type=migration_type,
            pre_attachment=None,
            settings=settings,
            date_shift_options=date_shift_options,
            selective_import=selective_import,
            select=select,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return create_content_migration(**params)

    async def list_migration_systems(
        self,
        context_type: Annotated[
            Literal["accounts", "courses", "groups", "users"],
            Field(description="Type of context (accounts, courses, groups, users)"),
        ],
        context_id: Annotated[str | int, Field(description="Context ID")],
    ) -> list[dict]:
        """List available migration systems."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return list_migration_systems(**params)

    async def copy_course_content(
        self,
        source_course_id: Annotated[
            str | int, Field(description="ID of the source course")
        ],
        destination_course_id: Annotated[
            str | int, Field(description="ID of the destination course")
        ],
        shift_dates: Annotated[
            bool, Field(description="Whether to shift dates")
        ] = False,
        old_start_date: Annotated[
            str | None, Field(description="Original start date (YYYY-MM-DD)")
        ] = None,
        new_start_date: Annotated[
            str | None, Field(description="New start date (YYYY-MM-DD)")
        ] = None,
        old_end_date: Annotated[
            str | None, Field(description="Original end date (YYYY-MM-DD)")
        ] = None,
        new_end_date: Annotated[
            str | None, Field(description="New end date (YYYY-MM-DD)")
        ] = None,
        day_substitutions: Annotated[
            dict | None, Field(description="Day substitution mapping")
        ] = None,
        remove_dates: Annotated[
            bool, Field(description="Whether to remove all dates")
        ] = False,
        selective_items: Annotated[
            dict | None,
            Field(description="Dictionary of content types and IDs to copy"),
        ] = None,
        import_blueprint_settings: Annotated[
            bool, Field(description="Whether to import blueprint settings")
        ] = False,
        move_to_assignment_group_id: Annotated[
            int | None,
            Field(description="Assignment group to move assignments to"),
        ] = None,
        insert_into_module_id: Annotated[
            int | None, Field(description="Module to add imported items to")
        ] = None,
        insert_into_module_type: Annotated[
            Literal["assignment", "discussion_topic", "file", "page", "quiz"] | None,
            Field(description="Type of items to add to module"),
        ] = None,
        insert_into_module_position: Annotated[
            int | None, Field(description="Position in module to insert items")
        ] = None,
        ctx: Context = None,
    ) -> dict:
        """Copy content from one course to another.

        This is a simplified wrapper for course-to-course content copying with
        common options like date shifting and selective copying.

        Example:
            # Simple course copy
            await copy_course_content(123, 456)

            # Course copy with date shifting
            await copy_course_content(
                123, 456,
                shift_dates=True,
                old_start_date="2023-01-01",
                new_start_date="2024-01-01"
            )

            # Selective course copy
            await copy_course_content(
                123, 456,
                selective_items={"assignments": [1, 2], "quizzes": [3]}
            )
        """
        if ctx:
            await ctx.info(
                f"Starting course content copy from {source_course_id} to {destination_course_id}"
            )
            if shift_dates:
                await ctx.debug(f"Date shifting: {old_start_date} -> {new_start_date}")
            if selective_items:
                await ctx.debug(f"Selective items: {list(selective_items.keys())}")

        params = self._validate_params(
            source_course_id=source_course_id,
            destination_course_id=destination_course_id,
            shift_dates=shift_dates,
            old_start_date=old_start_date,
            new_start_date=new_start_date,
            old_end_date=old_end_date,
            new_end_date=new_end_date,
            day_substitutions=day_substitutions,
            remove_dates=remove_dates,
            selective_items=selective_items,
            import_blueprint_settings=import_blueprint_settings,
            move_to_assignment_group_id=move_to_assignment_group_id,
            insert_into_module_id=insert_into_module_id,
            insert_into_module_type=insert_into_module_type,
            insert_into_module_position=insert_into_module_position,
        )
        params["base_url"], params["access_token"] = get_user_token()

        try:
            if ctx:
                await ctx.info("Executing course content copy")

            migration = copy_course_content(**params)

            if ctx:
                await ctx.info(
                    f"Course copy initiated successfully with migration ID: {migration.get('id')}"
                )

            return migration

        except Exception as e:
            if ctx:
                await ctx.error(f"Course content copy failed: {str(e)}")
            raise

    async def selective_course_copy(
        self,
        source_course_id: Annotated[
            str | int, Field(description="ID of the source course")
        ],
        destination_course_id: Annotated[
            str | int, Field(description="ID of the destination course")
        ],
        content_types: Annotated[
            list[str] | None,
            Field(
                description="List of content types to include (e.g., ['assignments', 'quizzes'])"
            ),
        ] = None,
        interactive_selection: Annotated[
            bool, Field(description="If True, return content for user selection")
        ] = True,
        poll_interval: Annotated[
            int, Field(description="Seconds between status checks")
        ] = 2,
        max_wait_time: Annotated[
            int, Field(description="Maximum seconds to wait for content analysis")
        ] = 300,
        ctx: Context = None,
    ) -> dict:
        """Perform selective course content copy with discovery workflow.

        This function initiates a selective import migration, waits for Canvas
        to analyze the source content, and returns available items for selection.

        Example:
            # Get available content for user selection
            result = await selective_course_copy(123, 456, ["assignments", "quizzes"])

            # The result contains:
            # - migration_id: Use with execute_selective_migration
            # - available_content: Items available for selection
            # - status: Current migration status
        """
        if ctx:
            await ctx.info(
                f"Starting selective course copy from course {source_course_id} to {destination_course_id}"
            )
            if content_types:
                await ctx.info(f"Content types filter: {', '.join(content_types)}")

            # Stage 1: Setup (0-10%)
            await ctx.report_progress(progress=0, total=100)
            await ctx.debug("Preparing migration parameters")

        params = self._validate_params(
            source_course_id=source_course_id,
            destination_course_id=destination_course_id,
            content_types=content_types,
            interactive_selection=interactive_selection,
            poll_interval=poll_interval,
            max_wait_time=max_wait_time,
        )
        params["base_url"], params["access_token"] = get_user_token()

        if ctx:
            await ctx.report_progress(progress=10, total=100)
            await ctx.info("Initiating selective migration with Canvas")

        # Create a custom implementation with progress reporting
        try:
            # Stage 2: Create migration (10-20%)
            if ctx:
                await ctx.debug("Creating content migration")
                await ctx.report_progress(progress=15, total=100)

            migration = create_content_migration(
                params["base_url"],
                params["access_token"],
                "courses",
                destination_course_id,
                "course_copy_importer",
                None,
                {"source_course_id": str(source_course_id)},
                None,
                True,
                None,
            )

            migration_id = migration["id"]

            if ctx:
                await ctx.info(f"Migration created with ID: {migration_id}")
                await ctx.report_progress(progress=20, total=100)

            # Stage 3: Wait for analysis (20-70%)
            if ctx:
                await ctx.info("Waiting for Canvas to analyze source content...")

            start_time = asyncio.get_event_loop().time()
            progress_step = 0

            while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
                current_status = get_content_migration(
                    params["base_url"],
                    params["access_token"],
                    "courses",
                    destination_course_id,
                    migration_id,
                )

                workflow_state = current_status["workflow_state"]

                # Update progress during waiting (20-70%)
                if ctx:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    wait_progress = min(50, (elapsed / max_wait_time) * 50)
                    await ctx.report_progress(progress=20 + wait_progress, total=100)

                    if progress_step % 10 == 0:  # Log every 10th check
                        await ctx.debug(f"Migration status: {workflow_state}")

                    progress_step += 1

                if workflow_state == "waiting_for_select":
                    break
                elif workflow_state in ["failed", "completed"]:
                    if ctx:
                        await ctx.error(
                            f"Migration completed unexpectedly with state: {workflow_state}"
                        )
                    return {
                        "migration_id": migration_id,
                        "status": workflow_state,
                        "error": "Migration completed unexpectedly or failed",
                        "migration_details": current_status,
                    }

                await asyncio.sleep(poll_interval)
            else:
                if ctx:
                    await ctx.warning(
                        f"Migration analysis timed out after {max_wait_time} seconds"
                    )
                return {
                    "migration_id": migration_id,
                    "status": "timeout",
                    "error": f"Migration did not reach waiting_for_select state within {max_wait_time} seconds",
                }

            if ctx:
                await ctx.report_progress(progress=70, total=100)
                await ctx.info("Content analysis complete, retrieving available items")

            # Stage 4: Get available content (70-90%)
            available_content = {}
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
                "assessment_question_banks": "assessment_question_banks",
            }

            target_types = (
                content_types if content_types else list(content_type_mapping.keys())
            )
            total_types = len(target_types)

            for i, content_type in enumerate(target_types):
                api_type = content_type_mapping.get(content_type, content_type)

                try:
                    if ctx:
                        await ctx.debug(f"Retrieving {content_type} content")

                    from canvasAPI.contentMigration.contentMigration import (
                        list_items_for_selective_import,
                    )

                    content_items = list_items_for_selective_import(
                        params["base_url"],
                        params["access_token"],
                        "courses",
                        destination_course_id,
                        migration_id,
                        type=api_type,
                    )
                    available_content[content_type] = content_items

                    if ctx:
                        item_count = (
                            len(content_items) if isinstance(content_items, list) else 1
                        )
                        await ctx.debug(f"Found {item_count} {content_type} items")

                except Exception as e:
                    if ctx:
                        await ctx.warning(
                            f"Failed to retrieve {content_type}: {str(e)}"
                        )
                    available_content[content_type] = {"error": str(e)}

                if ctx:
                    type_progress = 70 + ((i + 1) / total_types) * 20
                    await ctx.report_progress(progress=type_progress, total=100)

            # Stage 5: Finalize (90-100%)
            if ctx:
                await ctx.report_progress(progress=90, total=100)
                await ctx.debug("Preparing response data")

            result = {
                "migration_id": migration_id,
                "status": "waiting_for_select",
                "available_content": available_content,
                "source_course_id": source_course_id,
                "destination_course_id": destination_course_id,
            }

            if not interactive_selection:
                if ctx:
                    await ctx.info("Auto-selecting all available items")

                from canvasAPI.contentMigration.contentMigration import (
                    _extract_all_properties,
                    update_content_migration,
                )

                selected_properties = _extract_all_properties(available_content)

                update_content_migration(
                    params["base_url"],
                    params["access_token"],
                    "courses",
                    destination_course_id,
                    migration_id,
                    None,
                    None,
                    None,
                    None,
                    selected_properties,
                )

                result["status"] = "migration_started"
                result["selected_items"] = selected_properties

                if ctx:
                    await ctx.info(
                        f"Migration started with {len(selected_properties)} selected items"
                    )

            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info("Selective course copy setup completed successfully")

            return result

        except Exception as e:
            if ctx:
                await ctx.error(f"Selective course copy failed: {str(e)}")
            raise

    async def execute_selective_migration(
        self,
        destination_course_id: Annotated[
            str | int, Field(description="Destination course ID")
        ],
        migration_id: Annotated[
            str | int, Field(description="Migration ID from selective_course_copy")
        ],
        selected_properties: Annotated[
            dict, Field(description="Dictionary of property keys to 1 (selected items)")
        ],
        monitor_until_complete: Annotated[
            bool,
            Field(description="Whether to monitor migration progress until completion"),
        ] = True,
        poll_interval: Annotated[
            int, Field(description="Seconds between progress checks when monitoring")
        ] = 5,
        ctx: Context = None,
    ) -> dict:
        """Execute a selective migration with user-selected items and automatically monitor progress.

        This function executes the migration with selected items and by default monitors
        the progress until completion, providing real-time updates to the client.

        Example:
            # Properties extracted from available_content returned by selective_course_copy
            selected_properties = {
                "copy[assignments][id_i123abc]": 1,
                "copy[quizzes][id_i456def]": 1
            }

            # This will execute and monitor until completion
            result = await execute_selective_migration(456, migration_id, selected_properties)
        """
        if ctx:
            await ctx.info(
                f"Executing selective migration {migration_id} with {len(selected_properties)} selected items"
            )
            await ctx.debug("Preparing migration execution")

        params = self._validate_params(
            destination_course_id=destination_course_id,
            migration_id=migration_id,
            selected_properties=selected_properties,
        )
        params["base_url"], params["access_token"] = get_user_token()

        try:
            if ctx:
                await ctx.info("Starting migration execution with selected items")
                await ctx.debug(
                    f"Selected properties: {list(selected_properties.keys())[:5]}..."
                )

            # Execute the migration
            migration = _execute_selective_migration(**params)

            if ctx:
                await ctx.info("Migration execution initiated successfully")

            # If not monitoring, return immediately
            if not monitor_until_complete:
                return migration

            # Monitor progress until completion
            if ctx:
                await ctx.info("Monitoring migration progress until completion...")
                await ctx.report_progress(progress=0, total=100)

            start_time = asyncio.get_event_loop().time()
            check_count = 0

            while True:
                # Get current migration status
                progress = _get_migration_progress(
                    params["base_url"],
                    params["access_token"],
                    destination_course_id,
                    migration_id,
                )
                workflow_state = progress.get("workflow_state", "unknown")

                check_count += 1
                elapsed = asyncio.get_event_loop().time() - start_time

                if ctx:
                    # Report indeterminate progress since we don't know total time
                    await ctx.report_progress(progress=check_count)

                    if (
                        check_count % 3 == 0
                    ):  # Log every 3rd check for more frequent updates
                        await ctx.info(
                            f"Migration status: {workflow_state} (elapsed: {elapsed:.1f}s)"
                        )

                # Check if migration is complete
                if workflow_state in ["completed", "failed"]:
                    if ctx:
                        if workflow_state == "completed":
                            await ctx.info(
                                f"Migration completed successfully after {elapsed:.1f} seconds"
                            )
                            await ctx.report_progress(progress=100, total=100)
                        else:
                            await ctx.warning(
                                f"Migration failed after {elapsed:.1f} seconds"
                            )

                    # Return the final status
                    return progress

                elif workflow_state in ["pre_processing", "pre_processed", "running"]:
                    if ctx and check_count == 1:
                        await ctx.info(
                            f"Migration is {workflow_state}, continuing to monitor..."
                        )

                await asyncio.sleep(poll_interval)

        except Exception as e:
            if ctx:
                await ctx.error(f"Failed to execute selective migration: {str(e)}")
            raise

    async def get_migration_progress(
        self,
        destination_course_id: Annotated[
            str | int, Field(description="Destination course ID")
        ],
        migration_id: Annotated[str | int, Field(description="Migration ID")],
        monitor_progress: Annotated[
            bool, Field(description="Whether to continuously monitor until completion")
        ] = False,
        poll_interval: Annotated[
            int, Field(description="Seconds between progress checks when monitoring")
        ] = 5,
        ctx: Context = None,
    ) -> dict:
        """Get the current status and progress of a content migration.

        If monitor_progress is True, this will continuously poll the migration
        status and provide progress updates until completion.
        """
        if ctx:
            await ctx.info(f"Checking migration progress for migration {migration_id}")

        params = self._validate_params(
            destination_course_id=destination_course_id,
            migration_id=migration_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        try:
            if not monitor_progress:
                # Single status check
                progress = _get_migration_progress(**params)

                if ctx:
                    await ctx.info(
                        f"Migration status: {progress.get('workflow_state', 'unknown')}"
                    )

                return progress

            # Continuous monitoring mode
            if ctx:
                await ctx.info("Starting continuous migration progress monitoring...")
                await ctx.report_progress(progress=0, total=100)

            start_time = asyncio.get_event_loop().time()
            check_count = 0

            while True:
                progress = _get_migration_progress(**params)
                workflow_state = progress.get("workflow_state", "unknown")

                check_count += 1
                elapsed = asyncio.get_event_loop().time() - start_time

                if ctx:
                    # Report indeterminate progress since we don't know total time
                    await ctx.report_progress(progress=check_count)

                    if check_count % 5 == 0:  # Log every 5th check
                        await ctx.info(
                            f"Migration status: {workflow_state} (elapsed: {elapsed:.1f}s)"
                        )

                # Check if migration is complete
                if workflow_state in ["completed", "failed"]:
                    if ctx:
                        if workflow_state == "completed":
                            await ctx.info(
                                f"Migration completed successfully after {elapsed:.1f} seconds"
                            )
                        else:
                            await ctx.warning(
                                f"Migration failed after {elapsed:.1f} seconds"
                            )
                    break

                elif workflow_state in ["pre_processing", "pre_processed", "running"]:
                    if ctx and check_count == 1:
                        await ctx.info(
                            f"Migration is {workflow_state}, continuing to monitor..."
                        )

                await asyncio.sleep(poll_interval)

            return progress

        except Exception as e:
            if ctx:
                await ctx.error(f"Failed to get migration progress: {str(e)}")
            raise


class MigrationIssueTools(ToolProvider):
    """Tools for managing Canvas migration issues."""

    def _register_tools(self):
        """Register all migration issue-related tools."""
        tools_to_register = [
            (self.list_migration_issues, {"migration", "issues"}),
            (self.get_migration_issue, {"migration", "issues"}),
            (self.update_migration_issue, {"migration", "issues"}),
        ]
        
        for tool_func, tags in tools_to_register:
            wrapped_tool = self._wrap_tool_with_analytics(tool_func)
            self.mcp.tool(wrapped_tool, tags=tags)

    async def list_migration_issues(
        self,
        context_type: Annotated[
            Literal["accounts", "courses", "groups", "users"],
            Field(description="Type of context (accounts, courses, groups, users)"),
        ],
        context_id: Annotated[str | int, Field(description="Context ID")],
        content_migration_id: Annotated[
            str | int, Field(description="Content migration ID")
        ],
        all_pages: Annotated[
            bool, Field(description="Whether to fetch all pages")
        ] = False,
    ) -> list[dict]:
        """List migration issues for a content migration."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            content_migration_id=content_migration_id,
            all_pages=all_pages,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return list_migration_issues(**params)

    async def get_migration_issue(
        self,
        context_type: Annotated[
            Literal["accounts", "courses", "groups", "users"],
            Field(description="Type of context (accounts, courses, groups, users)"),
        ],
        context_id: Annotated[str | int, Field(description="Context ID")],
        content_migration_id: Annotated[
            str | int, Field(description="Content migration ID")
        ],
        issue_id: Annotated[str | int, Field(description="Migration issue ID")],
    ) -> dict:
        """Get details of a specific migration issue."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            content_migration_id=content_migration_id,
            issue_id=issue_id,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return get_migration_issue(**params)

    async def update_migration_issue(
        self,
        context_type: Annotated[
            Literal["accounts", "courses", "groups", "users"],
            Field(description="Type of context (accounts, courses, groups, users)"),
        ],
        context_id: Annotated[str | int, Field(description="Context ID")],
        content_migration_id: Annotated[
            str | int, Field(description="Content migration ID")
        ],
        issue_id: Annotated[str | int, Field(description="Migration issue ID")],
        workflow_state: Annotated[
            Literal["active", "resolved"],
            Field(description="New workflow state (active or resolved)"),
        ],
    ) -> dict:
        """Update the workflow state of a migration issue."""
        params = self._validate_params(
            context_type=context_type,
            context_id=context_id,
            content_migration_id=content_migration_id,
            issue_id=issue_id,
            workflow_state=workflow_state,
        )
        params["base_url"], params["access_token"] = get_user_token()

        return update_migration_issue(**params)
