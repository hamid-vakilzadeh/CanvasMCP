"""Analytics client for tracking tool usage with PostHog."""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import posthog
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AnalyticsClient:
    """
    Client for tracking analytics events using PostHog.
    
    This client implements privacy-first analytics:
    - No PII or sensitive data collection
    - No parameters or URLs logged
    - Sanitized error messages
    """
    
    def __init__(self):
        """Initialize the analytics client."""
        self.enabled = os.getenv("ANALYTICS_ENABLED", "false").lower() == "true"
        self.api_key = os.getenv("POSTHOG_API_KEY")
        self.host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
        
        if self.enabled and self.api_key:
            try:
                posthog.api_key = self.api_key
                posthog.host = self.host
                # Disable automatic capture of page views and other events
                posthog.disabled = False
                logger.debug(f"Analytics client initialized with host: {self.host}")
            except Exception as e:
                logger.error(f"Failed to initialize PostHog: {e}")
                self.enabled = False
        else:
            if self.enabled:
                logger.warning("Analytics enabled but POSTHOG_API_KEY not set")
            self.enabled = False
            posthog.disabled = True
    
    def track_tool_execution(
        self,
        tool_name: str,
        owner_id: Optional[str],
        session_id: Optional[str],
        duration_ms: int,
        success: bool,
        error_type: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> None:
        """
        Track a tool execution event.
        
        Args:
            tool_name: Name of the tool being executed
            owner_id: Owner ID from API key verification
            session_id: Hashed session identifier
            duration_ms: Execution time in milliseconds
            success: Whether the execution succeeded
            error_type: Type of error if failed (e.g., "ValidationError")
            error_details: Sanitized error message if failed
        """
        if not self.enabled:
            logger.debug(f"Analytics disabled - skipping tracking for {tool_name}")
            return
        
        try:
            # Use owner_id as the distinct_id for PostHog
            distinct_id = owner_id or "anonymous"
            
            properties = {
                "tool_name": tool_name,
                "session_id": session_id[:8] if session_id else None,  # Only first 8 chars for privacy
                "duration_ms": duration_ms,
                "success": success,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            # Only include error info if execution failed
            if not success:
                properties["error_type"] = error_type or "Unknown"
                properties["error_details"] = error_details or "No details available"
            
            posthog.capture(
                distinct_id=distinct_id,
                event="tool_executed",
                properties=properties
            )
            
            # Force flush to ensure event is sent immediately
            posthog.flush()
            
            logger.debug(f"Tracked tool execution: {tool_name} (success={success})")
            
        except Exception as e:
            # Never let analytics errors affect the main application
            logger.error(f"Failed to track analytics event for {tool_name}: {e}")
    
    def identify_user(self, owner_id: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """
        Identify a user for analytics tracking.
        
        Args:
            owner_id: The owner ID from API key verification
            properties: Optional user properties (be careful with PII)
        """
        if not self.enabled or not owner_id:
            return
        
        try:
            # Only set minimal, non-PII properties
            safe_properties = {
                "first_seen": datetime.now(timezone.utc).isoformat(),
            }
            
            if properties:
                # Filter out any potentially sensitive fields
                allowed_keys = {"plan", "tier", "organization_type"}
                safe_properties.update({
                    k: v for k, v in properties.items() 
                    if k in allowed_keys
                })
            
            posthog.identify(
                distinct_id=owner_id,
                properties=safe_properties
            )
            
            logger.debug(f"Identified user: {owner_id[:8]}...")
            
        except Exception as e:
            logger.debug(f"Failed to identify user: {e}")
    
    def flush(self) -> None:
        """Force flush any pending analytics events."""
        if self.enabled:
            try:
                posthog.flush()
            except Exception as e:
                logger.debug(f"Failed to flush analytics: {e}")
    
    def shutdown(self) -> None:
        """Shutdown the analytics client and flush pending events."""
        if self.enabled:
            try:
                posthog.flush()
                posthog.shutdown()
                logger.info("Analytics client shutdown complete")
            except Exception as e:
                logger.debug(f"Error during analytics shutdown: {e}")


# Singleton instance
_analytics_client: Optional[AnalyticsClient] = None


def get_analytics_client() -> AnalyticsClient:
    """
    Get the singleton analytics client instance.
    
    Returns:
        The analytics client instance
    """
    global _analytics_client
    if _analytics_client is None:
        _analytics_client = AnalyticsClient()
    return _analytics_client