from typing import List, Dict, Union, Literal
from .base import CanvasAPIBase


class CanvasAccountCalendarsAPI(CanvasAPIBase):
    """Canvas LMS Account Calendars API client with reusable methods for all calendar endpoints."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas Account Calendars API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def list_account_calendars(self, search_term: str = None) -> List[Dict]:
        """
        List available account calendars for the current user.

        Args:
            search_term: Search term for calendar names (minimum 2 characters)

        Returns:
            List of AccountCalendar dictionaries

        Raises:
            ValueError: If search_term is less than 2 characters
        """
        if search_term is not None and len(search_term) < 2:
            raise ValueError("Search term must be at least 2 characters")

        params = {}
        if search_term:
            params["search_term"] = search_term

        response = self._make_request("GET", "/api/v1/account_calendars", params=params)
        return response.json()

    def get_account_calendar(self, account_id: Union[int, str]) -> Dict:
        """
        Get details about a specific account calendar.

        Args:
            account_id: Account ID

        Returns:
            AccountCalendar dictionary
        """
        response = self._make_request(
            "GET", f"/api/v1/account_calendars/{account_id}"
        )
        return response.json()

    def update_account_calendar(
        self,
        account_id: Union[int, str],
        visible: bool = None,
        auto_subscribe: bool = None,
    ) -> Dict:
        """
        Update an account calendar's visibility and auto_subscribe settings.

        Args:
            account_id: Account ID
            visible: Allow administrators to create events and users to view calendar
            auto_subscribe: Automatically show events to users without manual subscription

        Returns:
            Updated AccountCalendar dictionary
        """
        data = {}
        if visible is not None:
            data["visible"] = visible
        if auto_subscribe is not None:
            data["auto_subscribe"] = auto_subscribe

        response = self._make_request(
            "PUT", f"/api/v1/account_calendars/{account_id}", data=data
        )
        return response.json()

    def bulk_update_account_calendars(
        self, account_id: Union[int, str], calendar_updates: List[Dict]
    ) -> Dict:
        """
        Update multiple account calendars simultaneously.

        Args:
            account_id: Parent account ID
            calendar_updates: List of calendar update objects with 'id', 'visible', and/or 'auto_subscribe' keys

        Returns:
            Dictionary with count of updated accounts

        Raises:
            ValueError: If calendar_updates is empty or contains invalid objects
        """
        if not calendar_updates:
            raise ValueError("calendar_updates cannot be empty")

        for update in calendar_updates:
            if "id" not in update:
                raise ValueError("Each calendar update must include an 'id' field")
            if not any(key in update for key in ["visible", "auto_subscribe"]):
                raise ValueError(
                    "Each calendar update must include at least one of 'visible' or 'auto_subscribe'"
                )

        response = self._make_request(
            "PUT",
            f"/api/v1/accounts/{account_id}/account_calendars",
            json_data=calendar_updates,
        )
        return response.json()

    def list_all_account_calendars(
        self,
        account_id: Union[int, str],
        search_term: str = None,
        filter: Literal["visible", "hidden"] = None,
    ) -> List[Dict]:
        """
        List all account calendars for an account and its sub-accounts.

        Args:
            account_id: Account ID
            search_term: Search term for calendar names (minimum 2 characters)
            filter: Filter by visibility (visible or hidden)

        Returns:
            List of AccountCalendar dictionaries

        Raises:
            ValueError: If search_term is less than 2 characters or filter is invalid
        """
        if search_term is not None and len(search_term) < 2:
            raise ValueError("Search term must be at least 2 characters")

        if filter is not None and filter not in ["visible", "hidden"]:
            raise ValueError("Filter must be either 'visible' or 'hidden'")

        params = {}
        if search_term:
            params["search_term"] = search_term
        if filter:
            params["filter"] = filter

        response = self._make_request(
            "GET", f"/api/v1/accounts/{account_id}/account_calendars", params=params
        )
        return response.json()

    def get_visible_calendars_count(self, account_id: Union[int, str]) -> Dict:
        """
        Get the count of visible account calendars.

        Args:
            account_id: Account ID

        Returns:
            Dictionary with count of visible calendars
        """
        response = self._make_request(
            "GET", f"/api/v1/accounts/{account_id}/visible_calendars_count"
        )
        return response.json()


# Convenience instance using environment variables
canvas_account_calendars = CanvasAccountCalendarsAPI()