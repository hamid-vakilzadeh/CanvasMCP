import requests
import json
from typing import Dict, List, Optional, Any


def verify_key(
    key: str,
    api_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    authorization_permissions: Optional[str] = None,
    remaining_cost: Optional[int] = None,
    ratelimit_cost: Optional[int] = None,
    ratelimits: Optional[List[Dict[str, Any]]] = None,
    base_url: str = "https://api.unkey.dev",
) -> Dict[str, Any]:
    """
    Verify a key using the Unkey API.

    Args:
        key: The key to verify (minimum length: 1)
        api_id: The id of the api where the key belongs to (optional)
        tags: Tags for filtering/aggregating verification data (max 10 items)
        authorization_permissions: RBAC permissions check
        remaining_cost: Cost for remaining uses deduction
        ratelimit_cost: Deprecated, use ratelimits instead
        ratelimits: Multiple ratelimit configurations with name, limit, duration
        base_url: Base URL for the Unkey API

    Returns:
        Dict containing verification result with keys:
        - valid (bool): Whether the key is valid
        - code (str): Verification code (VALID, NOT_FOUND, etc.)
        - requestId (str): Unique request identifier
        - keyId (str, optional): The key identifier
        - name (str, optional): Key name
        - ownerId (str, optional): Owner identifier
        - meta (dict, optional): Additional metadata
        - expires (int, optional): Unix timestamp when key expires
        - ratelimit (dict, optional): Ratelimit info with limit, remaining, reset
        - remaining (int, optional): Remaining request count
        - enabled (bool, optional): Whether key is enabled
        - permissions (list, optional): List of permissions
        - roles (list, optional): List of roles
        - environment (str, optional): Key environment
        - identity (dict, optional): Associated identity info

    Raises:
        requests.exceptions.RequestException: For HTTP errors
        ValueError: For invalid input parameters
    """

    if not key or len(key) < 1:
        raise ValueError("Key must have minimum length of 1")

    if tags and len(tags) > 10:
        raise ValueError("Maximum 10 tags allowed")

    if tags:
        for tag in tags:
            if not isinstance(tag, str) or len(tag) < 1 or len(tag) > 128:
                raise ValueError(
                    "Each tag must be a string between 1 and 128 characters long"
                )

    endpoint = "/v1/keys.verifyKey"
    url = f"{base_url}{endpoint}"

    payload: Dict[str, Any] = {"key": key}

    if api_id:
        payload["apiId"] = api_id

    if tags:
        payload["tags"] = tags

    if authorization_permissions:
        payload["authorization"] = {"permissions": authorization_permissions}

    if remaining_cost is not None:
        payload["remaining"] = {"cost": remaining_cost}

    if ratelimit_cost is not None:
        payload["ratelimit"] = {"cost": ratelimit_cost}

    if ratelimits:
        payload["ratelimits"] = ratelimits

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        data = response.json()

        # Validate required fields
        if "valid" not in data or "code" not in data or "requestId" not in data:
            raise ValueError("Invalid response format: missing required fields")

        return data

    except requests.exceptions.RequestException as e:
        print(f"Unkey API request failed: {e}")
        raise
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"Failed to parse Unkey API response: {e}")
        raise


def get_user_token():
    # Extract API key from HTTP request
    try:
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()

        if request and hasattr(request, "query_params"):
            apikey = request.query_params.get("apikey")
        else:
            # Fallback: try to get from URL if available
            apikey = None
            if request and hasattr(request, "url"):
                import urllib.parse

                parsed = urllib.parse.urlparse(str(request.url))
                params = urllib.parse.parse_qs(parsed.query)
                apikey = params.get("apikey", [None])[0]

        if not apikey:
            raise ValueError("API key required in query parameters (?apikey=your_key)")

    except Exception as e:
        raise ValueError(f"Error extracting API key from request: {str(e)}")

    verification_result = verify_key(apikey)
    if not verification_result.get("valid", False):
        raise ValueError("Invalid API key")

    # Extract Canvas credentials from meta object
    meta = verification_result.get("meta", {})
    base_url = meta.get("profileUrl")
    access_token = meta.get("profileAccessToken")

    if not base_url or not access_token:
        raise ValueError("Canvas credentials not found in API key metadata")

    return base_url, access_token
