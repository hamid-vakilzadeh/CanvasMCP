from dotenv import load_dotenv
import os
import requests
import json
from typing import Dict, List

# Load environment variables as fallback
load_dotenv()

# Global variables that can be set by the server
access_token = os.getenv("canvas_api_key")
url = os.getenv("main_url")


class CanvasAPIBase:
    """Base class for Canvas API clients with shared functionality."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        # Use provided arguments, then fall back to globals, then environment
        self.access_token = (
            access_token or globals().get("access_token") or os.getenv("canvas_api_key")
        )
        self.base_url = base_url or globals().get("url") or os.getenv("main_url")

        if not self.access_token or not self.base_url:
            raise ValueError(
                "Canvas API credentials not provided. Please provide access_token and base_url."
            )

        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None,
        json_data: Dict = None,
    ) -> requests.Response:
        """
        Make HTTP request to Canvas API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            params: Query parameters
            data: Form data
            json_data: JSON data

        Returns:
            requests.Response object

        Raises:
            requests.exceptions.RequestException: For HTTP errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()

        if json_data:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_data)

        try:
            response = requests.request(
                method=method, url=url, headers=headers, params=params, data=data
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            raise

    def _get_all_pages(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None,
        json_data: Dict = None,
    ) -> List[Dict]:
        """
        Fetch all pages from a paginated endpoint.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            params: Query parameters
            data: Form data
            json_data: JSON data

        Returns:
            List of all items from all pages
        """
        all_items = []
        response = self._make_request(method, endpoint, params, data, json_data)

        while True:
            items = response.json()
            if isinstance(items, list):
                all_items.extend(items)
            else:
                all_items.append(items)

            # Check if there's a next page using the links attribute
            if "next" in response.links:
                next_url = response.links["next"]["url"]
                response = requests.get(next_url, headers=self.headers)
                response.raise_for_status()
            else:
                break

        return all_items
