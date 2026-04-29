import os
import base64
import hashlib
from typing import Dict, List, Optional, Any
from unkey.py import Unkey
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from nacl.secret import SecretBox
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _get_env_canvas_credentials() -> Optional[tuple[str, str]]:
    """Return local Canvas credentials when configured for direct/dev access."""
    base_url = os.getenv("CANVAS_URL")
    access_token = os.getenv("CANVAS_ACCESS_TOKEN")

    if base_url and access_token:
        return base_url, access_token

    return None


def _env_flag_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _should_use_env_credentials(request_api_key: Optional[str]) -> bool:
    return not request_api_key or _env_flag_enabled("CANVAS_BYPASS_UNKEY")


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
    tags: Optional[List[str]] = None,
    authorization_permissions: Optional[str] = None,
    remaining_cost: Optional[int] = None,
    ratelimits: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Verify a key using the Unkey SDK.

    Returns:
        Dict with: valid, code, requestId, keyId, name, meta, expires,
        credits, enabled, permissions, roles, ratelimits, identity
    """
    if not key:
        raise ValueError("Key must have minimum length of 1")

    if tags and len(tags) > 10:
        raise ValueError("Maximum 10 tags allowed")

    if tags:
        for tag in tags:
            if not isinstance(tag, str) or len(tag) < 1 or len(tag) > 128:
                raise ValueError(
                    "Each tag must be a string between 1 and 128 characters long"
                )

    root_key = os.getenv("UNKEY_ROOT_KEY")
    if not root_key:
        raise ValueError("UNKEY_ROOT_KEY environment variable is required")

    credits_param = {"cost": remaining_cost} if remaining_cost is not None else None

    try:
        with Unkey(root_key=root_key) as unkey_client:
            res = unkey_client.keys.verify_key(
                key=key,
                tags=tags,
                permissions=authorization_permissions,
                credits=credits_param,
                ratelimits=ratelimits,
            )
    except Exception as e:
        error_message = str(e)
        if "Insufficient Permissions" in error_message or "verify_key" in error_message:
            raise ValueError(
                "UNKEY_ROOT_KEY is missing the api.*.verify_key permission required "
                "to verify request API keys."
            ) from e
        raise

    data = res.data.model_dump(by_alias=True)
    data["requestId"] = res.meta.request_id
    return data


def _credentials_from_api_key(
    api_key: str,
    *,
    verification_result: Optional[Dict[str, Any]] = None,
    ctx=None,
    session_id: Optional[str] = None,
) -> tuple[str, str]:
    if verification_result is None:
        verification_result = verify_key(api_key)

    if not verification_result.get("valid", False):
        raise ValueError("Invalid API key")

    owner_id = verification_result.get("ownerId")
    if owner_id and ctx:
        ctx.set_state("owner_id", owner_id)

    meta = verification_result.get("meta", {})
    base_url = meta.get("profileUrl")
    encrypted_access_token = meta.get("encryptedAccessToken")

    if not encrypted_access_token:
        raise ValueError("Encrypted access token not found in API key metadata")

    access_token = decrypt_token_with_api_key(encrypted_access_token, api_key)

    if not base_url or not access_token:
        raise ValueError("Canvas credentials not found in API key metadata")

    if session_id:
        from session_manager import session_manager

        session_manager.create_session(session_id, base_url, access_token)

    if ctx:
        ctx.set_state("canvas_base_url", base_url)
        ctx.set_state("canvas_access_token", access_token)

    return base_url, access_token


def get_user_token():
    """
    Get user token with lazy authentication.

    This function first tries to get cached credentials from session context.
    If not available, it performs authentication and creates a session for future use.

    During local testing without a request API key, credentials can be loaded
    from environment variables.

    Returns:
        Tuple of (base_url, access_token)

    Raises:
        ValueError: If authentication fails or credentials are not available
    """
    request_api_key = _extract_api_key_from_current_request()
    env_credentials = _get_env_canvas_credentials()

    # Environment credentials are a local/dev fallback. If a request API key is
    # present, they are only used when local dev explicitly bypasses Unkey.
    if env_credentials and _should_use_env_credentials(request_api_key):
        print("Using Canvas credentials from environment variables")
        return env_credentials

    try:
        from fastmcp.server.dependencies import get_context

        # Get the current FastMCP context
        ctx = get_context()
    except Exception:
        ctx = None

    api_key = request_api_key or _extract_api_key_from_current_request()
    if not api_key:
        raise ValueError("API key required in query parameters (?apikey=your_key)")

    session_id = None
    if ctx:
        # Try to get cached credentials after API verification.
        verification_result = verify_key(api_key)
        if not verification_result.get("valid", False):
            raise ValueError("Invalid API key")

        owner_id = verification_result.get("ownerId")
        if owner_id:
            ctx.set_state("owner_id", owner_id)

        base_url = ctx.get_state("canvas_base_url")
        access_token = ctx.get_state("canvas_access_token")

        if base_url and access_token:
            return base_url, access_token

        session_id = ctx.get_state("session_id")

        return _credentials_from_api_key(
            api_key,
            verification_result=verification_result,
            ctx=ctx,
            session_id=session_id,
        )

    return _credentials_from_api_key(api_key)


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

    except Exception as e:
        env_credentials = _get_env_canvas_credentials()
        if env_credentials:
            print("Using Canvas credentials from environment variables (legacy)")
            return env_credentials
        raise ValueError(f"Error extracting API key from request: {str(e)}")

    if not apikey:
        env_credentials = _get_env_canvas_credentials()
        if env_credentials:
            print("Using Canvas credentials from environment variables (legacy)")
            return env_credentials
        raise ValueError("API key required in query parameters (?apikey=your_key)")

    env_credentials = _get_env_canvas_credentials()
    if env_credentials and _should_use_env_credentials(apikey):
        print("Using Canvas credentials from environment variables (legacy)")
        return env_credentials

    return _credentials_from_api_key(apikey)


# Session monitoring functions removed for security -
# LLM should never have access to session data
