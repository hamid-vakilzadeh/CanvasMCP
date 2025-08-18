"""Error sanitization utilities for privacy-preserving analytics."""

import re
from typing import Tuple


def sanitize_error(error: Exception) -> Tuple[str, str]:
    """
    Sanitize error information to remove sensitive data before logging.

    This function removes:
    - URLs and domains
    - API keys and tokens
    - Email addresses
    - File paths with user information
    - Canvas-specific IDs

    Args:
        error: The exception to sanitize

    Returns:
        Tuple of (error_type, sanitized_error_details)
    """
    error_type = type(error).__name__
    error_message = str(error)

    # Sanitize the error message
    sanitized_message = sanitize_string(error_message)

    return error_type, sanitized_message


def sanitize_string(text: str) -> str:
    """
    Remove sensitive information from a string.

    Args:
        text: The string to sanitize

    Returns:
        Sanitized string with sensitive data replaced
    """
    if not text:
        return ""

    # Replace URLs (including Canvas instance URLs)
    text = re.sub(r"https?://[^\s]+", "[URL_REDACTED]", text, flags=re.IGNORECASE)

    # Replace API keys and tokens (common patterns)
    # Matches strings that look like tokens (long alphanumeric strings)
    text = re.sub(r"\b[a-zA-Z0-9]{32,}\b", "[TOKEN_REDACTED]", text)

    # Replace email addresses
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]", text
    )

    # Replace file paths that might contain usernames
    text = re.sub(
        r"(/Users/[^/\s]+|/home/[^/\s]+|C:\\Users\\[^\\s]+)", "[PATH_REDACTED]", text
    )

    # Replace Canvas-specific IDs (course_id, user_id, etc.)
    text = re.sub(
        r"\b(course_id|user_id|assignment_id|quiz_id|module_id)[:=]\s*\d+",
        r"\1=[ID_REDACTED]",
        text,
        flags=re.IGNORECASE,
    )

    # Replace numeric IDs that might be sensitive (6+ digits)
    text = re.sub(r"\b\d{6,}\b", "[ID_REDACTED]", text)

    # Replace query parameters in any remaining partial URLs
    text = re.sub(r'\?[^"\s]+', "?[PARAMS_REDACTED]", text)

    # Replace API key patterns in query strings
    text = re.sub(
        r"(apikey|api_key|access_token|token)=[^&\s]+",
        r"\1=[REDACTED]",
        text,
        flags=re.IGNORECASE,
    )

    return text


def get_safe_error_category(error: Exception) -> str:
    """
    Categorize errors into safe, high-level categories for analytics.

    Args:
        error: The exception to categorize

    Returns:
        A high-level error category string
    """
    error_type = type(error).__name__
    error_message = str(error).lower()

    # API-related errors
    if "api" in error_message or "request" in error_message:
        if "401" in error_message or "unauthorized" in error_message:
            return "AuthenticationError"
        elif "403" in error_message or "forbidden" in error_message:
            return "AuthorizationError"
        elif "404" in error_message or "not found" in error_message:
            return "NotFoundError"
        elif "429" in error_message or "rate limit" in error_message:
            return "RateLimitError"
        elif "500" in error_message or "server error" in error_message:
            return "ServerError"
        else:
            return "APIError"

    # Validation errors
    elif "validation" in error_message or "invalid" in error_message:
        return "ValidationError"

    # Connection errors
    elif "connection" in error_message or "timeout" in error_message:
        return "ConnectionError"

    # Permission errors
    elif "permission" in error_message or "access denied" in error_message:
        return "PermissionError"

    # Data errors
    elif (
        "json" in error_message or "decode" in error_message or "parse" in error_message
    ):
        return "DataFormatError"

    # Default to the actual error type if no category matches
    return error_type


def create_safe_error_summary(error: Exception, include_category: bool = True) -> dict:
    """
    Create a comprehensive but safe error summary for analytics.

    Args:
        error: The exception to summarize
        include_category: Whether to include the error category

    Returns:
        Dictionary with safe error information
    """
    error_type, sanitized_details = sanitize_error(error)

    summary = {
        "error_type": error_type,
        "error_details": sanitized_details[:500],  # Limit length
    }

    if include_category:
        summary["error_category"] = get_safe_error_category(error)

    return summary
