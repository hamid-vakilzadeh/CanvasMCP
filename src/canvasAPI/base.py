import requests
import json
from typing import Dict, List
from fastmcp.server.dependencies import get_access_token


def _make_request(
    method: str,
    endpoint: str,
    params: Dict = None,
    data: Dict = None,
    json_data: Dict = None,
    base_url: str = None,
    access_token: str = None,
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
    
    # Extract credentials from JWT if not provided
    if base_url is None or access_token is None:
        token = get_access_token()
        
        if base_url is None:
            base_url = getattr(token, 'canvas_url', None)
            if not base_url and hasattr(token, 'additional_claims'):
                base_url = token.additional_claims.get('canvas_url')
            if not base_url:
                raise ValueError("canvas_url not found in JWT token")
        
        if access_token is None:
            access_token = getattr(token, 'canvas_access_token', None)
            if not access_token and hasattr(token, 'additional_claims'):
                access_token = token.additional_claims.get('canvas_access_token')
            if not access_token:
                raise ValueError("canvas_access_token not found in JWT token")

    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{base_url}{endpoint}"

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
    method: str,
    endpoint: str,
    params: Dict = None,
    data: Dict = None,
    json_data: Dict = None,
    base_url: str = None,
    access_token: str = None,
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
            response.raise_for_status()
        else:
            break

    return all_items
