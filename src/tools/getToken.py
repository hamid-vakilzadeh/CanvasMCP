import requests
import json
import os
import base64
import hashlib
from typing import Dict, List, Optional, Any
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from nacl.secret import SecretBox
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_private_key():
    """Get the private key from environment variable."""
    secret = os.getenv("ENCRYPTION_SECRET")
    if not secret:
        raise ValueError("ENCRYPTION_SECRET environment variable is required")

    # Derive a consistent 32-byte key from the secret
    return hashlib.sha256(secret.encode()).digest()


def derive_key_from_api_key(api_key: str, private_key: bytes) -> bytes:
    """Combine API key (public) with private key to create unique encryption key."""
    combined = api_key.encode() + private_key

    # Derive final encryption key using PBKDF2 - reduced iterations for better performance
    # 5000 iterations is still cryptographically secure while being ~2x faster
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # NaCl SecretBox requires 32-byte keys
        salt=b"unkey-encryption-salt",
        iterations=5000,  # Reduced from 10000 for better performance
        backend=default_backend(),
    )
    return kdf.derive(combined)


def decrypt_token_with_api_key(encrypted_token: str, api_key: str) -> str:
    """Decrypt an encrypted token using the API key with NaCl SecretBox."""
    private_key = get_private_key()
    encryption_key = derive_key_from_api_key(api_key, private_key)

    # Decode the base64 encrypted token
    encrypted_data = base64.b64decode(encrypted_token)

    # Create SecretBox with the derived key
    box = SecretBox(encryption_key)

    try:
        # NaCl SecretBox handles nonce and authentication automatically
        decrypted_bytes = box.decrypt(encrypted_data)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Token decryption failed: {str(e)}")


