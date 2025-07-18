from typing import List, Union, Optional, Literal
from datetime import datetime, date
from ..base import CanvasAPIBase
from ..discussionTopic.discussionTopics import DiscussionTopic


class AnnouncementsAPI(CanvasAPIBase):
    """Canvas LMS Announcements API client for retrieving announcements."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Announcements API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def list_announcements(
        self,
        context_codes: List[str],
        start_date: Optional[Union[date, datetime, str]] = None,
        end_date: Optional[Union[date, datetime, str]] = None,
        available_after: Optional[Union[date, datetime, str]] = None,
        active_only: Optional[bool] = None,
        latest_only: Optional[bool] = None,
        include: Optional[List[Literal["sections", "sections_user_count"]]] = None,
        all_pages: bool = False,
    ) -> List[DiscussionTopic]:
        """
        List announcements for the given courses and date range.

        Args:
            context_codes: List of context codes to retrieve announcements for (e.g., ['course_123'])
            start_date: Only return announcements posted since the start_date (inclusive).
                       Defaults to 14 days ago. Format: yyyy-mm-dd or ISO 8601 YYYY-MM-DDTHH:MM:SSZ
            end_date: Only return announcements posted before the end_date (inclusive).
                     Defaults to 28 days from start_date. Format: yyyy-mm-dd or ISO 8601 YYYY-MM-DDTHH:MM:SSZ
            available_after: Only return announcements having locked_at nil or after available_after.
                           Format: yyyy-mm-dd or ISO 8601 YYYY-MM-DDTHH:MM:SSZ
            active_only: Only return active announcements that have been published
            latest_only: Only return the latest announcement for each associated context
            include: Optional list of resources to include ("sections", "sections_user_count")
            all_pages: If True, fetch all pages automatically. If False, return only first page.

        Returns:
            List of DiscussionTopic dictionaries representing announcements

        Raises:
            ValueError: If context_codes is empty or contains invalid format, or include contains invalid values
        """
        if not context_codes:
            raise ValueError("context_codes cannot be empty")

        # Validate context codes format (should be like 'course_123')
        for context_code in context_codes:
            if not isinstance(context_code, str) or "_" not in context_code:
                raise ValueError(
                    f"Invalid context_code format: '{context_code}'. Expected format: 'course_123'"
                )

        # Validate include values
        if include is not None:
            valid_includes = {"sections", "sections_user_count"}
            invalid_includes = [i for i in include if i not in valid_includes]
            if invalid_includes:
                raise ValueError(
                    f"Invalid include values: {', '.join(invalid_includes)}. "
                    f"Allowed values: {', '.join(sorted(valid_includes))}"
                )

        params = {}

        # TODO: Is this correct?
        # Add context codes as array parameters
        for i, context_code in enumerate(context_codes):
            params[f"context_codes[{i}]"] = context_code

        # Add optional date parameters
        if start_date is not None:
            if isinstance(start_date, (date, datetime)):
                params["start_date"] = start_date.isoformat()
            else:
                params["start_date"] = start_date

        if end_date is not None:
            if isinstance(end_date, (date, datetime)):
                params["end_date"] = end_date.isoformat()
            else:
                params["end_date"] = end_date

        if available_after is not None:
            if isinstance(available_after, (date, datetime)):
                params["available_after"] = available_after.isoformat()
            else:
                params["available_after"] = available_after

        # Add optional boolean parameters
        if active_only is not None:
            params["active_only"] = active_only

        if latest_only is not None:
            params["latest_only"] = latest_only

        # Add include parameters
        if include:
            params["include[]"] = include

        if all_pages:
            return self._get_all_pages("GET", "/api/v1/announcements", params=params)
        else:
            response = self._make_request("GET", "/api/v1/announcements", params=params)
            return response.json()


# Lazy-loaded convenience instance
def get_announcements():
    from ..base import access_token, url
    return AnnouncementsAPI(access_token, url)

class _LazyAnnouncementsAPI:
    def __getattr__(self, name):
        return getattr(get_announcements(), name)

announcements = _LazyAnnouncementsAPI()
