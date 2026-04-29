import json
import logging
from urllib.parse import urlparse
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


def _format_http_error(response: requests.Response) -> str:
    """Create a concise Canvas API error without exposing the full request URL."""
    parsed_url = urlparse(response.url)
    endpoint = parsed_url.path or "unknown endpoint"
    status = response.status_code
    reason = response.reason or "HTTP error"

    if status == 401:
        return (
            f"Canvas API authentication failed for {endpoint} "
            "(401 Unauthorized). Check that the Canvas access token is valid, "
            "has not been revoked, and belongs to the configured Canvas instance."
        )

    if status == 403:
        return (
            f"Canvas API authorization failed for {endpoint} "
            "(403 Forbidden). Check that the token owner has permission for this Canvas resource."
        )

    return f"Canvas API request failed for {endpoint} ({status} {reason})"


def _raise_for_status(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise requests.exceptions.HTTPError(
            _format_http_error(response), response=response
        ) from e


def _make_request(
    base_url: str,
    access_token: str,
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
        base_url: Canvas base URL (extracted from JWT if not provided)
        access_token: Canvas API token (extracted from JWT if not provided)

    Returns:
        requests.Response object

    Raises:
        requests.exceptions.RequestException: For HTTP errors
    """

    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{base_url}{endpoint}"

    if json_data:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_data)

    try:
        response = requests.request(
            method=method, url=url, headers=headers, params=params, data=data
        )
        _raise_for_status(response)
        return response
    except requests.exceptions.RequestException as e:
        logger.warning("API request failed: %s", e)
        raise


def _get_all_pages(
    base_url: str,
    access_token: str,
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
        base_url: Canvas base URL (extracted from JWT if not provided)
        access_token: Canvas API token (extracted from JWT if not provided)

    Returns:
        List of all items from all pages
    """

    headers = {"Authorization": f"Bearer {access_token}"}

    all_items = []
    response = _make_request(
        base_url, access_token, method, endpoint, params, data, json_data
    )

    while True:
        items = response.json()
        if isinstance(items, list):
            all_items.extend(items)
        else:
            all_items.append(items)

        # Check if there's a next page using the links attribute
        if "next" in response.links:
            next_url = response.links["next"]["url"]
            response = requests.get(next_url, headers=headers)
            _raise_for_status(response)
        else:
            break

    return all_items