def verify_key(
    key: str,
    api_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    authorization_permissions: Optional[str] = None,
    remaining_cost: Optional[int] = None,
    ratelimits: Optional[List[Dict[str, Any]]] = None,
    base_url: str = "https://api.unkey.dev",
) -> Dict[str, Any]:
    """
    Verify a key using the Unkey API.

    Args:
        key: The key to verify (minimum length: 1)
        api_id: The id of the api where the key belongs to (optional)
        tags: Tags for filtering/aggregating verification data (max 10 items)
        authorization_permissions: RBAC permissions check (AND/OR string)
        remaining_cost: Cost to deduct from key credits
        ratelimits: Multiple ratelimit configurations with name, limit, duration
        base_url: Base URL for the Unkey API

    Returns:
        Dict containing verification result with keys:
        - valid (bool): Whether the key is valid
        - code (str): Verification code (VALID, NOT_FOUND, etc.)
        - requestId (str): Unique request identifier
        - keyId (str, optional): The key identifier
        - name (str, optional): Key name
        - meta (dict, optional): Additional metadata
        - expires (int, optional): Unix timestamp when key expires
        - credits (int, optional): Remaining credit count
        - enabled (bool, optional): Whether key is enabled
        - permissions (list, optional): List of permissions
        - roles (list, optional): List of roles
        - ratelimits (list, optional): Ratelimit state per named limit
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

    unkey_api_key = os.getenv("UNKEY_ROOT_KEY")
    if not unkey_api_key:
        raise ValueError("UNKEY_ROOT_KEY environment variable is required")

    endpoint = "/v2/keys.verifyKey"
    url = f"{base_url}{endpoint}"

    payload: Dict[str, Any] = {"key": key}

    if api_id:
        payload["apiId"] = api_id

    if tags:
        payload["tags"] = tags

    if authorization_permissions:
        payload["permissions"] = authorization_permissions

    if remaining_cost is not None:
        payload["credits"] = {"cost": remaining_cost}

    if ratelimits:
        payload["ratelimits"] = ratelimits

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {unkey_api_key}",
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        body = response.json()

        if "data" not in body:
            raise ValueError("Invalid response format: missing 'data' field")

        data = body["data"]

        if "meta" in body and "requestId" in body["meta"]:
            data["requestId"] = body["meta"]["requestId"]

        if "valid" not in data or "code" not in data:
            raise ValueError("Invalid response format: missing required fields")

        return data

    except requests.exceptions.RequestException as e:
        raise
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise


def get_user_token():
    """
    Get user token with lazy authentication.

    This function first tries to get cached credentials from session context.
    If not available, it performs authentication and creates a session for future use.

    During testing, credentials can be bypassed using environment variables.

    Returns:
        Tuple of (base_url, access_token)

    Raises:
        ValueError: If authentication fails or credentials are not available
    """
    # Check for testing bypass using environment variables
    test_base_url = os.getenv("CANVAS_URL")
    test_access_token = os.getenv("CANVAS_ACCESS_TOKEN")

    if test_base_url and test_access_token:
        print("🧪 Using test credentials from environment variables")
        return test_base_url, test_access_token

    try:
        from fastmcp.server.dependencies import get_context

        # Get the current FastMCP context
        ctx = get_context()

        # Always verify API key for rate limiting on every tool call
        api_key = _extract_api_key_from_current_request()
        if not api_key:
            raise ValueError("API key required in query parameters (?apikey=your_key)")

        verification_result = verify_key(api_key)
        if not verification_result.get("valid", False):
            raise ValueError("Invalid API key")

        # Store owner_id in context for analytics
        owner_id = verification_result.get("ownerId")
        if owner_id:
            ctx.set_state("owner_id", owner_id)

        # Try to get cached credentials after API verification
        base_url = ctx.get_state("canvas_base_url")
        access_token = ctx.get_state("canvas_access_token")

        if base_url and access_token:
            return base_url, access_token

        # No cached credentials - perform authentication on first tool execution
        session_id = ctx.get_state("session_id")
        if not session_id:
            raise ValueError("No session context available")

        # Extract Canvas credentials from meta object
        meta = verification_result.get("meta", {})
        base_url = meta.get("profileUrl")
        encrypted_access_token = meta.get("encryptedAccessToken")

        if not encrypted_access_token:
            raise ValueError("Encrypted access token not found in API key metadata")

        # Decrypt access token
        access_token = decrypt_token_with_api_key(encrypted_access_token, api_key)

        if not base_url or not access_token:
            raise ValueError("Canvas credentials not found in API key metadata")

        # Update/create session for future use
        from session_manager import session_manager

        session_manager.create_session(session_id, base_url, access_token)

        # Store credentials in context for this request
        ctx.set_state("canvas_base_url", base_url)
        ctx.set_state("canvas_access_token", access_token)

        return base_url, access_token

    except Exception as e:
        # Fallback to legacy authentication if context is not available
        return _legacy_get_user_token()


def _extract_api_key_from_current_request() -> Optional[str]:
    """
    Extract API key from the current HTTP request context.

    Returns:
        API key if found, None otherwise
    """
    try:
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()
        if not request:
            return None

        # Try query parameters first
        if hasattr(request, "query_params"):
            api_key = request.query_params.get("apikey")
            if api_key:
                return api_key

        # Try to extract from URL if available
        if hasattr(request, "url"):
            import urllib.parse

            parsed = urllib.parse.urlparse(str(request.url))
            params = urllib.parse.parse_qs(parsed.query)
            api_key = params.get("apikey", [None])[0]
            if api_key:
                return api_key

        return None

    except Exception:
        return None


def _legacy_get_user_token():
    """
    Legacy token retrieval method (kept for backward compatibility).

    This method performs the original authentication and decryption process.
    It's used as a fallback when session context is not available.
    """
    # Check for testing bypass using environment variables first
    test_base_url = os.getenv("CANVAS_URL")
    test_access_token = os.getenv("CANVAS_ACCESS_TOKEN")

    if test_base_url and test_access_token:
        print("🧪 Using test credentials from environment variables (legacy)")
        return test_base_url, test_access_token

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
    encrypted_access_token = meta.get("encryptedAccessToken")

    # decrypt access token
    if not encrypted_access_token:
        raise ValueError("Encrypted access token not found in API key metadata")

    access_token = decrypt_token_with_api_key(encrypted_access_token, apikey)

    if not base_url or not access_token:
        raise ValueError("Canvas credentials not found in API key metadata")

    return base_url, access_token


# Session monitoring functions removed for security -
# LLM should never have access to session data
